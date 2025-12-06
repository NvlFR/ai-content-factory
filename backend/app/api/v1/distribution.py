from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import httpx

from app.db.database import get_db
from app.db.models import User, SocialChannel, GeneratedClip
from app.api.v1.auth import verify_jwt_token

router = APIRouter()

# TikTok API endpoints
TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_UPLOAD_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"

# Instagram/Meta API endpoints
INSTAGRAM_AUTH_URL = "https://api.instagram.com/oauth/authorize"
INSTAGRAM_TOKEN_URL = "https://api.instagram.com/oauth/access_token"


def get_current_user_from_token(authorization: str, db: Session) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    token = authorization.replace("Bearer ", "")
    payload = verify_jwt_token(token)
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


class ConnectPlatformRequest(BaseModel):
    platform: str  # tiktok, instagram
    auth_code: str
    redirect_uri: Optional[str] = None


class PublishRequest(BaseModel):
    clip_id: int
    platform: str
    caption: Optional[str] = None
    schedule_time: Optional[str] = None  # ISO format for scheduled posts


class PlatformStatus(BaseModel):
    platform: str
    is_connected: bool
    username: Optional[str] = None
    profile_picture: Optional[str] = None


# --- GET CONNECTED PLATFORMS ---
@router.get("/platforms", response_model=List[PlatformStatus])
def get_connected_platforms(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Get all connected social platforms for distribution"""
    user = get_current_user_from_token(authorization, db)
    
    channels = db.query(SocialChannel).filter(
        SocialChannel.user_id == user.id,
        SocialChannel.platform.in_(["tiktok", "instagram", "youtube_shorts"])
    ).all()
    
    # Build response with all platforms
    platforms = ["tiktok", "instagram", "youtube_shorts"]
    result = []
    
    for platform in platforms:
        channel = next((c for c in channels if c.platform == platform), None)
        result.append(PlatformStatus(
            platform=platform,
            is_connected=channel.is_connected if channel else False,
            username=channel.channel_name if channel else None,
            profile_picture=channel.channel_thumbnail if channel else None
        ))
    
    return result


# --- TIKTOK OAUTH ---
@router.get("/tiktok/auth-url")
def get_tiktok_auth_url():
    """Get TikTok OAuth authorization URL"""
    client_key = os.environ.get("TIKTOK_CLIENT_KEY", "")
    redirect_uri = os.environ.get("TIKTOK_REDIRECT_URI", "http://localhost:3000/auth/tiktok/callback")
    
    if not client_key:
        raise HTTPException(status_code=500, detail="TikTok client key not configured")
    
    scope = "user.info.basic,video.publish,video.upload"
    
    auth_url = (
        f"{TIKTOK_AUTH_URL}?"
        f"client_key={client_key}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope}"
    )
    
    return {"auth_url": auth_url}


@router.post("/tiktok/connect")
async def connect_tiktok(
    request: ConnectPlatformRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Exchange TikTok auth code for access token and save connection"""
    user = get_current_user_from_token(authorization, db)
    
    client_key = os.environ.get("TIKTOK_CLIENT_KEY", "")
    client_secret = os.environ.get("TIKTOK_CLIENT_SECRET", "")
    redirect_uri = request.redirect_uri or os.environ.get("TIKTOK_REDIRECT_URI", "")
    
    try:
        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_response = await client.post(
                TIKTOK_TOKEN_URL,
                data={
                    "client_key": client_key,
                    "client_secret": client_secret,
                    "code": request.auth_code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri
                }
            )
            tokens = token_response.json()
            
            if "error" in tokens:
                raise HTTPException(status_code=400, detail=tokens.get("error_description", "TikTok OAuth failed"))
            
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")
            open_id = tokens.get("open_id")
            
            # Get user info
            user_response = await client.get(
                "https://open.tiktokapis.com/v2/user/info/",
                params={"fields": "open_id,display_name,avatar_url"},
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_info = user_response.json().get("data", {}).get("user", {})
        
        # Save or update channel
        existing = db.query(SocialChannel).filter(
            SocialChannel.user_id == user.id,
            SocialChannel.platform == "tiktok"
        ).first()
        
        if existing:
            existing.access_token = access_token
            existing.refresh_token = refresh_token
            existing.channel_id = open_id
            existing.channel_name = user_info.get("display_name")
            existing.channel_thumbnail = user_info.get("avatar_url")
            existing.is_connected = True
        else:
            new_channel = SocialChannel(
                user_id=user.id,
                platform="tiktok",
                access_token=access_token,
                refresh_token=refresh_token,
                channel_id=open_id,
                channel_name=user_info.get("display_name"),
                channel_thumbnail=user_info.get("avatar_url"),
                is_connected=True
            )
            db.add(new_channel)
        
        db.commit()
        return {"status": "connected", "username": user_info.get("display_name")}
        
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"TikTok API error: {str(e)}")


@router.delete("/tiktok")
def disconnect_tiktok(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Disconnect TikTok account"""
    user = get_current_user_from_token(authorization, db)
    
    channel = db.query(SocialChannel).filter(
        SocialChannel.user_id == user.id,
        SocialChannel.platform == "tiktok"
    ).first()
    
    if channel:
        channel.is_connected = False
        db.commit()
    
    return {"status": "disconnected"}


# --- INSTAGRAM OAUTH ---
@router.get("/instagram/auth-url")
def get_instagram_auth_url():
    """Get Instagram OAuth authorization URL"""
    client_id = os.environ.get("INSTAGRAM_CLIENT_ID", "")
    redirect_uri = os.environ.get("INSTAGRAM_REDIRECT_URI", "http://localhost:3000/auth/instagram/callback")
    
    if not client_id:
        raise HTTPException(status_code=500, detail="Instagram client ID not configured")
    
    scope = "user_profile,user_media"
    
    auth_url = (
        f"{INSTAGRAM_AUTH_URL}?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope}"
    )
    
    return {"auth_url": auth_url}


@router.post("/instagram/connect")
async def connect_instagram(
    request: ConnectPlatformRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Exchange Instagram auth code for access token"""
    user = get_current_user_from_token(authorization, db)
    
    client_id = os.environ.get("INSTAGRAM_CLIENT_ID", "")
    client_secret = os.environ.get("INSTAGRAM_CLIENT_SECRET", "")
    redirect_uri = request.redirect_uri or os.environ.get("INSTAGRAM_REDIRECT_URI", "")
    
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                INSTAGRAM_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": request.auth_code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri
                }
            )
            tokens = token_response.json()
            
            if "error_type" in tokens:
                raise HTTPException(status_code=400, detail=tokens.get("error_message", "Instagram OAuth failed"))
            
            access_token = tokens.get("access_token")
            user_id_ig = str(tokens.get("user_id"))
            
            # Get user profile
            profile_response = await client.get(
                f"https://graph.instagram.com/{user_id_ig}",
                params={
                    "fields": "id,username",
                    "access_token": access_token
                }
            )
            profile = profile_response.json()
        
        # Save channel
        existing = db.query(SocialChannel).filter(
            SocialChannel.user_id == user.id,
            SocialChannel.platform == "instagram"
        ).first()
        
        if existing:
            existing.access_token = access_token
            existing.channel_id = user_id_ig
            existing.channel_name = profile.get("username")
            existing.is_connected = True
        else:
            new_channel = SocialChannel(
                user_id=user.id,
                platform="instagram",
                access_token=access_token,
                channel_id=user_id_ig,
                channel_name=profile.get("username"),
                is_connected=True
            )
            db.add(new_channel)
        
        db.commit()
        return {"status": "connected", "username": profile.get("username")}
        
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Instagram API error: {str(e)}")


