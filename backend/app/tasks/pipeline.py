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
import re
from google import genai
from google.genai import types

# --- IMPORT DATABASE ---
from app.db.database import SessionLocal
from app.db.models import Project, GeneratedClip
# -----------------------

from celery.schedules import crontab

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
    
    print(f"🚀 [Task {task_id}] Memulai Proses V5 (Save to DB)")

    # 1. BUKA KONEKSI DB
    db = SessionLocal()
    
    try:
        # 2. CATAT PROJECT BARU (Status: Processing)
        new_project = Project(id=task_id, youtube_url=youtube_url, status="processing")
        db.add(new_project)
        db.commit()

        # --- LOGIC PROCESSING DIMULAI ---
        
        # A. DOWNLOAD
        self.update_state(state='PROGRESS', meta={'status': 'Downloading Video...'})
        video_path = _download_video(youtube_url, work_dir)
        if not video_path: 
            raise Exception("Download failed")

        # B. GEMINI ANALYSIS
        self.update_state(state='PROGRESS', meta={'status': 'Gemini is watching...'})
        analysis_result = _analyze_with_gemini_official(video_path)
        
        if not analysis_result:
            raise Exception("Gemini Analysis Failed")

        # C. RENDER LOOP
        self.update_state(state='PROGRESS', meta={'status': 'Rendering Clips...'})
        
        final_clips = []
        for i, clip in enumerate(analysis_result):
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
                
                # 3. CATAT CLIP KE DB (Langsung simpan begitu jadi)
                new_clip = GeneratedClip(
                    project_id=task_id, 
                    file_path=result_path,
                    title=title
                )
                db.add(new_clip)
                db.commit()

        # 4. UPDATE STATUS JADI COMPLETED
        new_project.status = "completed"
        # Opsional: Simpan judul video asli jika ada (nanti bisa diambil dari yt-dlp)
        db.commit()

        return {
            "status": "completed",
            "original_video": video_path,
            "generated_clips": final_clips
        }

    except Exception as e:
        # KALAU ERROR, UPDATE STATUS DB JADI FAILED
        print(f"🔥 Critical Error: {e}")
        db.rollback() # Batalkan perubahan terakhir
        # Query ulang object karena sesi mungkin stale setelah rollback
        project = db.query(Project).filter(Project.id == task_id).first()
        if project:
            project.status = "failed"
            db.commit()
        return {"status": "failed", "error": str(e)}
        
    finally:
        # TUTUP KONEKSI DB (WAJIB)
        db.close()

# --- HELPER FUNCTIONS (SAMA SEPERTI SEBELUMNYA) ---

def _analyze_with_gemini_official(video_path):
    print("🤖 Phase 1: Global Analysis...")
    try:
        client = genai.Client()
        video_file = client.files.upload(file=video_path)
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = client.files.get(name=video_file.name)

        if video_file.state.name == "FAILED": return None

        prompt = """
        You are a viral content editor. 
        Identify 3 distinct, engaging segments (15-60 seconds).
        Return JSON List: [{"start_time": "MM:SS", "end_time": "MM:SS", "title": "Topic", "caption": "Exact spoken words"}]
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[video_file, prompt],
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        return json.loads(response.text)

    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        return None

def _generate_precise_json_subs(video_clip_path):
    print(f"   🎤 Transcribing clip to JSON...")
    try:
        time.sleep(2) 
        client = genai.Client()
        clip_file = client.files.upload(file=video_clip_path)
        
        while clip_file.state.name == "PROCESSING":
            time.sleep(1)
            clip_file = client.files.get(name=clip_file.name)

        prompt = """
        Listen carefully. Transcribe the audio perfectly.
        Break the text into short segments (max 4-5 words) for dynamic captions.
        Return output ONLY as JSON List:
        [
          {"start": 0.0, "end": 1.5, "text": "Halo semuanya"},
          {"start": 1.5, "end": 3.0, "text": "balik lagi disini"}
        ]
        Use float for seconds.
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[clip_file, prompt],
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ Gagal Transkrip JSON: {e}")
        return None

