import json
import ffmpeg
import cv2
import mediapipe as mp
import os

VIDEO_PATH = "downloads/jNQXAC9IVRw.mp4"
TRANSCRIPT_PATH = "downloads/transcript.json"
OUTPUT_FOLDER = "downloads/clips"

def get_face_center(video_path, start_time, duration):
    """
    Fungsi Pintar: Mencari koordinat wajah rata-rata di segmen video.
    Jika tidak ada wajah, default ke tengah video.
    """
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
    
    mp_face_detection = mp.solutions.face_detection
    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    x_centers = []
    frames_to_check = 10 # Cek 10 frame saja supaya cepat
    
    with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
        for _ in range(frames_to_check):
            success, image = cap.read()
            if not success: break
            
            # Ubah warna ke RGB karena MediaPipe butuh RGB
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = face_detection.process(image)
            
            if results.detections:
                for detection in results.detections:
                    # Ambil kotak wajah
                    bboxC = detection.location_data.relative_bounding_box
                    center_x = bboxC.xmin + (bboxC.width / 2)
                    x_centers.append(center_x)
    
    cap.release()
    
    # Jika ketemu wajah, ambil rata-rata posisinya. Jika tidak, ambil tengah (0.5)
    final_center_x = sum(x_centers) / len(x_centers) if x_centers else 0.5
    print(f"👁️ Deteksi Wajah: {'Ketemu' if x_centers else 'Tidak (Pakai Tengah)'} | Posisi X: {final_center_x:.2f}")
    
    # Konversi posisi relatif (0.0 - 1.0) ke pixel
    pixel_center_x = int(final_center_x * video_width)
    return pixel_center_x, video_width, video_height

def create_portrait_clip():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    # 1. Load Data Transkrip
    with open(TRANSCRIPT_PATH, 'r') as f:
        data = json.load(f)
    
    # Kita ambil segmen ke-2 (Index 1) tentang "Long Trunks" sebagai contoh
    segmen = data['segments'][1] 
    start = segmen['start']
    end = segmen['end']
    text = segmen['text']
    
    print(f"🎬 Memproses Klip: '{text}'")
    print(f"⏱️ Durasi: {start}s sampai {end}s")

    # 2. Cari Titik Potong (Smart Crop Calculation)
    center_x, width, height = get_face_center(VIDEO_PATH, start, end - start)
    
    # Target: 9:16 Rasio
    target_height = height
    target_width = int(target_height * 9 / 16)
    
    # Hitung koordinat X supaya kotak crop ada di tengah wajah
    x_start = center_x - (target_width // 2)
    
    # Pastikan kotak crop tidak keluar batas kiri/kanan video
    if x_start < 0: x_start = 0
    if x_start + target_width > width: x_start = width - target_width

    print(f"✂️  Cropping area: X={x_start}, Y=0, W={target_width}, H={target_height}")

    # 3. Eksekusi FFmpeg
    output_filename = f"{OUTPUT_FOLDER}/clip_long_trunks.mp4"
    
    try:
        (
            ffmpeg
            .input(VIDEO_PATH, ss=start, t=(end-start)) # Potong durasi
            .filter('crop', target_width, target_height, x_start, 0) # Potong layar
            .output(output_filename, vcodec='libx264', acodec='aac')
            .overwrite_output()
            .run(quiet=True)
        )
        print(f"\n✅ Klip Berhasil Dibuat!")
        print(f"📂 Lokasi: {output_filename}")
    except ffmpeg.Error as e:
        print(f"❌ FFmpeg Error: {e.stderr}")

if __name__ == "__main__":
    create_portrait_clip()