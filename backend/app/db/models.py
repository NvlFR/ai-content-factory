from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
from .database import Base


class PlatformType(enum.Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    credits_balance = Column(Integer, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    social_channels = relationship("SocialChannel", back_populates="user")
    projects = relationship("Project", back_populates="user")


class SocialChannel(Base):
    __tablename__ = "social_channels"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    platform = Column(String, nullable=False)  # youtube, tiktok, instagram
    access_token = Column(Text, nullable=True)  # Encrypted in production
    refresh_token = Column(Text, nullable=True)
    channel_id = Column(String, nullable=True)
    channel_name = Column(String, nullable=True)
    channel_thumbnail = Column(String, nullable=True)
    is_connected = Column(Boolean, default=True)
    # For video monitoring
    last_video_id = Column(String, nullable=True)
    uploads_playlist_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="social_channels")


class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, index=True) 
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    youtube_url = Column(String, nullable=False)
    status = Column(String, default="processing") 
    title = Column(String, nullable=True) 
    thumbnail_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="projects")
    clips = relationship("GeneratedClip", back_populates="project")
    candidates = relationship("ClipCandidate", back_populates="project")

class GeneratedClip(Base):
    __tablename__ = "generated_clips"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id")) 
    file_path = Column(String, nullable=False) 
    title = Column(String, nullable=True)
    caption = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_platform = Column(String, nullable=True)
    credits_used = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    project = relationship("Project", back_populates="clips")


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # Negative for deduction, positive for addition
    action = Column(String, nullable=False)  # render, purchase, bonus, refund
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")

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