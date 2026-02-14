import os
import datetime
import requests
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
    payload = {"q": query, "num": 10, "tbs": "qdr:w"}
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("organic", [])
    except Exception as e:
        print(f"Serper error for query '{query}': {str(e)}")
        return []

queries = [
    "new hotel construction project budget over $10 million",
    "data center build OR expansion budget $10 million+",
    "airport OR high-rise tower construction project capex over $10 million"
    "residential project with capex over $10 million"
    "roads or transport project with a budget over $10 million"
    "rail or metro project with a budget over $10 million"
]

session = Session()
inserted_count = 0

try:
    print("Database connection OK")

    for q in queries:
        print(f"Searching: {q}")
        results = search_serper(q)
        print(f"Found {len(results)} results")

        for res in results:
            proj_name = res.get("title", "")[:255]
            proj_link = res.get("link", "")[:255]

            print(f"Processing: {proj_name}")

            try:
                exists = session.execute(
                    text("SELECT 1 FROM projects WHERE link = :link OR name = :name"),
                    {"link": proj_link, "name": proj_name}
                ).scalar()

                if exists:
                    print(f"Skipped duplicate: {proj_name}")
                    continue

                session.execute(
                    text("""
                        INSERT INTO projects (name, status, last_updated, announcement_date, link)
                        VALUES (:name, 'Pending Review', CURRENT_DATE, CURRENT_DATE, :link)
                    """),
                    {"name": proj_name, "link": proj_link}
                )
                inserted_count += 1
                print(f"Inserted: {proj_name} (link: {proj_link})")

            except Exception as e:
                print(f"Insert failed for '{proj_name}': {str(e)}")

    session.commit()
    print(f"Daily run finished. Added {inserted_count} new projects.")
except Exception as e:
    print(f"Unexpected error: {str(e)}")
    session.rollback()
finally:
    session.close()
