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
    "new hotel construction project budget over $10 million announced after:2026-02-01",
    "data center build OR expansion budget $10 million+ after:2026-02-01",
    "airport OR high-rise tower construction project capex over $10 million 2026"
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

                # Extract budget, location, sector from snippet + title
                text = title + " " + snippet
                budget_match = re.search(r'(\$[\d.,]+ ?(million|billion))', text, re.I)
                budget = budget_match.group(1) if budget_match else None

                location_match = re.search(r'(Dubai|UAE|Saudi|Indiana|Louisiana|Pennsylvania|Texas|Utah|Wyoming|Georgetown|Wichita|Lebanon|Egypt)', text, re.I)
                location = location_match.group(1) if location_match else "Unknown"

                sector = "Unknown"
                if any(word in text.lower() for word in ["hotel", "hospitality"]):
                    sector = "Hospitality"
                elif any(word in text.lower() for word in ["data center", "ai", "gigawatt"]):
                    sector = "Data Centers"
                elif any(word in text.lower() for word in ["airport", "high-rise", "tower"]):
                    sector = "Infrastructure / High-Rise"
                elif "lunar" in text.lower():
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
