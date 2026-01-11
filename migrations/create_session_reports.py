"""
Migration: Create session_reports table for storing session reports with learnings
"""
import psycopg2
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

def run_migration():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS session_reports (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_date TEXT NOT NULL,
            session_type TEXT NOT NULL,
            accomplishments JSONB DEFAULT '[]',
            learnings JSONB DEFAULT '[]',
            tips_for_tomorrow JSONB DEFAULT '[]',
            manus_task_id TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    
    # Add index on session_date
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_session_reports_date 
        ON session_reports(session_date DESC)
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete: session_reports table created")

if __name__ == "__main__":
    run_migration()
