"""
Migration: Create broadcasts table for storing hourly broadcasts
"""

import psycopg
import os

DATABASE_URL = os.getenv("DATABASE_URL")

def run_migration():
    """Create the broadcasts table."""
    conn = psycopg.connect(DATABASE_URL, connect_timeout=30)
    cursor = conn.cursor()
    
    try:
        # Create broadcasts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS broadcasts (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(100) NOT NULL,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                broadcast_type VARCHAR(50) DEFAULT 'Thought',
                priority VARCHAR(20) DEFAULT 'Medium',
                confidence FLOAT DEFAULT 0.8,
                notion_synced BOOLEAN DEFAULT FALSE,
                read_by_thinking BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_broadcasts_created_at ON broadcasts(created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_broadcasts_read ON broadcasts(read_by_thinking)
        """)
        
        conn.commit()
        print("✅ Broadcasts table created successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
