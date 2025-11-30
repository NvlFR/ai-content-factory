import yt_dlp
import os

# URL Video Pendek untuk test (Durasi < 1 menit supaya hemat kuota & cepat)
TEST_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw" # "Me at the zoo" - Video pertama di YouTube

def download_video(url):
    print(f"🚀 Memulai download: {url}")
    
    # Konfigurasi yt-dlp
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # Prioritas MP4
        'outtmpl': 'downloads/%(id)s.%(ext)s', # Simpan di folder downloads, nama file = ID video
        'quiet': False,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            print(f"✅ Download Sukses!")
            print(f"📂 Lokasi File: {filename}")
            print(f"⏱️ Durasi: {info.get('duration')} detik")
            return filename
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

if __name__ == "__main__":
    # Cek apakah folder downloads ada
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
        
    download_video(TEST_URL)