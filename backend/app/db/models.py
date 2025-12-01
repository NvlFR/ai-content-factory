from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Project(Base):
    __tablename__ = "projects"

    # ID kita pakai string UUID (dari Celery Task ID) biar gampang dilacak
    id = Column(String, primary_key=True, index=True) 
    youtube_url = Column(String, nullable=False)
    status = Column(String, default="processing") # processing, completed, failed
    title = Column(String, nullable=True) # Judul Video YouTube
    thumbnail_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relasi: Satu Project punya banyak Clips
    clips = relationship("GeneratedClip", back_populates="project")

class GeneratedClip(Base):
    __tablename__ = "generated_clips"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id")) # Link ke Project
    file_path = Column(String, nullable=False) # Lokasi file video clip
    title = Column(String, nullable=True) # Topik/Judul Clip
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relasi balik
    project = relationship("Project", back_populates="clips")