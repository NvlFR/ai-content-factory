import httpx
import asyncio
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import SocialChannel

from app.tasks.pipeline import celery_app

YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"


def refresh_access_token(channel: SocialChannel, db: Session) -> str:
    """Refresh expired access token using refresh token"""
    import os
    
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    
    if not channel.refresh_token:
        return None
    
    try:
        import requests
        response = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": channel.refresh_token,
                "grant_type": "refresh_token"
            }
        )
        tokens = response.json()
        
        if "access_token" in tokens:
            channel.access_token = tokens["access_token"]
            db.commit()
            return tokens["access_token"]
    except Exception as e:
        print(f"   ❌ Failed to refresh token: {e}")
    
    return None


def get_latest_video_from_playlist(access_token: str, playlist_id: str) -> dict:
    """Fetch the latest video from a YouTube playlist using sync request"""
    import requests
    
    response = requests.get(
        YOUTUBE_PLAYLIST_ITEMS_URL,
        params={
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": 1
        },
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    data = response.json()
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" in data and len(data["items"]) > 0:
        item = data["items"][0]
        snippet = item["snippet"]
        return {
            "video_id": snippet["resourceId"]["videoId"],
            "title": snippet["title"],
            "video_url": f"https://www.youtube.com/watch?v={snippet['resourceId']['videoId']}"
        }
    
    return None


@celery_app.task
def run_watcher_task():
    print("🕵️‍♂️  WATCHER: Memulai patroli channel YouTube yang terhubung...")
    check_connected_channels_for_new_videos()


def check_connected_channels_for_new_videos():
    db = SessionLocal()
    try:
        # Get all connected YouTube channels
        channels = db.query(SocialChannel).filter(
            SocialChannel.platform == "youtube",
            SocialChannel.is_connected == True,
            SocialChannel.uploads_playlist_id != None
        ).all()
        
        if not channels:
            print("   💤 Tidak ada channel YouTube yang terhubung untuk dipantau.")
            return

        for channel in channels:
            print(f"   📡 Mengecek channel: {channel.channel_name} (User: {channel.user_id[:8]}...)...")
            
            if not channel.uploads_playlist_id:
                print("      ⚠️ Uploads playlist ID tidak tersedia, skip.")
                continue
            
            # Try to get latest video
            result = get_latest_video_from_playlist(channel.access_token, channel.uploads_playlist_id)
            
            # Handle token expiration
            if result and "error" in result:
                error = result["error"]
                if error.get("code") == 401:
                    print("      🔄 Token expired, mencoba refresh...")
                    new_token = refresh_access_token(channel, db)
                    if new_token:
                        result = get_latest_video_from_playlist(new_token, channel.uploads_playlist_id)
                    else:
                        print("      ❌ Gagal refresh token, skip channel ini.")
                        continue
                else:
                    print(f"      ❌ API Error: {error.get('message', 'Unknown error')}")
                    continue
            
            if not result or "error" in result:
                print("      ⚠️ Gagal mengambil video terbaru.")
                continue
            
            video_id = result["video_id"]
            video_url = result["video_url"]
            video_title = result["title"]
            
            # Check if this is a new video
            if channel.last_video_id != video_id:
                print(f"      🔥 VIDEO BARU DETECTED: {video_title}")
                print(f"      🚀 Memicu Analisis Otomatis...")
                
                # Trigger analysis task
                from app.tasks.pipeline import analyze_video_task
                analyze_video_task.delay(video_url)
                
                # Update last_video_id in database
                channel.last_video_id = video_id
                db.commit()
            else:
                print("      ✅ Belum ada upload baru (Video terakhir masih sama).")
                
    except Exception as e:
        print(f"❌ Error Watcher: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        print("🏁 Patroli selesai.\n")


if __name__ == "__main__":
    check_connected_channels_for_new_videos()
