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
import whisper  # Library Whisper Local
from google import genai
from google.genai import types
from celery.schedules import crontab

# --- IMPORT DATABASE ---
from app.db.database import SessionLocal
from app.db.models import Project, GeneratedClip, ClipCandidate
# -----------------------

celery_app = Celery(
    "worker",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
    include=['app.tasks.pipeline', 'app.tasks.watcher']
)

# Variable Global untuk model Whisper (Lazy Loading)
whisper_model = None

# ... import tetap sama ...

# ==========================================
# TASK 1: THE ANALYST (Updated Debugging)
# ==========================================
@celery_app.task(bind=True)
def analyze_video_task(self, youtube_url: str):
    task_id = self.request.id
    work_dir = f"downloads/{task_id}"
    os.makedirs(work_dir, exist_ok=True)
    
    print(f"🚀 [Task {task_id}] START: Analyst Mode V10 (Debug & Loose Filter)")
    db = SessionLocal()
    
    try:
        # 1. Create/Update Project
        project = db.query(Project).filter(Project.id == task_id).first()
        if not project:
            new_project = Project(id=task_id, youtube_url=youtube_url, status="analyzing")
            db.add(new_project)
        else:
            project.status = "analyzing"
        db.commit()

        # 2. Download
        self.update_state(state='PROGRESS', meta={'status': 'Downloading...'})
        video_path, duration = _download_video_with_meta(youtube_url, work_dir)
        
        if not video_path: raise Exception("Download failed")

        # 3. Gemini Analysis
        self.update_state(state='PROGRESS', meta={'status': 'AI Mencari Konten Viral...'})
        candidates = _analyze_smart_context(video_path, duration)
        
        if not candidates: raise Exception("Gagal analisa konten viral (Result Kosong)")

        print(f"🔍 Gemini menyarankan {len(candidates)} klip raw. Mulai filtering...")
        
        saved_count = 0
        for i, c in enumerate(candidates):
            s = _time_to_seconds(c.get('start_time', '00:00'))
            e = _time_to_seconds(c.get('end_time', '00:00'))
            dur = e - s
            
            # DEBUG LOG: Tampilkan apa yang diterima
            print(f"   📝 Cek Kandidat #{i+1}: {s}s - {e}s (Durasi: {dur}s) - {c.get('title')}")

            # FILTER LEBIH LONGGAR: Minimal 10 detik (sebelumnya 20/30)
            if dur < 10: 
                print(f"      ⚠️ SKIP: Terlalu pendek (<10s)")
                continue
            if dur > 300:
                print(f"      ⚠️ SKIP: Terlalu panjang (>5m)")
                continue

            # Simpan ke DB
            candidate = ClipCandidate(
                project_id=task_id,
                start_time=s, end_time=e,
                title=c.get('title', 'Untitled'),
                description=c.get('caption', 'No description'), # Pakai caption untuk deskripsi
                viral_score=c.get('score', 85),
                is_rendered=False
            )
            db.add(candidate)
            saved_count += 1
        
        new_project = db.query(Project).filter(Project.id == task_id).first()
        new_project.status = "analysis_completed"
        db.commit()

        print(f"✅ Selesai! {saved_count} draft tersimpan di Database.")
        return {"status": "analysis_completed", "candidates_count": saved_count}

    except Exception as e:
        print(f"🔥 Error: {e}")
        db.rollback()
        project = db.query(Project).filter(Project.id == task_id).first()
        if project: project.status = "failed"; db.commit()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task(bind=True)
