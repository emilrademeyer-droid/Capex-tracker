import os
import datetime
import requests
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

print("CapexTracker Daily Runner started at", datetime.datetime.now().isoformat())

DATABASE_URL = os.getenv("DATABASE_URL")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not DATABASE_URL or not SERPER_API_KEY:
    print("ERROR: Missing env vars!")
    exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def search_serper(query):
    url = "https://google.serper.dev/search"
    payload = {"q": query, "num": 15, "tbs": "qdr:w"}  # past week, more results
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json().get("organic", [])
    except Exception as e:
        print(f"Serper error for '{query}': {str(e)}")
        return []

queries = [
    "new hotel OR data center OR airport OR high-rise construction project budget OR cost OR capex $10 million OR billion announced OR started OR planned 2026 OR 2025",
    "construction project OR infrastructure development OR tower OR hotel OR data center budget over $10 million site:enr.com OR site:constructiondive.com OR site:reuters.com OR site:bloomberg.com",
    "L&T OR Larsen & Toubro OR Saudi OR UAE OR Dubai construction contract OR project $10 million+"
]

session = Session()
new_projects = 0

try:
    print("Database connection OK")

    for query in queries:
        print(f"Searching: {query}")
        results = search_serper(query)
        print(f"Found {len(results)} results")

        for result in results:
            title = result.get("title", "")[:255]
            link = result.get("link", "")[:255]
            snippet = result.get("snippet", "")

            try:
                # Check for duplicate
                exists = session.execute(
                    text("SELECT 1 FROM projects WHERE link = :link OR name = :name"),
                    {"link": link, "name": title}
                ).scalar()

                if exists:
                    print(f"Skipped duplicate: {title}")
                    continue

                # Basic extraction (improve later with better NLP if needed)
                budget_match = re.search(r'(\$[\d.,]+ ?(million|billion))', snippet + title, re.IGNORECASE)
                budget = budget_match.group(1) if budget_match else None

                location_match = re.search(r'(Dubai|UAE|Indiana|Louisiana|Texas|Pennsylvania|New Mexico|Utah|Wyoming|Georgetown|Wichita|Lebanon|Egypt|Saudi)', snippet + title, re.IGNORECASE)
                location = location_match.group(1) if location_match else "Unknown"

                sector = "Unknown"
                if any(word in (title + snippet).lower() for word in ["hotel", "hospitality"]):
                    sector = "Hospitality"
                elif any(word in (title + snippet).lower() for word in ["data center", "ai", "gigawatt"]):
                    sector = "Data Centers"
                elif any(word in (title + snippet).lower() for word in ["airport", "high-rise", "tower"]):
                    sector = "Infrastructure / High-Rise"
                elif "lunar" in (title + snippet).lower():
                    sector = "Space / Lunar"

                # Insert
                session.execute(
                    text("""
                        INSERT INTO projects (
                            name, status, last_updated, announcement_date, 
                            link, budget_usd, country, industry_sector
                        ) VALUES (
                            :name, 'Pending Review', CURRENT_DATE, CURRENT_DATE,
                            :link, :budget, :country, :sector
                        )
                    """),
                    {
                        "name": title,
                        "link": link,
                        "budget": budget,
                        "country": location,
                        "sector": sector
                    }
                )
                new_projects += 1
                print(f"Inserted: {title} | Sector: {sector} | Budget: {budget} | Location: {location}")

            except Exception as e:
                print(f"Insert skipped for '{title}': {str(e)}")

    session.commit()
    print(f"Daily run finished. Added {new_projects} new projects.")
except Exception as e:
    print(f"Unexpected error: {str(e)}")
    session.rollback()
finally:
    session.close()
