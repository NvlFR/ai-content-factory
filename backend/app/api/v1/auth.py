from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
import httpx
from datetime import datetime, timedelta
import jwt

from app.db.database import get_db
from app.db.models import User, SocialChannel

router = APIRouter()

# Environment Variables
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/auth/google/callback")
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"


async def fetch_youtube_channel_info(access_token: str) -> dict:
    """Fetch user's YouTube channel info using YouTube Data API"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            YOUTUBE_CHANNELS_URL,
            params={
                "part": "snippet,contentDetails",
                "mine": "true"
            },
            headers={"Authorization": f"Bearer {access_token}"}
        )
        data = response.json()
        
        if "items" in data and len(data["items"]) > 0:
            channel = data["items"][0]
            return {
                "channel_id": channel["id"],
                "channel_name": channel["snippet"]["title"],
                "channel_thumbnail": channel["snippet"]["thumbnails"]["default"]["url"],
                "uploads_playlist_id": channel["contentDetails"]["relatedPlaylists"]["uploads"]
            }
        return None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    picture: Optional[str]
    credits_balance: int


class GoogleAuthRequest(BaseModel):
    code: str
    redirect_uri: Optional[str] = None


def create_jwt_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(token: str, db: Session) -> User:
    payload = verify_jwt_token(token)
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/google/login")
async def google_login():
    """Redirect user to Google OAuth consent screen"""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile https://www.googleapis.com/auth/youtube.readonly",
        "access_type": "offline",
        "prompt": "consent"
    }
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{query_string}")


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        async with httpx.AsyncClient() as client:
            # Exchange code for tokens
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": GOOGLE_REDIRECT_URI
                }
            )
            tokens = token_response.json()
            
            if "error" in tokens:
                raise HTTPException(status_code=400, detail=tokens.get("error_description", "OAuth failed"))
            
            # Get user info
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {tokens['access_token']}"}
            )
            userinfo = userinfo_response.json()
        
        # Find or create user
        user = db.query(User).filter(User.email == userinfo["email"]).first()
        if not user:
            user = User(
                email=userinfo["email"],
                name=userinfo.get("name"),
                picture=userinfo.get("picture")
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Fetch YouTube channel info
        yt_channel_info = await fetch_youtube_channel_info(tokens["access_token"])
        
        # Store YouTube channel connection
        existing_channel = db.query(SocialChannel).filter(
            SocialChannel.user_id == user.id,
            SocialChannel.platform == "youtube"
        ).first()
        
        if not existing_channel:
            youtube_channel = SocialChannel(
                user_id=user.id,
                platform="youtube",
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                channel_id=yt_channel_info["channel_id"] if yt_channel_info else None,
                channel_name=yt_channel_info["channel_name"] if yt_channel_info else None,
                channel_thumbnail=yt_channel_info["channel_thumbnail"] if yt_channel_info else None,
                uploads_playlist_id=yt_channel_info["uploads_playlist_id"] if yt_channel_info else None
            )
            db.add(youtube_channel)
        else:
            existing_channel.access_token = tokens["access_token"]
            if tokens.get("refresh_token"):
                existing_channel.refresh_token = tokens["refresh_token"]
            if yt_channel_info:
                existing_channel.channel_id = yt_channel_info["channel_id"]
                existing_channel.channel_name = yt_channel_info["channel_name"]
                existing_channel.channel_thumbnail = yt_channel_info["channel_thumbnail"]
                existing_channel.uploads_playlist_id = yt_channel_info["uploads_playlist_id"]
            existing_channel.is_connected = True
        db.commit()
        
        # Create JWT
        jwt_token = create_jwt_token(user.id, user.email)
        
        # Redirect to frontend with token
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(url=f"{frontend_url}/auth/callback?token={jwt_token}")
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"OAuth request failed: {str(e)}")


@router.post("/google/token", response_model=TokenResponse)
async def google_token_exchange(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Exchange Google auth code for JWT token (for frontend OAuth flow)"""
    redirect_uri = request.redirect_uri or GOOGLE_REDIRECT_URI
    
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": request.code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri
                }
            )
            tokens = token_response.json()
            
            if "error" in tokens:
                raise HTTPException(status_code=400, detail=tokens.get("error_description", "OAuth failed"))
            
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {tokens['access_token']}"}
            )
            userinfo = userinfo_response.json()
        
        # Find or create user
        user = db.query(User).filter(User.email == userinfo["email"]).first()
        if not user:
            user = User(
                email=userinfo["email"],
                name=userinfo.get("name"),
                picture=userinfo.get("picture")
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.name = userinfo.get("name", user.name)
            user.picture = userinfo.get("picture", user.picture)
            db.commit()
        
        # Fetch YouTube channel info
        yt_channel_info = await fetch_youtube_channel_info(tokens["access_token"])
        
        # Store tokens and channel info
        existing_channel = db.query(SocialChannel).filter(
            SocialChannel.user_id == user.id,
            SocialChannel.platform == "youtube"
        ).first()
        
        if not existing_channel:
            youtube_channel = SocialChannel(
                user_id=user.id,
                platform="youtube",
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                channel_id=yt_channel_info["channel_id"] if yt_channel_info else None,
                channel_name=yt_channel_info["channel_name"] if yt_channel_info else None,
                channel_thumbnail=yt_channel_info["channel_thumbnail"] if yt_channel_info else None,
                uploads_playlist_id=yt_channel_info["uploads_playlist_id"] if yt_channel_info else None
            )
            db.add(youtube_channel)
        else:
            existing_channel.access_token = tokens["access_token"]
            if tokens.get("refresh_token"):
                existing_channel.refresh_token = tokens["refresh_token"]
            if yt_channel_info:
                existing_channel.channel_id = yt_channel_info["channel_id"]
                existing_channel.channel_name = yt_channel_info["channel_name"]
                existing_channel.channel_thumbnail = yt_channel_info["channel_thumbnail"]
                existing_channel.uploads_playlist_id = yt_channel_info["uploads_playlist_id"]
            existing_channel.is_connected = True
        db.commit()
        
        jwt_token = create_jwt_token(user.id, user.email)
        
        return TokenResponse(
            access_token=jwt_token,
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "picture": user.picture,
                "credits_balance": user.credits_balance
            }
        )
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"OAuth request failed: {str(e)}")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    authorization: str = None,
    db: Session = Depends(get_db)
):
    """Get current authenticated user info"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token, db)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        picture=user.picture,
        credits_balance=user.credits_balance
    )


@router.post("/logout")
async def logout():
    """Logout user (client should discard token)"""
    return {"message": "Logged out successfully"}