def _json_to_srt_file(subs_json, output_path):
    def sec_to_srt_fmt(seconds):
        ms = int((seconds % 1) * 1000)
        seconds = int(seconds)
        mins, secs = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"

    with open(output_path, "w", encoding='utf-8') as f:
        for i, line in enumerate(subs_json):
            start = sec_to_srt_fmt(line['start'])
            end = sec_to_srt_fmt(line['end'])
            text = line['text']
            f.write(f"{i+1}\n{start} --> {end}\n{text}\n\n")
    return True

def _smart_crop_segment(video_path, segmen, output_folder, filename):
    start, end = segmen['start'], segmen['end']
    duration = end - start
    
    temp_cut_path = f"{output_folder}/temp_{filename}"
    output_filename = f"{output_folder}/{filename}"
    srt_path = f"{output_folder}/{filename}.srt"

    print(f"   ✂️ Cutting temp video ({start}-{end})...")
    subprocess.run(['ffmpeg', '-y', '-ss', str(start), '-t', str(duration), '-i', video_path, '-c', 'copy', temp_cut_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    subs_json = _generate_precise_json_subs(temp_cut_path)
    if subs_json: _json_to_srt_file(subs_json, srt_path)
    else: _create_srt("Subtitle Error", duration, srt_path)

    center_x = _scan_face_average(temp_cut_path)
    cap = cv2.VideoCapture(temp_cut_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    target_width = int(height * 9 / 16)
    x_start = int(center_x - (target_width // 2))
    x_start = max(0, min(x_start, width - target_width))

    print(f"   🔥 Burning Subtitles...")
    abs_srt_path = os.path.abspath(srt_path)
    style = "Fontname=Liberation Sans,Fontsize=14,PrimaryColour=&HFFFFFF,BorderStyle=3,BackColour=&H80000000,Outline=0,Shadow=0,Alignment=2,MarginV=25,Bold=1"

    command = ['ffmpeg', '-y', '-i', temp_cut_path, '-vf', f"crop={target_width}:{height}:{x_start}:0,subtitles='{abs_srt_path}':force_style='{style}',format=yuv420p", '-c:v', 'libx264', '-c:a', 'aac', '-b:a', '128k', '-preset', 'ultrafast', output_filename]

    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(temp_cut_path): os.remove(temp_cut_path)
        print(f"   ✅ Sukses: {filename}")
        return output_filename
    except subprocess.CalledProcessError as e:
        print(f"   ❌ FFmpeg Gagal: {e.stderr.decode('utf8')}")
        return None

def _create_srt(text, duration, output_path):
    content = f"1\n00:00:00,000 --> 00:00:05,000\n{text}"
    with open(output_path, "w", encoding='utf-8') as f: f.write(content)

def _scan_face_average(video_path):
    cap = cv2.VideoCapture(video_path)
    mp_face = mp.solutions.face_detection
    detected_positions = []
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(total_frames / 10))
    with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.4) as face_det:
        for i in range(0, total_frames, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
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

def _time_to_seconds(time_str):
    try:
        parts = list(map(int, time_str.split(':')))
        if len(parts) == 2: return parts[0] * 60 + parts[1]
        elif len(parts) == 3: return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except: return 0.0

def _download_video(url, output_folder):
    ydl_opts = {'format': 'bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'outtmpl': f'{output_folder}/source.%(ext)s', 'quiet': True, 'no_warnings': True, 'nocheckcertificate': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            return f"{output_folder}/source.mp4"
    except Exception as e:
        print(f"❌ Download Error: {e}")
        return None

# --- SETUP JADWAL CRONJOB ---

# Tambahkan konfigurasi beat di app celery yang sudah ada
celery_app.conf.beat_schedule = {
    'check-youtube-every-hour': {
        'task': 'app.tasks.watcher.run_watcher_task', # Kita butuh wrapper task
        'schedule': crontab(minute=0), # Jalan setiap jam menit ke-0 (jam 1:00, 2:00, dst)
        # 'schedule': 60.0, # ATAU: Jalan setiap 60 detik (untuk testing cepat)
    },
}