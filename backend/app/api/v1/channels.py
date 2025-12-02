from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List
import requests
import re

from app.db.database import get_db
from app.db import models

router = APIRouter()

# --- SCHEMAS ---
class ChannelCreate(BaseModel):
    url: str # User input: https://www.youtube.com/@GadgetIn

class ChannelResponse(BaseModel):
    id: int
    name: str
    channel_id: str
    is_active: bool

    class Config:
        from_attributes = True

# --- HELPER: CARI CHANNEL ID ---
def extract_channel_info(url):
    """
    Mengambil ID Channel & Nama dari URL YouTube.
    Menggunakan teknik scraping ringan karena YouTube API ribet/berbayar.
    """
    try:
        # 1. Request halaman channel
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        html = response.text

        # 2. Cari Channel ID (Biasanya pola "channelId":"UC...")
        channel_id_match = re.search(r'"channelId":"(UC[\w-]+)"', html)
        if not channel_id_match:
            # Coba pola alternatif (RSS Link di header HTML)
            channel_id_match = re.search(r'channel_id=([\w-]+)', html)
        
        # 3. Cari Nama Channel
        title_match = re.search(r'<title>(.*?) - YouTube</title>', html)
        
        if channel_id_match:
            c_id = channel_id_match.group(1)
            name = title_match.group(1) if title_match else "Unknown Channel"
            return c_id, name
        return None, None
    except Exception as e:
        print(f"Error extracting channel: {e}")
        return None, None

# --- ENDPOINTS ---

@router.post("/", response_model=ChannelResponse)
def add_channel(channel: ChannelCreate, db: Session = Depends(get_db)):
    """Menambahkan channel baru untuk dipantau."""
    
    # 1. Cari ID Channel Asli
    c_id, c_name = extract_channel_info(channel.url)
    if not c_id:
        raise HTTPException(status_code=400, detail="Gagal menemukan Channel ID. Pastikan URL benar.")

    # 2. Cek apakah sudah ada di DB
    existing = db.query(models.MonitoredChannel).filter(models.MonitoredChannel.channel_id == c_id).first()
    if existing:
        return existing

    # 3. Simpan ke DB
    rss_link = f"https://www.youtube.com/feeds/videos.xml?channel_id={c_id}"
    
    new_channel = models.MonitoredChannel(
        channel_id=c_id,
        name=c_name,
        rss_url=rss_link
    )
    db.add(new_channel)
    db.commit()
    db.refresh(new_channel)
    
    return new_channel

@router.get("/", response_model=List[ChannelResponse])
def get_channels(db: Session = Depends(get_db)):
    """List semua channel yang sedang dipantau."""
    return db.query(models.MonitoredChannel).filter(models.MonitoredChannel.is_active == True).all()

@router.delete("/{id}")
def delete_channel(id: int, db: Session = Depends(get_db)):
    """Stop memantau channel."""
    ch = db.query(models.MonitoredChannel).filter(models.MonitoredChannel.id == id).first()
    if ch:
        db.delete(ch)
        db.commit()
    return {"status": "deleted"}