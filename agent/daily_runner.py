import os
import datetime
import requests
import re
import numpy as np
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
    payload = {"q": query, "num": 15, "tbs": "qdr:w"}
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json().get("organic", [])
    except Exception as e:
        print(f"Serper error for '{query}': {str(e)}")
        return []

def s_curve(budget, duration_months):
    if duration_months <= 0 or budget is None:
        return None
    time = np.arange(0, duration_months + 1)
    percent_time = time / duration_months
    k = 10  # steepness
    midpoint = 0.55
    cash_percent = 1 / (1 + np.exp(-k * (percent_time - midpoint)))
    cash_percent = cash_percent / cash_percent.max()
    monthly_spend = np.diff(cash_percent, prepend=0) * budget
    return monthly_spend.tolist()

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
                # Check duplicate
                exists = session.execute(
                    text("SELECT 1 FROM projects WHERE link = :link OR name = :name"),
                    {"link": link, "name": title}
                ).scalar()

                if exists:
                    print(f"Skipped duplicate: {title}")
                    continue

                text = title + " " + snippet
                budget_match = re.search(r'(\$[\d.,]+ ?(million|billion))', text, re.I)
                budget_str = budget_match.group(1) if budget_match else None
                budget = float(re.sub(r'[^\d.]', '', budget_str)) * (1e6 if "million" in (budget_str or "").lower() else 1e9) if budget_str else None

                location_match = re.search(r'(Dubai|UAE|Saudi|Indiana|Louisiana|Pennsylvania|Texas|Utah|Wyoming|Georgetown|Wichita|Lebanon|Egypt)', text, re.I)
                location = location_match.group(1) if location_match else "Unknown"

                sector = "Unknown"
                lower_text = text.lower()
                if "hotel" in lower_text or "hospitality" in lower_text:
                    sector = "Hospitality"
                elif "data center" in lower_text or "ai" in lower_text or "gigawatt" in lower_text:
                    sector = "Data Centers"
                elif "airport" in lower_text or "high-rise" in lower_text or "tower" in lower_text:
                    sector = "Infrastructure / High-Rise"
                elif "lunar" in lower_text:
                    sector = "Space / Lunar"

                # Extract dates (basic)
                start_match = re.search(r'(start|begin|break ground|construction start) (\d{4}-\d{2}-\d{2}|\d{4})', text, re.I)
                start_date = datetime.datetime.strptime(start_match.group(2), '%Y-%m-%d' if '-' in start_match.group(2) else '%Y').date() if start_match else None

                end_match = re.search(r'(complete|finish|open|completion) (\d{4}-\d{2}-\d{2}|\d{4})', text, re.I)
                end_date = datetime.datetime.strptime(end_match.group(2), '%Y-%m-%d' if '-' in end_match.group(2) else '%Y').date() if end_match else None

                duration = ((end_date - start_date).days / 30) if start_date and end_date else None

                progress = ((datetime.date.today() - start_date).days / (duration * 30)) * 100 if duration and start_date else None
                progress = min(max(progress, 0), 100) if progress else None

                capex_curve = s_curve(budget, duration) if budget and duration else None

                session.execute(
                    text("""
                        INSERT INTO projects (
                            name, status, last_updated, announcement_date, 
                            link, budget_usd, country, industry_sector, 
                            construction_start_date, construction_completion_date, 
                            duration_months, progress_percent, capex_curve
                        ) VALUES (
                            :name, 'Pending Review', CURRENT_DATE, CURRENT_DATE, 
                            :link, :budget, :country, :sector, 
                            :start, :end, :duration, :progress, :capex_curve
                        )
                    """),
                    {
                        "name": title,
                        "link": link,
                        "budget": budget,
                        "country": location,
                        "sector": sector,
                        "start": start_date,
                        "end": end_date,
                        "duration": duration,
                        "progress": progress,
                        "capex_curve": capex_curve
                    }
                )
                new_projects += 1
                print(f"Inserted: {title} | Sector: {sector} | Budget: {budget} | Location: {location} | Duration: {duration} | Progress: {progress} | Capex Curve: {capex_curve}")

            except Exception as e:
                print(f"Insert skipped for '{title}': {str(e)}")

    session.commit()
    print(f"Daily run finished. Added {new_projects} new projects.")
except Exception as e:
    print(f"Unexpected error: {str(e)}")
    session.rollback()
finally:
    session.close()