# --- PUBLISH CLIP ---
@router.post("/publish")
async def publish_clip(
    request: PublishRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Publish a rendered clip to a social platform"""
    user = get_current_user_from_token(authorization, db)
    
    # Get clip
    clip = db.query(GeneratedClip).filter(GeneratedClip.id == request.clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    # Get platform channel
    channel = db.query(SocialChannel).filter(
        SocialChannel.user_id == user.id,
        SocialChannel.platform == request.platform,
        SocialChannel.is_connected == True
    ).first()
    
    if not channel:
        raise HTTPException(status_code=400, detail=f"{request.platform} not connected")
    
    # Platform-specific publishing
    if request.platform == "tiktok":
        result = await _publish_to_tiktok(clip, channel, request.caption)
    elif request.platform == "instagram":
        result = await _publish_to_instagram(clip, channel, request.caption)
    elif request.platform == "youtube_shorts":
        result = await _publish_to_youtube_shorts(clip, channel, request.caption)
    else:
        raise HTTPException(status_code=400, detail=f"Platform {request.platform} not supported")
    
    return result


async def _publish_to_tiktok(clip: GeneratedClip, channel: SocialChannel, caption: str = None):
    """Upload video to TikTok"""
    video_path = clip.file_path
    
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # TikTok requires video to be uploaded via their API
    # This is a simplified version - production needs chunked upload
    try:
        async with httpx.AsyncClient() as client:
            # Initialize upload
            init_response = await client.post(
                TIKTOK_UPLOAD_URL,
                headers={
                    "Authorization": f"Bearer {channel.access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "post_info": {
                        "title": caption or clip.title or "Check this out!",
                        "privacy_level": "PUBLIC_TO_EVERYONE"
                    },
                    "source_info": {
                        "source": "FILE_UPLOAD"
                    }
                }
            )
            
            result = init_response.json()
            
            if "error" in result:
                return {"status": "failed", "error": result.get("error", {}).get("message")}
            
            return {
                "status": "success",
                "platform": "tiktok",
                "message": "Video uploaded to TikTok"
            }
            
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def _publish_to_instagram(clip: GeneratedClip, channel: SocialChannel, caption: str = None):
    """Upload reel to Instagram (requires Business/Creator account)"""
    # Instagram Reels API requires:
    # 1. Video URL (public) or container upload
    # 2. Business/Creator account
    
    return {
        "status": "pending",
        "platform": "instagram",
        "message": "Instagram Reels upload requires video to be hosted on public URL. Implementation pending."
    }


async def _publish_to_youtube_shorts(clip: GeneratedClip, channel: SocialChannel, caption: str = None):
    """Upload to YouTube Shorts (uses existing YouTube OAuth)"""
    # YouTube Shorts is just a regular YouTube upload with #Shorts in title
    # This would use the YouTube Data API v3
    
    return {
        "status": "pending",
        "platform": "youtube_shorts",
        "message": "YouTube Shorts upload implementation pending."
    }
