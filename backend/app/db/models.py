from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
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

class GeneratedClip(Base):
    __tablename__ = "generated_clips"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id")) 
    file_path = Column(String, nullable=False) 
    title = Column(String, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="clips")

# --- TAMBAHAN BARU: TABEL CHANNEL ---
class MonitoredChannel(Base):
    __tablename__ = "monitored_channels"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String, unique=True, index=True) # ID Unik dari YouTube (misal: UCx....)
    name = Column(String) # Nama Channel (misal: GadgetIn)
    rss_url = Column(String) # Link XML untuk dipantau
    last_video_id = Column(String, nullable=True) # Video terakhir yang kita proses (biar gak double)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())