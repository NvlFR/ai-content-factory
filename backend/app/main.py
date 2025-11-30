from fastapi import FastAPI

app = FastAPI(title="AI Content Factory API")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "AI Content Factory Backend is running!",
        "version": "0.1.0"
    }

@app.get("/health")
def health_check():
    return {"database": "check_pending", "redis": "check_pending"}