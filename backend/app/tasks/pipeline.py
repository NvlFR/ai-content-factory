from celery import Celery
import os
import yt_dlp
import cv2
import mediapipe as mp
import ffmpeg
import json
from openai import OpenAI

# Konfigurasi Celery
celery_app = Celery(
    "worker",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

# Mock Data untuk hemat kuota (Bisa diganti False jika saldo sudah ada)
USE_MOCK_AI = True

MOCK_TRANSCRIPT = {
    "text": "All right, so here we are in front of the elephants.",
    "segments": [
        {"start": 0.0, "end": 4.5, "text": "Opening Scene"},
        {"start": 4.5, "end": 9.5, "text": "The cool thing about these guys..."},
    ]
}

@celery_app.task(bind=True)
def process_video_pipeline(self, youtube_url: str):
    """
    Task Utama: Menjalankan seluruh proses dari Download sampai Crop.
    """
    task_id = self.request.id
    work_dir = f"downloads/{task_id}"
    os.makedirs(work_dir, exist_ok=True)
    
    print(f"🚀 [Task {task_id}] Memulai proses untuk: {youtube_url}")

    # --- STEP 1: DOWNLOAD ---
    self.update_state(state='PROGRESS', meta={'status': 'Downloading Video...'})
    video_path = _download_video(youtube_url, work_dir)
    if not video_path:
        return {"status": "failed", "error": "Download failed"}

    # --- STEP 2: TRANSCRIBE ---
    self.update_state(state='PROGRESS', meta={'status': 'Transcribing Audio...'})
    transcript = _transcribe_audio(video_path)
    
    # --- STEP 3: ANALYZE & CROP ---
    self.update_state(state='PROGRESS', meta={'status': 'Analyzing & Cropping...'})
    clips = _smart_crop(video_path, transcript, work_dir)

    return {
        "status": "completed",
        "original_video": video_path,
        "generated_clips": clips
    }

# --- HELPER FUNCTIONS (Fungsi Pembantu) ---

def _download_video(url, output_folder):
    ydl_opts = {
        # Ambil video MP4 dengan tinggi maksimal 1080 pixel (HD), audio m4a
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
    if USE_MOCK_AI:
        print("🤖 Menggunakan Mock Transkrip")
        return MOCK_TRANSCRIPT
    
    # Jika pakai OpenAI Asli
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    with open(video_path, "rb") as audio:
        res = client.audio.transcriptions.create(
            model="whisper-1", file=audio, response_format="verbose_json"
        )
    return res

def _smart_crop(video_path, transcript, output_folder):
    generated_files = []
    
    # Ambil 1 segmen pertama saja untuk demo
    segmen = transcript['segments'][1] if len(transcript['segments']) > 1 else transcript['segments'][0]
    
    start, end = segmen['start'], segmen['end']
    print(f"✂️ Cropping segmen: {start}s - {end}s")
    
    # Logika deteksi wajah (Sederhana)
    center_x = _get_face_center(video_path, start)
    
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    # Hitung crop 9:16
    target_width = int(height * 9 / 16)
    x_start = int(center_x - (target_width // 2))
    x_start = max(0, min(x_start, width - target_width)) # Clamp agar tidak keluar batas
    
    output_filename = f"{output_folder}/clip_final.mp4"
    
    print(f"⚙️ FFmpeg Config: Crop X={x_start}, W={target_width}, H={height}")

    try:
        # --- PERBAIKAN UTAMA DI SINI ---
        # Kita chaining filter secara eksplisit: Input -> Crop -> Format Pixel -> Output
        stream = ffmpeg.input(video_path, ss=start, t=(end-start))
        stream = stream.filter('crop', target_width, height, x_start, 0)
        
        #         # Paksa format yuv420p agar kompatibel dengan Browser/QuickTime/Android
        stream = stream.filter('format', 'yuv420p')
        
        stream = stream.output(output_filename, vcodec='libx264', acodec='aac', preset='fast')
        
        # Jalankan dengan capture_stderr agar kita bisa baca errornya kalau gagal
        stream.overwrite_output().run(capture_stderr=True)
        
        generated_files.append(output_filename)
        print(f"✅ Render Berhasil: {output_filename}")

    except ffmpeg.Error as e:
        # Tampilkan detail error yang sebenarnya (Bukan cuma 'ffmpeg error')
        error_message = e.stderr.decode('utf8') if e.stderr else "Unknown error"
        print(f"❌ FFmpeg Gagal Total!")
        print(f"🔍 Detail Error:\n{error_message}")
        
    return generated_files

def _get_face_center(video_path, start_time):
    # (Versi ringkas dari logika test_crop.py)
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
    mp_face = mp.solutions.face_detection
    
    detected_x = []
    with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_det:
        for _ in range(5): # Cek 5 frame
            success, img = cap.read()
            if not success: break
            results = face_det.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            if results.detections:
                bbox = results.detections[0].location_data.relative_bounding_box
                detected_x.append(bbox.xmin + bbox.width/2)
                
    cap.release()
    avg_x = sum(detected_x)/len(detected_x) if detected_x else 0.5
    return avg_x * cap.get(cv2.CAP_PROP_FRAME_WIDTH)