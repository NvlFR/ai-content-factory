# Gunakan Python 3.11 (Versi stabil & cepat)
FROM python:3.11-slim

# Set folder kerja di dalam container
WORKDIR /app

# Install dependencies sistem (FFmpeg wajib untuk video editing)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements dan install library Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kode aplikasi
COPY . .

# Command default (jalankan server)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]