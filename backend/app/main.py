from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# --- IMPORT DATABASE ---
from app.db import models
from app.db.database import engine
# -----------------------

from app.api.v1 import videos, channels, auth

# INI KUNCINYA: Membuat tabel otomatis jika belum ada
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Content Factory API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists("downloads"):
    os.makedirs("downloads")

app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(videos.router, prefix="/api/v1/videos", tags=["Videos"])
app.include_router(channels.router, prefix="/api/v1/channels", tags=["Channels"])

@app.get("/")
def read_root():
    return {"status": "online", "version": "1.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "connected"}