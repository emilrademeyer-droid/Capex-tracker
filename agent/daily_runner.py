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
    payload = {"q": query, "num": 10, "tbs": "qdr:d"}
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
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

            try:
                exists = session.execute(
                    text("SELECT 1 FROM projects WHERE link = :link OR name = :name"),
                    {"link": link, "name": title}
                ).scalar()

                if not exists:
                    session.execute(
                        text("""
                            INSERT INTO projects (name, status, last_updated, announcement_date, link)
                            VALUES (:name, 'Review Needed', CURRENT_DATE, CURRENT_DATE, :link)
                        """),
                        {"name": title, "link": link}
                    )
                    new_projects += 1
                    print(f"Inserted: {title} (link: {link})")
            except Exception as e:
                print(f"Insert skipped for '{title}': {str(e)}")

    session.commit()
    print(f"Daily run finished. Added {new_projects} new projects.")
except Exception as e:
    print(f"Unexpected error: {str(e)}")
    session.rollback()
finally:
    session.close()
