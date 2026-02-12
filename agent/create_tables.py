import os
import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: No DATABASE_URL!")
    exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, echo=True)

try:
    with engine.connect() as conn:
        # Check if 'link' column exists in 'projects'
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'projects' AND column_name = 'link'
        """)).scalar()
        
        if not result:
            print("Adding 'link' column to 'projects' table...")
            conn.execute(text("ALTER TABLE projects ADD COLUMN link VARCHAR(255)"))
            print("Column added successfully.")
        else:
            print("'link' column already exists.")
        
        # Test insert (ignore duplicate)
        conn.execute(text("""
            INSERT INTO companies (name, type, location) VALUES ('Test Construction Ltd', 'Owner', 'Dubai, UAE') 
            ON CONFLICT (name) DO NOTHING
        """))
        print("Test company inserted (or skipped if duplicate).")
        
except SQLAlchemyError as e:
    print(f"Database error: {str(e)}")
    exit(1)

print("Script finished.")
