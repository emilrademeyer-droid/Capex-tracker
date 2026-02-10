import os
import datetime
from sqlalchemy import create_engine, text

print("CapexTracker Daily Runner started at", datetime.datetime.now().isoformat())

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("No DATABASE_URL – skipping DB operations (normal in testing)")
else:
    try:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # Just a test query
            conn.execute(text("SELECT 1"))
            print("Database connection OK")
            
            # Later we will add real INSERT / UPDATE here
            print("Would insert new project data here if any found...")
            
    except Exception as e:
        print("Database error:", str(e))

print("Daily run finished. No real search yet – placeholder only.")
