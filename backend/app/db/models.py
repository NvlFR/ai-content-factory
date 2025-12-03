from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True) 
    youtube_url = Column(String, nullable=False)
    status = Column(String, default="processing") 
    title = Column(String, nullable=True) 
    thumbnail_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    clips = relationship("GeneratedClip", back_populates="project")
    # Relasi ke Kandidat (Draft)
    candidates = relationship("ClipCandidate", back_populates="project")

class GeneratedClip(Base):
    __tablename__ = "generated_clips"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id")) 
    file_path = Column(String, nullable=False) 
    title = Column(String, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="clips")

# --- TABEL MONITORING (Yang tadi siang) ---
class MonitoredChannel(Base):
    __tablename__ = "monitored_channels"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String, unique=True, index=True)
    name = Column(String)
    rss_url = Column(String)
    last_video_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- BARU: TABEL KANDIDAT / DRAFT ---
class ClipCandidate(Base):
    __tablename__ = "clip_candidates"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"))
    
    # Data Analisis AI
    start_time = Column(Float) # Detik mulai
    end_time = Column(Float)   # Detik selesai
    title = Column(String)     # Judul catchy
    description = Column(Text) # Alasan kenapa ini viral
    viral_score = Column(Integer) # 1-100
    
    # Status Render
    is_rendered = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="candidates")