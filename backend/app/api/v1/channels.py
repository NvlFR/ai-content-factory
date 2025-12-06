from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx

from app.db.database import get_db
from app.db.models import SocialChannel, User
from app.api.v1.auth import verify_jwt_token

router = APIRouter()

YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"


class ChannelResponse(BaseModel):
    id: str
    platform: str
    channel_id: Optional[str]
    channel_name: Optional[str]
    channel_thumbnail: Optional[str]
    is_connected: bool

    class Config:
        from_attributes = True


class VideoItem(BaseModel):
    video_id: str
    title: str
    thumbnail: str
    published_at: str


def get_current_user_from_token(authorization: str, db: Session) -> User:
    """Extract user from JWT token in Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    token = authorization.replace("Bearer ", "")
    payload = verify_jwt_token(token)
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/youtube", response_model=Optional[ChannelResponse])
def get_connected_youtube_channel(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get user's connected YouTube channel"""
    user = get_current_user_from_token(authorization, db)
    
    channel = db.query(SocialChannel).filter(
        SocialChannel.user_id == user.id,
        SocialChannel.platform == "youtube"
    ).first()
    
    if not channel:
        return None
    
    return ChannelResponse(
        id=channel.id,
        platform=channel.platform,
        channel_id=channel.channel_id,
        channel_name=channel.channel_name,
        channel_thumbnail=channel.channel_thumbnail,
        is_connected=channel.is_connected
    )


@router.delete("/youtube")
def disconnect_youtube_channel(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Disconnect YouTube channel (revoke monitoring, keep user account)"""
    user = get_current_user_from_token(authorization, db)
    
    channel = db.query(SocialChannel).filter(
        SocialChannel.user_id == user.id,
        SocialChannel.platform == "youtube"
    ).first()
    
    if channel:
        channel.is_connected = False
        db.commit()
    
    return {"status": "disconnected"}


@router.post("/youtube/reconnect")
async def reconnect_youtube_channel(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Re-enable YouTube channel monitoring"""
    user = get_current_user_from_token(authorization, db)
    
    channel = db.query(SocialChannel).filter(
        SocialChannel.user_id == user.id,
        SocialChannel.platform == "youtube"
    ).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="No YouTube channel found. Please login again with Google.")
    
    channel.is_connected = True
    db.commit()
    
    return {"status": "reconnected", "channel_name": channel.channel_name}


@router.get("/youtube/videos", response_model=List[VideoItem])
async def get_youtube_channel_videos(
    max_results: int = 10,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get latest videos from user's connected YouTube channel"""
    user = get_current_user_from_token(authorization, db)
    
    channel = db.query(SocialChannel).filter(
        SocialChannel.user_id == user.id,
        SocialChannel.platform == "youtube",
        SocialChannel.is_connected == True
    ).first()
    
    if not channel or not channel.channel_id:
        raise HTTPException(status_code=404, detail="No connected YouTube channel found")
    
    # First get the uploads playlist ID
    async with httpx.AsyncClient() as client:
        # Get channel's uploads playlist
        channel_response = await client.get(
            YOUTUBE_CHANNELS_URL,
            params={
                "part": "contentDetails",
                "id": channel.channel_id,
                "key": None  # Will use OAuth token instead
            },
            headers={"Authorization": f"Bearer {channel.access_token}"}
        )
        channel_data = channel_response.json()
        
        if "items" not in channel_data or len(channel_data["items"]) == 0:
            raise HTTPException(status_code=404, detail="Could not fetch channel data")
        
        uploads_playlist_id = channel_data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # Get videos from uploads playlist
        videos_response = await client.get(
            YOUTUBE_PLAYLIST_ITEMS_URL,
            params={
                "part": "snippet",
                "playlistId": uploads_playlist_id,
                "maxResults": max_results
            },
            headers={"Authorization": f"Bearer {channel.access_token}"}
        )
        videos_data = videos_response.json()
    
    if "items" not in videos_data:
        return []
    
    videos = []
    for item in videos_data["items"]:
        snippet = item["snippet"]
        videos.append(VideoItem(
            video_id=snippet["resourceId"]["videoId"],
            title=snippet["title"],
            thumbnail=snippet["thumbnails"]["medium"]["url"] if "medium" in snippet["thumbnails"] else snippet["thumbnails"]["default"]["url"],
            published_at=snippet["publishedAt"]
        ))
    
    return videos
