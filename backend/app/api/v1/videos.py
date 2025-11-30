from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from celery.result import AsyncResult
from app.tasks.pipeline import process_video_pipeline

router = APIRouter()

# Schema untuk Request (Apa yang dikirim user)
class VideoRequest(BaseModel):
    url: str

# Schema untuk Response (Apa yang diterima user)
class TaskResponse(BaseModel):
    task_id: str
    status: str

@router.post("/", response_model=TaskResponse)
def create_video_task(video: VideoRequest):
    """
    Tombol START: Menerima URL YouTube dan memulai proses di background.
    """
    if "youtube.com" not in video.url and "youtu.be" not in video.url:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    # Kirim tugas ke Celery Worker
    task = process_video_pipeline.delay(video.url)
    
    return {"task_id": task.id, "status": "processing_started"}

@router.get("/{task_id}")
def get_task_status(task_id: str):
    """
    Layar MONITOR: Mengecek progress tugas (Apakah sudah selesai?).
    """
    task_result = AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task_result.state,
        "result": task_result.result if task_result.ready() else None
    }
    
    # Jika task menyimpan meta info (seperti 'Downloading...'), tampilkan juga
    if task_result.state == 'PROGRESS':
        response["progress"] = task_result.info
        
    return response