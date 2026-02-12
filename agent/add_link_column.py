import os
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
        # Check if 'link' exists
        result = conn.execute(text("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'projects' AND column_name = 'link'
        """)).scalar()
        
        if result is None:
            print("Adding 'link' column...")
            conn.execute(text("ALTER TABLE projects ADD COLUMN link VARCHAR(255)"))
            conn.commit()
            print("Column added successfully.")
        else:
            print("'link' column already exists.")
except SQLAlchemyError as e:
    print(f"Error: {str(e)}")
    exit(1)

print("Script finished.")
