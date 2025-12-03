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
import math
from google import genai
from google.genai import types
from celery.schedules import crontab

# --- IMPORT DATABASE ---
from app.db.database import SessionLocal
from app.db.models import Project, GeneratedClip, ClipCandidate
# -----------------------

# Konfigurasi Celery
celery_app = Celery(
    "worker",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

# ==========================================
# TASK 1: THE ANALYST (Cuma Download & Mikir)
# ==========================================
@celery_app.task(bind=True)
def analyze_video_task(self, youtube_url: str):
    task_id = self.request.id
    work_dir = f"downloads/{task_id}"
    os.makedirs(work_dir, exist_ok=True)
    
    print(f"🚀 [Task {task_id}] START: Analyst Mode (No Rendering Yet)")
    db = SessionLocal()
    
    try:
        # 1. Create Project
        new_project = Project(id=task_id, youtube_url=youtube_url, status="analyzing")
        db.add(new_project)
        db.commit()

        # 2. Download
        self.update_state(state='PROGRESS', meta={'status': 'Downloading...'})
        video_path, duration = _download_video_with_meta(youtube_url, work_dir)
        
        if not video_path: 
            raise Exception("Download failed")

        # 3. Gemini Analysis (Mencari Kandidat)
        self.update_state(state='PROGRESS', meta={'status': 'AI Analyzing Context...'})
        candidates = _analyze_smart_context(video_path, duration)
        
        if not candidates:
            raise Exception("No viral clips found")

        # 4. Save Candidates to DB (DRAFT MODE)
        print(f"💾 Saving {len(candidates)} candidates to Database...")
        for c in candidates:
            candidate = ClipCandidate(
                project_id=task_id,
                start_time=_time_to_seconds(c.get('start_time', '00:00')),
                end_time=_time_to_seconds(c.get('end_time', '00:00')),
                title=c.get('title', 'Untitled'),
                description=c.get('caption', 'No description'), # Pakai caption sbg deskripsi sementara
                viral_score=85, # Default score, nanti bisa minta Gemini nilai
                is_rendered=False
            )
            db.add(candidate)
        
        new_project.status = "analysis_completed" # Status baru: Menunggu user memilih
        db.commit()

        return {"status": "analysis_completed", "candidates_count": len(candidates)}

    except Exception as e:
        print(f"🔥 Error: {e}")
        db.rollback()
        project = db.query(Project).filter(Project.id == task_id).first()
        if project:
            project.status = "failed"
            db.commit()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()

# ==========================================
# TASK 2: THE RENDERER (Eksekusi Pilihan User)
# ==========================================
@celery_app.task(bind=True)
def render_single_clip_task(self, candidate_id: int):
    """
    Dipanggil saat user menekan tombol 'RENDER' di Dashboard.
    """
    print(f"🎬 [Render Task] Processing Candidate ID: {candidate_id}")
    db = SessionLocal()
    
    try:
        # 1. Ambil Data Kandidat
        candidate = db.query(ClipCandidate).filter(ClipCandidate.id == candidate_id).first()
        if not candidate: raise Exception("Candidate not found")
        
        project_id = candidate.project_id
        work_dir = f"downloads/{project_id}"
        video_path = f"{work_dir}/source.mp4"
        
        # Validasi file source masih ada?
        if not os.path.exists(video_path):
            raise Exception("Source video missing. Please re-analyze.")

        clip_filename = f"render_{candidate.id}.mp4"
        
        # 2. Render (Logic V5 yang sudah sempurna)
        segmen = {'start': candidate.start_time, 'end': candidate.end_time}
        
        # Reuse fungsi smart crop yang sudah bagus kemarin
        result_path = _smart_crop_segment(video_path, segmen, work_dir, clip_filename)
        
        if result_path:
            # 3. Simpan ke Tabel GeneratedClip (Hasil Jadi)
            final_clip = GeneratedClip(
                project_id=project_id,
                file_path=result_path,
                title=candidate.title
            )
            db.add(final_clip)
            
            # Tandai kandidat sudah dirender
            candidate.is_rendered = True
            db.commit()
            return {"status": "completed", "path": result_path}
        else:
            raise Exception("Rendering process failed")

    except Exception as e:
        print(f"❌ Render Error: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


# --- HELPER FUNCTIONS (CORE ENGINE V5 - FULLY PRESERVED) ---

def _download_video_with_meta(url, output_folder):
    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f'{output_folder}/source.%(ext)s',
        'quiet': True, 'no_warnings': True, 'nocheckcertificate': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return f"{output_folder}/source.mp4", info.get('duration', 0)
    except Exception as e:
        print(f"❌ Download Error: {e}")
        return None, 0

def _analyze_smart_context(video_path, duration):
    print(f"   📊 Analisis Video (Durasi: {duration}s)")
    try:
        client = genai.Client()
        video_file = client.files.upload(file=video_path)
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = client.files.get(name=video_file.name)

        if video_file.state.name == "FAILED": return None

        # RUMUS DINAMIS: 1 klip tiap 3 menit (180s), min 3 max 15
        target_clips = max(3, min(15, math.ceil(duration / 180)))
        print(f"   🎯 Target: Mencari {target_clips} klip...")

        prompt = f"""
        You are a Master Video Editor. Analyze this video deeply.
        Find exactly {target_clips} segments that are VIRAL WORTHY.
        
        RULES:
        1. DURATION: Flexible. Can be as short as 40 seconds, or as long as 3 minutes.
           - If a topic is short & punchy -> keep it short (40-60s).
           - If a story needs depth -> keep it long (up to 3 mins).
           DO NOT cut a story in the middle. Capture the FULL context.
        
        2. HOOK: The clip MUST start with a strong sentence/reaction (The Hook).

        OUTPUT JSON:
        [
            {{
                "start_time": "MM:SS", 
                "end_time": "MM:SS", 
                "title": "Clickbait Title", 
                "caption": "Short summary/reason why this is viral"
            }}
        ]
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
    # Jeda untuk menghindari Rate Limit
    time.sleep(3) 
    try:
        client = genai.Client()
        clip_file = client.files.upload(file=video_clip_path)
        while clip_file.state.name == "PROCESSING":
            time.sleep(1)
            clip_file = client.files.get(name=clip_file.name)

        prompt = """
        Transcribe audio perfectly. Break text into very short segments (3-5 words max) for fast subtitles.
        Return JSON List: [{"start": 0.0, "end": 1.2, "text": "Hello world"}]
        """
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=[clip_file, prompt], 
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        return json.loads(response.text)
    except: return None

def _json_to_srt_file(subs_json, output_path):
    def sec_to_srt_fmt(seconds):
        ms = int((seconds % 1) * 1000); seconds = int(seconds)
        mins, secs = divmod(seconds, 60); hrs, mins = divmod(mins, 60)
        return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"
    with open(output_path, "w", encoding='utf-8') as f:
        for i, line in enumerate(subs_json):
            f.write(f"{i+1}\n{sec_to_srt_fmt(line['start'])} --> {sec_to_srt_fmt(line['end'])}\n{line['text']}\n\n")
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
    else: _create_srt("Subtitle Unavailable", duration, srt_path)

    center_x = _scan_face_average(temp_cut_path)
    cap = cv2.VideoCapture(temp_cut_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
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
        return output_filename
    except: return None

def _create_srt(text, duration, output_path):
    with open(output_path, "w", encoding='utf-8') as f: f.write(f"1\n00:00:00,000 --> 00:00:05,000\n{text}")

def _scan_face_average(video_path):
    cap = cv2.VideoCapture(video_path); mp_face = mp.solutions.face_detection; detected_positions = []
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); step = max(1, int(total_frames / 10))
    with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.4) as face_det:
        for i in range(0, total_frames, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i); success, img = cap.read()
            if not success: continue
            results = face_det.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            if results.detections:
                bbox = results.detections[0].location_data.relative_bounding_box
                detected_positions.append((bbox.xmin + bbox.width/2) * cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    cap.release()
    return sum(detected_positions)/len(detected_positions) if detected_positions else 0.5 * cap.get(cv2.CAP_PROP_FRAME_WIDTH)

def _time_to_seconds(time_str):
    try:
        parts = list(map(int, time_str.split(':')))
        if len(parts) == 2: return parts[0]*60 + parts[1]
        elif len(parts) == 3: return parts[0]*3600 + parts[1]*60 + parts[2]
    except: return 0
    return 0

# --- SETUP JADWAL CRONJOB ---
celery_app.conf.beat_schedule = {
    'check-youtube-every-hour': {
        'task': 'app.tasks.watcher.run_watcher_task', 
        'schedule': crontab(minute=0), 
    },
}