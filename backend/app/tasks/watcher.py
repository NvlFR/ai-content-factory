import feedparser
import time
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import MonitoredChannel
from app.tasks.pipeline import process_video_pipeline, celery_app # Import app

# Bungkus jadi Task Celery
@celery_app.task
def run_watcher_task():
    print("🕵️‍♂️  WATCHER: Memulai patroli otomatis...")
    check_for_new_videos()

def check_for_new_videos():
    print("🕵️‍♂️  WATCHER: Memulai patroli channel...")
    
    db = SessionLocal()
    try:
        # 1. Ambil semua channel yang aktif
        channels = db.query(MonitoredChannel).filter(MonitoredChannel.is_active == True).all()
        
        if not channels:
            print("   💤 Tidak ada channel untuk dipantau.")
            return

        for channel in channels:
            print(f"   📡 Mengecek: {channel.name}...")
            
            # 2. Baca RSS Feed
            feed = feedparser.parse(channel.rss_url)
            
            if not feed.entries:
                print("      ⚠️ Gagal baca feed atau kosong.")
                continue

            # Ambil video paling atas (terbaru)
            latest_video = feed.entries[0]
            video_id = latest_video.yt_videoid
            video_url = latest_video.link
            video_title = latest_video.title

            # 3. Cek apakah ini video baru?
            if channel.last_video_id != video_id:
                print(f"      🔥 VIDEO BARU DETECTED: {video_title}")
                print(f"      🚀 Memicu Worker untuk memproses...")
                
                # --- TRIGGER OTOMATIS ---
                process_video_pipeline.delay(video_url)
                
                # Update Database agar tidak diproses ulang nanti
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
    # Script ini akan berjalan sekali jalan (One-off)
    # Nanti bisa kita pasang di Cronjob atau Loop
    check_for_new_videos()