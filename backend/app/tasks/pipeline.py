import subprocess
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

# Mock Data yang lebih kaya (Simulasi 3 Klip Viral)
MOCK_TRANSCRIPT = {
    "text": "Full transcript text...",
    "segments": [
        # Klip 1: Detik 0 sampai 5
        {"start": 0.0, "end": 5.0, "text": "Clip 1: Bagian Awal."},
        # Klip 2: Detik 5 sampai 10
        {"start": 5.0, "end": 10.0, "text": "Clip 2: Bagian Tengah."},
        # Klip 3: Detik 10 sampai 15
        {"start": 10.0, "end": 15.0, "text": "Clip 3: Bagian Akhir."}
    ]
}

@celery_app.task(bind=True)
def process_video_pipeline(self, youtube_url: str):
    task_id = self.request.id
    work_dir = f"downloads/{task_id}"
    os.makedirs(work_dir, exist_ok=True)
    
    print(f"🚀 [Task {task_id}] Memulai proses V2 (Multi-Clip) untuk: {youtube_url}")

    # 1. DOWNLOAD
    self.update_state(state='PROGRESS', meta={'status': 'Downloading Video...'})
    video_path = _download_video(youtube_url, work_dir)
    if not video_path: return {"status": "failed", "error": "Download failed"}

    # 2. TRANSCRIBE (Disini nanti otak AI bekerja)
    self.update_state(state='PROGRESS', meta={'status': 'AI Analyzing Content...'})
    transcript = _transcribe_audio(video_path)
    
    # 3. SMART CROP LOOP (Memproses SEMUA segmen, bukan cuma satu)
    self.update_state(state='PROGRESS', meta={'status': 'Rendering Multiple Clips...'})
    
    final_clips = []
    # Loop semua segmen yang ditemukan AI
    for i, segmen in enumerate(transcript['segments']):
        clip_name = f"clip_{i+1}.mp4"
        print(f"🔄 Processing Clip #{i+1}: {segmen['text']}")
        
        # Panggil fungsi crop yang baru
        result_path = _smart_crop_segment(video_path, segmen, work_dir, clip_name)
        if result_path:
            final_clips.append(result_path)

    return {
        "status": "completed",
        "original_video": video_path,
        "generated_clips": final_clips # Mengembalikan LIST banyak video
    }

# --- HELPER FUNCTIONS (Fungsi Pembantu) ---

def _download_video(url, output_folder):
    ydl_opts = {
        # Ambil video MP4 dengan tinggi maksimal 1080 pixel (HD), audio m4a
        # [vcodec^=avc1] PENTING: Menghindari codec AV1 yang bikin error di Docker
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

def _smart_crop_segment(video_path, segmen, output_folder, filename):
    start, end = segmen['start'], segmen['end']
    duration = end - start
    output_filename = f"{output_folder}/{filename}"
    
    # 1. Deteksi Wajah
    center_x = _get_face_center(video_path, start + (duration/2))
    
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    # 2. Hitung Crop
    target_width = int(height * 9 / 16)
    x_start = int(center_x - (target_width // 2))
    x_start = max(0, min(x_start, width - target_width))
    
    print(f"   ⚙️ Rendering {filename} via Raw FFmpeg...")

    # 3. Render Menggunakan Subprocess (Raw Command) - LEBIH STABIL
    # Perintah: ffmpeg -y -ss [start] -t [dur] -i [input] -vf [filter] -c:v libx264 -c:a aac [output]
    
    command = [
        'ffmpeg', 
        '-y',                  # Overwrite file jika ada
        '-ss', str(start),     # Start time
        '-t', str(duration),   # Duration
        '-i', video_path,      # Input file
        '-vf', f"crop={target_width}:{height}:{x_start}:0,format=yuv420p", # Filter Crop & Pixel
        '-c:v', 'libx264',     # Video Codec
        '-c:a', 'aac',         # Audio Codec (PENTING: Ini memaksa audio masuk)
        '-b:a', '128k',        # Bitrate Audio
        '-preset', 'ultrafast',
        output_filename
    ]

    try:
        # Jalankan perintah terminal dari Python
        result = subprocess.run(
            command, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        print(f"   ✅ Sukses: {filename}")
        return output_filename
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8') if e.stderr else "Unknown Error"
        print(f"   ❌ FFmpeg Gagal: {error_msg}")
        return None
def _get_face_center(video_path, start_time):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
    mp_face = mp.solutions.face_detection
    
    detected_x = []
    with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_det:
        for _ in range(5): # Cek 5 frame
            success, img = cap.read()
            if not success: break
            # Convert ke RGB karena OpenCV pakai BGR
            results = face_det.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            if results.detections:
                bbox = results.detections[0].location_data.relative_bounding_box
                detected_x.append(bbox.xmin + bbox.width/2)
                
    cap.release()
    # Kalau tidak ada wajah, ambil tengah (0.5)
    avg_x = sum(detected_x)/len(detected_x) if detected_x else 0.5
    return avg_x * cap.get(cv2.CAP_PROP_FRAME_WIDTH)