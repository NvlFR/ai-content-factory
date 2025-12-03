import feedparser
import time
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import MonitoredChannel

# 1. IMPORT CELERY APP (Wajib untuk decorator)
from app.tasks.pipeline import celery_app

# Bungkus jadi Task Celery agar bisa dijadwalkan oleh Beat
@celery_app.task
def run_watcher_task():
    print("🕵️‍♂️  WATCHER: Memulai patroli otomatis...")
    check_for_new_videos()

def check_for_new_videos():
    db = SessionLocal()
    try:
        # Ambil semua channel yang aktif
        channels = db.query(MonitoredChannel).filter(MonitoredChannel.is_active == True).all()
        
        if not channels:
            print("   💤 Tidak ada channel untuk dipantau.")
            return

        for channel in channels:
            print(f"   📡 Mengecek: {channel.name}...")
            
            # Baca RSS Feed
            feed = feedparser.parse(channel.rss_url)
            
            if not feed.entries:
                print("      ⚠️ Gagal baca feed atau kosong.")
                continue

            # Ambil video paling atas (terbaru)
            latest_video = feed.entries[0]
            video_id = latest_video.yt_videoid
            video_url = latest_video.link
            video_title = latest_video.title

            # Cek apakah ini video baru?
            if channel.last_video_id != video_id:
                print(f"      🔥 VIDEO BARU DETECTED: {video_title}")
                print(f"      🚀 Memicu Analisis Otomatis (Draft Mode)...")
                
                # 2. UPDATE: Panggil Task Analisis (Bukan Render Langsung)
                # Gunakan Lazy Import untuk menghindari Circular Error
                from app.tasks.pipeline import analyze_video_task
                
                analyze_video_task.delay(video_url)
                
                # Update Database
                channel.last_video_id = video_id
                db.commit()
            else:
                print("      ✅ Belum ada update (Video terakhir masih sama).")
                
    except Exception as e:
        print(f"❌ Error Watcher: {e}")
    finally:
        db.close()
        print("🏁 Patroli selesai.\n")

if __name__ == "__main__":
    check_for_new_videos()