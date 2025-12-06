from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.db.database import get_db
from app.db.models import GeneratedClip, Project, User
from app.api.v1.auth import verify_jwt_token

router = APIRouter()


def get_current_user_from_token(authorization: str, db: Session) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    token = authorization.replace("Bearer ", "")
    payload = verify_jwt_token(token)
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


class ClipResponse(BaseModel):
    id: int
    project_id: str
    file_path: str
    title: Optional[str]
    caption: Optional[str]
    is_approved: bool
    published_at: Optional[datetime]
    published_platform: Optional[str]
    credits_used: int
    created_at: datetime

    class Config:
        from_attributes = True


class ClipUpdateRequest(BaseModel):
    caption: Optional[str] = None
    is_approved: Optional[bool] = None


class ClipApprovalRequest(BaseModel):
    approved: bool


@router.get("/", response_model=List[ClipResponse])
def list_clips(
    skip: int = 0,
    limit: int = 50,
    approved_only: bool = False,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """List all clips for the current user"""
    user = get_current_user_from_token(authorization, db)
    
    query = db.query(GeneratedClip).join(Project).filter(Project.user_id == user.id)
    
    if approved_only:
        query = query.filter(GeneratedClip.is_approved == True)
    
    clips = query.order_by(GeneratedClip.created_at.desc()).offset(skip).limit(limit).all()
    return clips


@router.get("/{clip_id}", response_model=ClipResponse)
def get_clip(
    clip_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Get a specific clip"""
    user = get_current_user_from_token(authorization, db)
    
    clip = db.query(GeneratedClip).join(Project).filter(
        GeneratedClip.id == clip_id,
        Project.user_id == user.id
    ).first()
    
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    return clip


@router.patch("/{clip_id}", response_model=ClipResponse)
def update_clip(
    clip_id: int,
    request: ClipUpdateRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Update clip caption or approval status"""
    user = get_current_user_from_token(authorization, db)
    
    clip = db.query(GeneratedClip).join(Project).filter(
        GeneratedClip.id == clip_id,
        Project.user_id == user.id
    ).first()
    
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    if request.caption is not None:
        clip.caption = request.caption
    
    if request.is_approved is not None:
        clip.is_approved = request.is_approved
    
    db.commit()
    db.refresh(clip)
    
    return clip


@router.post("/{clip_id}/approve")
def approve_clip(
    clip_id: int,
    request: ClipApprovalRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Approve or reject a clip for publishing"""
    user = get_current_user_from_token(authorization, db)
    
    clip = db.query(GeneratedClip).join(Project).filter(
        GeneratedClip.id == clip_id,
        Project.user_id == user.id
    ).first()
    
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    clip.is_approved = request.approved
    db.commit()
    
    return {
        "status": "approved" if request.approved else "rejected",
        "clip_id": clip_id
    }


@router.delete("/{clip_id}")
def delete_clip(
    clip_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Delete a clip (does not refund credits)"""
    user = get_current_user_from_token(authorization, db)
    
    clip = db.query(GeneratedClip).join(Project).filter(
        GeneratedClip.id == clip_id,
        Project.user_id == user.id
    ).first()
    
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    # Don't delete if already published
    if clip.published_at:
        raise HTTPException(status_code=400, detail="Cannot delete published clips")
    
    db.delete(clip)
    db.commit()
    
    return {"status": "deleted", "clip_id": clip_id}


@router.get("/pending/count")
def get_pending_count(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Get count of clips pending approval"""
    user = get_current_user_from_token(authorization, db)
    
    count = db.query(GeneratedClip).join(Project).filter(
        Project.user_id == user.id,
        GeneratedClip.is_approved == False,
        GeneratedClip.published_at == None
    ).count()
    
    return {"pending_count": count}
