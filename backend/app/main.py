from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # <--- 1. IMPORT INI
import os # <--- 2. IMPORT INI
from app.api.v1 import videos

app = FastAPI(title="AI Content Factory API")

# Setup CORS (Sudah ada sebelumnya)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- TAMBAHAN BARU: STATIC FILE MOUNTING ---
# Pastikan folder ada dulu biar ga error
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# Mounting: URL "localhost:8000/downloads" -> Folder "downloads"
app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")

app.include_router(videos.router, prefix="/api/v1/videos", tags=["Videos"])

@app.get("/")
def read_root():
    return {"status": "online", "version": "1.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}