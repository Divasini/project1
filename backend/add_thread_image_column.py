"""
Adds the missing 'image_url' column to the existing 'threads' table
in PostgreSQL. Safe to run — it checks first so it won't error out
if the column already exists.

Run this from inside your backend folder:
    python add_thread_image_column.py
"""

from sqlalchemy import text
from database import engine

with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE threads
        ADD COLUMN IF NOT EXISTS image_url VARCHAR(500) DEFAULT '';
    """))
    conn.commit()

print("Done! 'image_url' column added to 'threads' table (or already existed).")