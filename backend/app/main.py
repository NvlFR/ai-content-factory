from fastapi import FastAPI
from app.api.v1 import videos  # <--- Import file videos.py tadi

app = FastAPI(title="AI Content Factory API")

# Daftarkan Router Video di alamat /api/v1/videos
app.include_router(videos.router, prefix="/api/v1/videos", tags=["Videos"])

@app.get("/")
def read_root():
    return {"status": "online", "version": "1.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}