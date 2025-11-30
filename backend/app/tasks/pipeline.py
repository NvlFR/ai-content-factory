from celery import Celery
import os

# Setup koneksi Celery ke Redis
celery_app = Celery(
    "worker",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

@celery_app.task
def test_task(word: str):
    """Contoh task sederhana untuk test queue"""
    return f"Worker menerima kata: {word}"