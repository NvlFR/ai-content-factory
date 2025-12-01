import subprocess
from celery import Celery
import os
import yt_dlp
import cv2
import mediapipe as mp
import ffmpeg
import json
import time
import numpy as np
from google import genai           
from google.genai import types     

# Konfigurasi Celery
celery_app = Celery(
    "worker",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

@celery_app.task(bind=True)
def process_video_pipeline(self, youtube_url: str):
    task_id = self.request.id
    work_dir = f"downloads/{task_id}"
    os.makedirs(work_dir, exist_ok=True)
    
    print(f"🚀 [Task {task_id}] Memulai proses V3 (Google GenAI Official)")

    # 1. DOWNLOAD
    self.update_state(state='PROGRESS', meta={'status': 'Downloading Video...'})
    video_path = _download_video(youtube_url, work_dir)
    if not video_path: return {"status": "failed", "error": "Download failed"}

    # 2. GEMINI ANALYSIS
    self.update_state(state='PROGRESS', meta={'status': 'Gemini 1.5 Flash is watching...'})
    
    analysis_result = _analyze_with_gemini_official(video_path)
    
    if not analysis_result:
        print("⚠️ Gemini Gagal / Timeout.")
        return {"status": "failed", "error": "Gemini Analysis Failed"}

    # 3. RENDER LOOP
    self.update_state(state='PROGRESS', meta={'status': 'Rendering Clips...'})
    
    final_clips = []
    for i, clip in enumerate(analysis_result):
        # Validasi data
        if 'start_time' not in clip or 'end_time' not in clip: continue
        
        clip_name = f"clip_{i+1}.mp4"
        title = clip.get('title', f'Clip {i+1}')
        print(f"🔄 Processing Clip #{i+1}: {title}")
        
        segmen = {
            'start': _time_to_seconds(clip['start_time']),
            'end': _time_to_seconds(clip['end_time']),
            'text': clip.get('caption', '')
        }
        
        result_path = _smart_crop_segment(video_path, segmen, work_dir, clip_name)
        if result_path:
            final_clips.append(result_path)

    return {
        "status": "completed",
        "original_video": video_path,
        "generated_clips": final_clips
    }

# --- HELPER FUNCTIONS ---

def _analyze_with_gemini_official(video_path):
    print("🤖 Connecting to Gemini Client...")
    
    try:
        # Inisialisasi Client
        client = genai.Client()

        # 1. Upload Video
        print(f"   📤 Uploading file: {video_path}")
        video_file = client.files.upload(file=video_path)
        
        # 2. Tunggu Processing
        while video_file.state.name == "PROCESSING":
            print("   ⏳ Menunggu Google memproses video...")
            time.sleep(2)
            video_file = client.files.get(name=video_file.name)

        if video_file.state.name == "FAILED":
            print("❌ Video processing failed on Google side.")
            return None

        print("   🧠 Gemini 2.0 Flash Thinking...")

        # 3. Prompt
        prompt = """
        You are a viral content editor. 
        Analyze the video and extract 3 funniest or most interesting segments (15-60 seconds each).
        Return output strictly as a JSON List.
        Format:
        [{"start_time": "MM:SS", "end_time": "MM:SS", "title": "Topic", "caption": "Exact spoken words"}]
        """

        # 4. Generate Content
        # UPDATE: Menggunakan model yang tersedia di akun Anda
        response = client.models.generate_content(
            model='gemini-2.0-flash',  # <--- KITA GANTI KE VERSI 2.0 FLASH
            contents=[video_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type='application/json' 
            )
        )
        
        # 5. Parse JSON
        print(f"   💡 Raw Response: {response.text}")
        clips = json.loads(response.text)
        
        return clips

    except Exception as e:
        print(f"❌ Gemini SDK Error: {e}")
        return None
def _time_to_seconds(time_str):
    try:
        parts = list(map(int, time_str.split(':')))
        if len(parts) == 2: return parts[0] * 60 + parts[1]
        elif len(parts) == 3: return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except: return 0.0

def _download_video(url, output_folder):
    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f'{output_folder}/source.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            return f"{output_folder}/source.mp4"
    except Exception as e:
        print(f"❌ Download Error: {e}")
        return None

def _create_srt(text, duration, output_path):
    def format_timestamp(seconds):
        ms = int((seconds % 1) * 1000)
        seconds = int(seconds)
        mins, secs = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"

    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 20: 
            lines.append(" ".join(current_line))
            current_line = []
    if current_line: lines.append(" ".join(current_line))
    final_text = "\n".join(lines)

    content = f"1\n00:00:00,000 --> {format_timestamp(duration)}\n{final_text}"
    with open(output_path, "w", encoding='utf-8') as f:
        f.write(content)
    return output_path

def _smart_crop_segment(video_path, segmen, output_folder, filename):
    start, end = segmen['start'], segmen['end']
    duration = end - start
    output_filename = f"{output_folder}/{filename}"
    
    srt_path = f"{output_folder}/{filename}.srt"
    _create_srt(segmen['text'], duration, srt_path)
    abs_srt_path = os.path.abspath(srt_path)

    center_x = _scan_face_average(video_path, start, end)
    
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    target_width = int(height * 9 / 16)
    x_start = int(center_x - (target_width // 2))
    x_start = max(0, min(x_start, width - target_width))
    
    print(f"   ⚙️ Rendering {filename} via Raw FFmpeg...")

    style = "Fontname=Liberation Sans,Fontsize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=1,Outline=3,Shadow=0,Alignment=2,MarginV=50,Bold=1"

    # Perintah FFmpeg
    command = [
        'ffmpeg', '-y',
        '-ss', str(start), '-t', str(duration),
        '-i', video_path,
        '-vf', f"crop={target_width}:{height}:{x_start}:0,subtitles='{abs_srt_path}':force_style='{style}',format=yuv420p",
        '-c:v', 'libx264',
        '-c:a', 'aac', '-b:a', '128k', 
        '-preset', 'ultrafast',
        output_filename
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"   ✅ Sukses: {filename}")
        return output_filename
    except subprocess.CalledProcessError as e:
        print(f"   ❌ FFmpeg Gagal: {e.stderr.decode('utf8') if e.stderr else 'Unknown'}")
        return None

def _scan_face_average(video_path, start_time, end_time):
    cap = cv2.VideoCapture(video_path)
    mp_face = mp.solutions.face_detection
    detected_positions = []
    
    step = max(1.0, (end_time - start_time) / 10) 
    timestamps = np.arange(start_time, end_time, step)
    
    with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.4) as face_det:
        for t in timestamps:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            success, img = cap.read()
            if not success: continue
            results = face_det.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            if results.detections:
                bbox = results.detections[0].location_data.relative_bounding_box
                center_x = bbox.xmin + (bbox.width / 2)
                detected_positions.append(center_x * cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    cap.release()
    if detected_positions: return sum(detected_positions) / len(detected_positions)
    else: return 0.5 * cap.get(cv2.CAP_PROP_FRAME_WIDTH)