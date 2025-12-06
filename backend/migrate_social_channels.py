"""
Migration script to add new columns to social_channels table.
Run this inside the backend container or with DATABASE_URL set.
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost:5432/content_factory_db")

def run_migration():
    engine = create_engine(DATABASE_URL)
    
    migrations = [
        # Add last_video_id column
        """
        ALTER TABLE social_channels 
        ADD COLUMN IF NOT EXISTS last_video_id VARCHAR;
        """,
        # Add uploads_playlist_id column
        """
        ALTER TABLE social_channels 
        ADD COLUMN IF NOT EXISTS uploads_playlist_id VARCHAR;
        """,
    ]
    
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"✅ Executed: {sql.strip()[:50]}...")
            except Exception as e:
                print(f"⚠️ Skipped (may already exist): {e}")
    
    print("\n🎉 Migration completed!")

if __name__ == "__main__":
    run_migration()
