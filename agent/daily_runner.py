import os
import datetime
import requests
from sqlalchemy import create_engine, text, Column, Integer, String, Date, Numeric, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError

Base = declarative_base()

# Reuse the same schema as create_tables.py
class Company(Base):
    __tablename__ = 'companies'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    type = Column(String(100))
    location = Column(String(255))
    contact_info = Column(JSON)

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    owner_id = Column(Integer, ForeignKey('companies.id'))
    owner = relationship("Company", foreign_keys=[owner_id])
    gps = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    industry_sector = Column(String(100))
    announcement_date = Column(Date)
    construction_start_date = Column(Date)
    construction_completion_date = Column(Date)
    budget_usd = Column(Numeric(precision=18, scale=2))
    duration_months = Column(Numeric(precision=10, scale=2))
    progress_percent = Column(Numeric(precision=5, scale=2))
    last_updated = Column(Date, default=datetime.date.today)
    status = Column(String(50), default="Pending Data")

print("CapexTracker Daily Runner started at", datetime.datetime.now().isoformat())

DATABASE_URL = os.getenv("DATABASE_URL")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not DATABASE_URL:
    print("ERROR: No DATABASE_URL in environment variables!")
    exit(1)

if not SERPER_API_KEY:
    print("ERROR: No SERPER_API_KEY in environment variables!")
    exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

try:
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    print("Database connection OK")
except SQLAlchemyError as e:
    print(f"Database error: {str(e)}")
    exit(1)

# Simple search function using Serper
def search_serper(query):
    url = "https://google.serper.dev/search"
    payload = {
        "q": query,
        "num": 10,  # top 10 results
        "tbs": "qdr:d"  # past day (d = day, h=hour, w=week, m=month, y=year)
    }
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get("organic", [])
    else:
        print(f"Serper error: {response.status_code} - {response.text}")
        return []

# Example search queries (customize these!)
queries = [
    "new hotel construction project budget over $10 million announced after:2026-02-01",
    "data center build OR expansion budget $10 million+ after:2026-02-01",
    "airport OR high-rise tower construction project capex over $10 million 2026"
]

new_projects = 0

for query in queries:
    print(f"Searching: {query}")
    results = search_serper(query)
    
    for result in results:
        title = result.get("title", "")
        link = result.get("link", "")
        snippet = result.get("snippet", "")
        
        # Very basic parsing — improve later with NLP/regex
        if "million" in snippet.lower() or "budget" in snippet.lower():
            # Dummy insert — replace with real extraction logic
            project_name = title[:100]  # truncate
            try:
                # Check if already exists (by name + link)
                exists = session.execute(
                    text("SELECT 1 FROM projects WHERE name = :name OR link = :link"),
                    {"name": project_name, "link": link}
                ).scalar()
                
                if not exists:
                    session.execute(
                        text("""
                            INSERT INTO projects (name, country, status, last_updated, announcement_date)
                            VALUES (:name, 'Unknown', 'Announced', CURRENT_DATE, CURRENT_DATE)
                        """),
                        {"name": project_name}
                    )
                    new_projects += 1
                    print(f"Inserted new project: {project_name}")
            except Exception as e:
                print(f"Insert error: {str(e)}")

session.commit()
session.close()

print(f"Daily run finished. Added {new_projects} new projects.")
