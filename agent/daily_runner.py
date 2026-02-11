import os
import datetime
import requests
from sqlalchemy import create_engine, text, Column, Integer, String, Date, Numeric, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

Base = declarative_base()

# Schema (same as before)
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
    architect_id = Column(Integer, ForeignKey('companies.id'))
    contractor_id = Column(Integer, ForeignKey('companies.id'))
    announcement_date = Column(Date)
    construction_start_date = Column(Date)
    construction_completion_date = Column(Date)
    client_handover_date = Column(Date)
    budget_usd = Column(Numeric(precision=18, scale=2))
    duration_months = Column(Numeric(precision=10, scale=2))
    progress_percent = Column(Numeric(precision=5, scale=2))
    capex_curve = Column(JSON)
    last_updated = Column(Date, default=datetime.date.today)
    status = Column(String(50), default="Pending Data")
    link = Column(String(255), nullable=True)  # NEW

print("CapexTracker Daily Runner started at", datetime.datetime.now().isoformat())

DATABASE_URL = os.getenv("DATABASE_URL")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not DATABASE_URL:
    print("ERROR: No DATABASE_URL!")
    exit(1)

if not SERPER_API_KEY:
    print("ERROR: No SERPER_API_KEY!")
    exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Search function
def search_serper(query):
    url = "https://google.serper.dev/search"
    payload = {
        "q": query,
        "num": 10,
        "tbs": "qdr:d"  # past day
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

# Queries
queries = [
    "new hotel construction project budget over $10 million announced after:2026-02-01",
    "data center build OR expansion budget $10 million+ after:2026-02-01",
    "airport OR high-rise tower construction project capex over $10 million 2026"
]

new_projects = 0

session = Session()
try:
    print("Database connection OK")

    for query in queries:
        print(f"Searching: {query}")
        results = search_serper(query)
        
        for result in results:
            title = result.get("title", "")
            link = result.get("link", "")
            snippet = result.get("snippet", "")
            
            # Basic filter
            if "million" in snippet.lower() or "budget" in snippet.lower():
                try:
                    # Deduplicate by name OR link
                    exists = session.execute(
                        text("SELECT 1 FROM projects WHERE name = :name OR link = :link"),
                        {"name": title[:255], "link": link}
                    ).scalar()
                    
                    if not exists:
                        # Insert basic project
                        session.execute(
                            text("""
                                INSERT INTO projects (name, status, last_updated, announcement_date, link)
                                VALUES (:name, 'Announced', CURRENT_DATE, CURRENT_DATE, :link)
                            """),
                            {"name": title[:255], "link": link}
                        )
                        new_projects += 1
                        print(f"Inserted new project: {title}")
                except IntegrityError as ie:
                    print(f"Duplicate or integrity error: {str(ie)}")
                    session.rollback()
                except SQLAlchemyError as e:
                    print(f"Insert error: {str(e)}")
                    session.rollback()
except Exception as e:
    print(f"Unexpected error: {str(e)}")
    session.rollback()
finally:
    session.close()

print(f"Daily run finished. Added {new_projects} new projects.")
