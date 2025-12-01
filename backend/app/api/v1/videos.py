from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from celery.result import AsyncResult
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

# Import Database stuff
from app.db.database import get_db
from app.db import models
from app.tasks.pipeline import process_video_pipeline

router = APIRouter()

# --- SCHEMAS (Format Data) ---
class VideoRequest(BaseModel):
    url: str

class ClipSchema(BaseModel):
    file_path: str
    title: Optional[str] = None
    
    class Config:
        from_attributes = True

class ProjectSchema(BaseModel):
    id: str
    youtube_url: str
    status: str
    created_at: datetime
    clips: List[ClipSchema] = []

    class Config:
        from_attributes = True

class TaskResponse(BaseModel):
    task_id: str
    status: str

# --- ENDPOINTS ---

@router.post("/", response_model=TaskResponse)
def create_video_task(video: VideoRequest):
    """Start processing a new video."""
    if "youtube.com" not in video.url and "youtu.be" not in video.url:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    task = process_video_pipeline.delay(video.url)
    return {"task_id": task.id, "status": "processing_started"}

@router.get("/", response_model=List[ProjectSchema])
def list_projects(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Ambil daftar project history dari database."""
    projects = db.query(models.Project).order_by(models.Project.created_at.desc()).offset(skip).limit(limit).all()
    return projects

@router.get("/{task_id}")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """Cek status task. Jika selesai, ambil data dari Database."""
    task_result = AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task_result.state,
        "result": None
    }

    # Jika task sukses, kita ambil data rapi dari Database, bukan dari Redis lagi
    if task_result.state == 'SUCCESS':
        project = db.query(models.Project).filter(models.Project.id == task_id).first()
        if project:
            # Format manual agar sesuai struktur frontend sebelumnya
            clip_paths = [c.file_path for c in project.clips]
            response["result"] = {
                "status": "completed",
                "generated_clips": clip_paths
            }
            
    return response