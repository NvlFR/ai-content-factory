import subprocess
from celery import Celery
import os
import yt_dlp
import cv2
import mediapipe as mp
import ffmpeg
import json
from openai import OpenAI
import numpy as np # Pastikan numpy ada (biasanya bawaan cv2/pandas)

# Konfigurasi Celery
celery_app = Celery(
    "worker",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

USE_MOCK_AI = True

# Mock Data (Durasi Aman untuk video pendek)
MOCK_TRANSCRIPT = {
    "text": "Full transcript...",
    "segments": [
        {"start": 0.0, "end": 5.0, "text": "Clip 1: Halo guys! Balik lagi di kebun binatang."},
        {"start": 5.0, "end": 10.0, "text": "Clip 2: Di belakang gue ini ada gajah yang besar banget."},
        {"start": 10.0, "end": 15.0, "text": "Clip 3: Belalainya panjang banget kan? Keren abis!"}
    ]
}

@celery_app.task(bind=True)
def process_video_pipeline(self, youtube_url: str):
    task_id = self.request.id
    work_dir = f"downloads/{task_id}"
    os.makedirs(work_dir, exist_ok=True)
    
    print(f"🚀 [Task {task_id}] Memulai proses V3 (Smart Tracking)")

    # 1. DOWNLOAD
    self.update_state(state='PROGRESS', meta={'status': 'Downloading Video...'})
    video_path = _download_video(youtube_url, work_dir)
    if not video_path: return {"status": "failed", "error": "Download failed"}

    # 2. TRANSCRIBE
    self.update_state(state='PROGRESS', meta={'status': 'AI Analyzing Content...'})
    transcript = _transcribe_audio(video_path)
    
    # 3. RENDER LOOP
    self.update_state(state='PROGRESS', meta={'status': 'Rendering Clips...'})
    
    final_clips = []
    for i, segmen in enumerate(transcript['segments']):
        clip_name = f"clip_{i+1}.mp4"
        print(f"🔄 Processing Clip #{i+1}...")
        
        result_path = _smart_crop_segment(video_path, segmen, work_dir, clip_name)
        if result_path:
            final_clips.append(result_path)

    return {
        "status": "completed",
        "original_video": video_path,
        "generated_clips": final_clips
    }

# --- HELPER FUNCTIONS ---

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

def _transcribe_audio(video_path):
    if USE_MOCK_AI: return MOCK_TRANSCRIPT
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    with open(video_path, "rb") as audio:
        res = client.audio.transcriptions.create(model="whisper-1", file=audio, response_format="verbose_json")
    return res

def _create_srt(text, duration, output_path):
    def format_timestamp(seconds):
        ms = int((seconds % 1) * 1000)
        seconds = int(seconds)
        mins, secs = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"

    # Teks dibagi jadi beberapa baris kalau kepanjangan (Basic wrapping)
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 20: # Max 20 karakter per baris
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
    
    # 1. SRT Creation
    srt_path = f"{output_folder}/{filename}.srt"
    _create_srt(segmen['text'], duration, srt_path)
    abs_srt_path = os.path.abspath(srt_path)

    # 2. SMART TRACKING (Scan seluruh durasi klip)
    center_x = _scan_face_average(video_path, start, end)
    
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    # 3. Hitung Crop
    target_width = int(height * 9 / 16)
    x_start = int(center_x - (target_width // 2))
    
    # Clamp agar tidak keluar batas
    x_start = max(0, min(x_start, width - target_width))
    
    print(f"   ⚙️ Rendering {filename} (FaceCenter={int(center_x)})...")

    # 4. Styling Subtitle ala TikTok (Upgrade)
    # Fontsize Besar (24), Warna Putih (&HFFFFFF), Outline Hitam Tebal (3), Posisi Bawah (MarginV=50)
    style = "Fontname=Liberation Sans,Fontsize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=1,Outline=3,Shadow=0,Alignment=2,MarginV=50,Bold=1"

    # Perintah FFmpeg
    # [ crop ] -> [ subtitles ] -> [ format ]
    vf_command = f"crop={target_width}:{height}:{x_start}:0,subtitles='{abs_srt_path}':force_style='{style}',format=yuv420p"

    command = [
        'ffmpeg', '-y',
        '-ss', str(start),
        '-t', str(duration),
        '-i', video_path,
        '-vf', vf_command,
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
    """
    Fungsi Baru: Mengecek posisi wajah setiap 1 detik, lalu dirata-rata.
    """
    cap = cv2.VideoCapture(video_path)
    mp_face = mp.solutions.face_detection
    
    detected_positions = []
    
    # Cek setiap 1 detik (atau 0.5 detik jika klip pendek)
    timestamps = np.arange(start_time, end_time, 1.0)
    if len(timestamps) == 0: timestamps = [start_time] # Minimal cek awal

    with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.4) as face_det:
        for t in timestamps:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            success, img = cap.read()
            if not success: continue
            
            results = face_det.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            if results.detections:
                # Ambil wajah terbesar (biasanya pembicara utama)
                detection = results.detections[0]
                bbox = detection.location_data.relative_bounding_box
                center_x = bbox.xmin + (bbox.width / 2)
                
                # Simpan posisi absolut pixel
                pixel_x = center_x * cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                detected_positions.append(pixel_x)
                # Debug print
                # print(f"      👀 Face found at {t}s: X={int(pixel_x)}")
    
    cap.release()
    
    if detected_positions:
        # Ambil rata-rata posisi wajah sepanjang klip
        final_avg = sum(detected_positions) / len(detected_positions)
        print(f"      🎯 Average Face Position: X={int(final_avg)} (from {len(detected_positions)} frames)")
        return final_avg
    else:
        print("      ⚠️ No face detected, using Center Default.")
        return 0.5 * cap.get(cv2.CAP_PROP_FRAME_WIDTH)