def prepare_editor_task(self, candidate_id: int):
    """
    Menyiapkan data untuk Editor:
    1. Membuat video crop 9:16 POLOS (tanpa subtitle).
    2. Menjalankan Whisper untuk dapat JSON Transkrip.
    3. Menyimpan keduanya ke DB.
    """
    print(f"📝 [Editor Prep] Preparing Candidate ID: {candidate_id}")
    db = SessionLocal()
    
    try:
        candidate = db.query(ClipCandidate).filter(ClipCandidate.id == candidate_id).first()
        if not candidate: raise Exception("Candidate not found")
        
        project_id = candidate.project_id
        work_dir = f"downloads/{project_id}"
        video_path = f"{work_dir}/source.mp4"
        
        if not os.path.exists(video_path): raise Exception("Source video missing.")

        # Nama File Draft
        draft_filename = f"draft_{candidate.id}.mp4"
        draft_path = f"{work_dir}/{draft_filename}"
        
        # A. BUAT VIDEO POLOS (CROP ONLY)
        # Reuse logika crop tapi tanpa subtitle filter
        print("   ✂️ Creating Clean Draft Video...")
        segmen = {'start': candidate.start_time, 'end': candidate.end_time}
        _create_clean_crop(video_path, segmen, draft_path)
        
        # B. TRANSKRIPSI WHISPER (JSON)
        print("   🎤 Extracting Transcript JSON...")
        # Ekstrak audio dari draft video biar cepat
        temp_audio = f"{work_dir}/temp_audio_{candidate.id}.wav"
        subprocess.run(['ffmpeg', '-y', '-i', draft_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', temp_audio], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        transcript_json = _transcribe_with_whisper(temp_audio)
        if os.path.exists(temp_audio): os.remove(temp_audio)
        
        # C. SIMPAN KE DB
        candidate.draft_video_path = f"downloads/{project_id}/{draft_filename}"
        candidate.transcript_data = transcript_json
        db.commit()
        
        print(f"   ✅ Editor Data Ready for Candidate #{candidate_id}")
        return {"status": "ready_for_editing", "transcript_len": len(transcript_json)}

    except Exception as e:
        print(f"❌ Editor Prep Error: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()



@celery_app.task(bind=True)
def render_single_clip_task(self, candidate_id: int):
    print(f"🎬 [Render Task] Processing Candidate ID: {candidate_id}")
    db = SessionLocal()
    
    try:
        candidate = db.query(ClipCandidate).filter(ClipCandidate.id == candidate_id).first()
        if not candidate: raise Exception("Candidate not found")
        
        project_id = candidate.project_id
        work_dir = f"downloads/{project_id}"
        video_path = f"{work_dir}/source.mp4"
        
        if not os.path.exists(video_path): raise Exception("File video master hilang.")

        clip_filename = f"render_{candidate.id}.mp4"
        segmen = {'start': candidate.start_time, 'end': candidate.end_time}
        
        # PANGGIL FUNGSI SMART CROP BARU (YANG PAKAI WHISPER)
        result_path = _smart_crop_segment(video_path, segmen, work_dir, clip_filename)
        
        if result_path:
            final_clip = GeneratedClip(
                project_id=project_id,
                file_path=result_path,
                title=candidate.title
            )
            db.add(final_clip)
            candidate.is_rendered = True
            db.commit()
            return {"status": "completed", "path": result_path}
        else:
            raise Exception("Gagal merender video")

    except Exception as e:
        print(f"❌ Render Error: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


# --- HELPER FUNCTIONS (WHISPER INTEGRATION) ---

def _transcribe_with_whisper(audio_path):
    """
    Menggunakan Whisper Local untuk mendapatkan Word-Level Timestamp.
    """
    global whisper_model
    if whisper_model is None:
        print("⏳ Loading Whisper Model (Lazy Load)...")
        whisper_model = whisper.load_model("small")
        print("✅ Whisper Model Loaded!")
    
    print(f"   🎤 Whisper sedang mendengarkan {os.path.basename(audio_path)}...")
    
    # Transkripsi dengan word_timestamps=True (Fitur sakti!)
    result = whisper_model.transcribe(audio_path, word_timestamps=True, fp16=False) # fp16=False biar aman di CPU
    
    # Kita butuh daftar kata-katanya
    words_list = []
    for segment in result['segments']:
        for word in segment['words']:
            words_list.append({
                'start': word['start'],
                'end': word['end'],
                'word': word['word'].strip()
            })
    
    return words_list

def _json_to_srt_one_word(words_json, output_path):
    """
    Konversi data Whisper ke SRT format 'Satu Kata Satu Waktu'.
    """
    def sec_to_srt_fmt(seconds):
        ms = int((seconds % 1) * 1000)
        seconds = int(seconds)
        mins, secs = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"

    with open(output_path, "w", encoding='utf-8') as f:
        counter = 1
        for w in words_json:
            start = sec_to_srt_fmt(w['start'])
            end = sec_to_srt_fmt(w['end'])
            text = w['word']
            
            # Tulis block SRT untuk 1 kata ini
            f.write(f"{counter}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")
            counter += 1
            
    return True

def _smart_crop_segment(video_path, segmen, output_folder, filename):
    start, end = segmen['start'], segmen['end']
    duration = end - start
    
    temp_cut_path = f"{output_folder}/temp_{filename}"
    output_filename = f"{output_folder}/{filename}"
    srt_path = f"{output_folder}/{filename}.srt"

    # 1. CUTTING TEMP VIDEO
    print(f"   ✂️ Cutting temp video ({start}-{end})...")
    subprocess.run(['ffmpeg', '-y', '-ss', str(start), '-t', str(duration), '-i', video_path, '-c', 'copy', temp_cut_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 2. GENERATE SUBTITLE (PAKAI WHISPER)
    try:
        # Kita butuh audio-only untuk Whisper (biar cepat)
        temp_audio_path = f"{output_folder}/temp_audio_{filename}.wav"
        subprocess.run(['ffmpeg', '-y', '-i', temp_cut_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', temp_audio_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Panggil Whisper
        words_data = _transcribe_with_whisper(temp_audio_path)
        
        # Buat SRT Satu Kata
        _json_to_srt_one_word(words_data, srt_path)
        
        # Bersihkan audio temp
        if os.path.exists(temp_audio_path): os.remove(temp_audio_path)
        
    except Exception as e:
        print(f"❌ Whisper Error: {e}. Fallback to dummy sub.")
        _create_srt("Error Subtitle", duration, srt_path)

    # 3. FACE TRACKING
    center_x = _scan_face_average(temp_cut_path)
    cap = cv2.VideoCapture(temp_cut_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    target_width = int(height * 9 / 16)
    x_start = int(center_x - (target_width // 2))
    x_start = max(0, min(x_start, width - target_width))

    print(f"   🔥 Burning Dynamic Subtitles...")
    abs_srt_path = os.path.abspath(srt_path)
    
    # Style Baru: Font Lebih Besar & Kuning Terang (Supaya 1 kata kelihatan jelas)
    # Alignment 10 (Middle Center) atau 2 (Bottom Center). Kita pakai 2 (Bottom).
    style = "Fontname=Liberation Sans,Fontsize=20,PrimaryColour=&H00FFFF,BorderStyle=3,BackColour=&H80000000,Outline=0,Shadow=0,Alignment=2,MarginV=60,Bold=1"

    command = [
        'ffmpeg', '-y',
        '-i', temp_cut_path,
        '-vf', f"crop={target_width}:{height}:{x_start}:0,subtitles='{abs_srt_path}':force_style='{style}',format=yuv420p",
        '-c:v', 'libx264', '-c:a', 'aac', '-b:a', '128k', '-preset', 'ultrafast',
        output_filename
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(temp_cut_path): os.remove(temp_cut_path)
        print(f"   ✅ Sukses: {filename}")
        return output_filename
    except subprocess.CalledProcessError as e:
        print(f"   ❌ FFmpeg Gagal: {e.stderr.decode('utf8')}")
        return None

# --- HELPER LAIN (GEMINI UNTUK ANALISIS) TETAP SAMA ---

def _analyze_smart_context(video_path, duration):
    print(f"   📊 Analisis Gemini (Durasi: {duration}s)")
    try:
        client = genai.Client()
        video_file = client.files.upload(file=video_path)
        
        # Tunggu processing dengan timeout safety
        start_wait = time.time()
        while video_file.state.name == "PROCESSING":
            if time.time() - start_wait > 600: # Timeout 10 menit
                print("❌ Timeout menunggu Gemini process video")
                return None
            time.sleep(5)
            video_file = client.files.get(name=video_file.name)

        if video_file.state.name == "FAILED": 
            print("❌ Video processing failed di sisi Google.")
            return None

        target_clips = max(3, min(15, math.ceil(duration / 120)))
        
        # PROMPT YANG LEBIH STABIL
        prompt = f"""
        You are an AI Video Editor. Analyze this video.
        Task: Find {target_clips} interesting segments (viral clips).
        
        Constraints:
        - Clip duration: 30s - 180s.
        - Language: Use the SAME language as the video audio for titles/captions.
        
        Output Format: JSON List.
        [
            {{
                "start_time": "MM:SS", 
                "end_time": "MM:SS", 
                "title": "Interesting Title", 
                "caption": "Summary"
            }}
        ]
        """
        
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=[video_file, prompt], 
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        
        print(f"   💡 RAW GEMINI RESPONSE: {response.text[:500]}...") # Print 500 char pertama buat debug
        
        parsed = json.loads(response.text)
        if not parsed:
            print("⚠️ Gemini mengembalikan list kosong []")
            return None
            
        return parsed
        
    except Exception as e:
        print(f"❌ Gemini Error Exception: {e}")
        return None

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
                center_x = bbox.xmin + (bbox.width / 2)
                detected_positions.append(center_x * cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    cap.release()
    return sum(detected_positions)/len(detected_positions) if detected_positions else 0.5 * cap.get(cv2.CAP_PROP_FRAME_WIDTH)

def _download_video_with_meta(url, output_folder):
    ydl_opts = {'format': 'bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'outtmpl': f'{output_folder}/source.%(ext)s', 'quiet': True, 'no_warnings': True, 'nocheckcertificate': True, 'socket_timeout': 30,}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return f"{output_folder}/source.mp4", info.get('duration', 0)
    except: return None, 0

def _time_to_seconds(time_str):
    try:
        parts = list(map(int, time_str.split(':')))
        if len(parts) == 2: return parts[0]*60 + parts[1]
        elif len(parts) == 3: return parts[0]*3600 + parts[1]*60 + parts[2]
    except: return 0
    return 0

# --- SCHEDULE ---
celery_app.conf.beat_schedule = {
    'check-youtube-every-hour': {
        'task': 'app.tasks.watcher.run_watcher_task', 
        'schedule': crontab(minute=0), 
    },
}