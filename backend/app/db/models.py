from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float, JSON
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
    candidates = relationship("ClipCandidate", back_populates="project")

class GeneratedClip(Base):
    __tablename__ = "generated_clips"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id")) 
    file_path = Column(String, nullable=False) 
    title = Column(String, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    project = relationship("Project", back_populates="clips")

class MonitoredChannel(Base):
    __tablename__ = "monitored_channels"
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String, unique=True, index=True)
    name = Column(String)
    rss_url = Column(String)
    last_video_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ClipCandidate(Base):
    __tablename__ = "clip_candidates"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"))
    
    start_time = Column(Float)
    end_time = Column(Float)
    title = Column(String)
    description = Column(Text)
    viral_score = Column(Integer)
    
    is_rendered = Column(Boolean, default=False)
    
    # --- KOLOM BARU UNTUK EDITOR ---
    # Menyimpan video 9:16 polos (tanpa teks) untuk preview di editor
    draft_video_path = Column(String, nullable=True)
    # Menyimpan data JSON Whisper (word-level timestamps) agar bisa diedit
    transcript_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    project = relationship("Project", back_populates="candidates")