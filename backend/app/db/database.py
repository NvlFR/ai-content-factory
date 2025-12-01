from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Ambil URL Database dari environment variable (settingan di docker-compose)
# Format: postgresql://user:password@db:5432/db_name
SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL")

# Buat Engine Koneksi
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Buat Sesi (Session) untuk transaksi data
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base Model untuk semua tabel nanti
Base = declarative_base()

# Dependency Helper: Untuk dipakai di API nanti
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()