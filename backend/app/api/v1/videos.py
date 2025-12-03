from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from celery.result import AsyncResult
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.db import models

router = APIRouter()

# --- SCHEMAS ---
class VideoRequest(BaseModel):
    url: str

class ClipSchema(BaseModel):
    file_path: str
    title: Optional[str] = None
    class Config: from_attributes = True

# Schema untuk Kandidat (Draft)
class CandidateSchema(BaseModel):
    id: int
    start_time: float
    end_time: float
    title: str
    description: str
    viral_score: int
    is_rendered: bool
    class Config: from_attributes = True

class ProjectSchema(BaseModel):
    id: str
    youtube_url: str
    status: str
    created_at: datetime
    # Kita sertakan keduanya: Klip jadi DAN Kandidat draft
    clips: List[ClipSchema] = []
    candidates: List[CandidateSchema] = [] 

    class Config: from_attributes = True

class TaskResponse(BaseModel):
    task_id: str
    status: str

# --- ENDPOINTS ---

@router.post("/", response_model=TaskResponse)
def create_video_task(video: VideoRequest):
    """Start Analysis (Draft Mode)."""
    if "youtube.com" not in video.url and "youtu.be" not in video.url:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    # Lazy Import
    from app.tasks.pipeline import analyze_video_task
    task = analyze_video_task.delay(video.url)
    
    return {"task_id": task.id, "status": "analysis_started"}

@router.post("/render/{candidate_id}")
def render_candidate(candidate_id: int):
    """Trigger rendering untuk satu kandidat spesifik."""
    from app.tasks.pipeline import render_single_clip_task
    task = render_single_clip_task.delay(candidate_id)
    return {"task_id": task.id, "status": "rendering_started"}

@router.get("/", response_model=List[ProjectSchema])
def list_projects(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """Ambil daftar project beserta kandidatnya."""
    projects = db.query(models.Project).order_by(models.Project.created_at.desc()).offset(skip).limit(limit).all()
    return projects

@router.get("/{task_id}")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    task_result = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task_result.state,
    }