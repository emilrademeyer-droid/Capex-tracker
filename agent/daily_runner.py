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
    payload = {"q": query, "num": 15, "tbs": "qdr:w"}  # past week
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json().get("organic", [])
    except Exception as e:
        print(f"Serper error for '{query}': {str(e)}")
        return []

def calculate_s_curve(budget, duration_months):
    if not budget or duration_months <= 0:
        return None
    time = np.linspace(0, 1, int(duration_months) + 1)
    k = 10
    midpoint = 0.55
    cash_percent = 1 / (1 + np.exp(-k * (time - midpoint)))
    cash_percent = cash_percent / cash_percent[-1]
    monthly_spend = np.diff(cash_percent, prepend=0) * budget
    return [round(x, 2) for x in monthly_spend.tolist()]

queries = [
    "new hotel construction project budget over $10 million announced after:2026-02-01",
    "data center build OR expansion budget $10 million+ after:2026-02-01",
    "airport OR high-rise tower construction project capex over $10 million 2026"
]

session = Session()
new_projects = 0
updated_projects = 0

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
                # Deduplication check - fetch existing row safely
                existing = session.execute(
                    text("SELECT id, budget_usd, construction_start_date, construction_completion_date FROM projects WHERE link = :link OR name = :name"),
                    {"link": link, "name": title}
                ).fetchone()

                text = title + " " + snippet

                # Extract budget
                budget_match = re.search(r'(\$[\d.,]+ ?(million|billion))', text, re.I)
                budget_str = budget_match.group(1) if budget_match else None
                budget = float(re.sub(r'[^\d.]', '', budget_str)) * (1e6 if "million" in (budget_str or "").lower() else 1e9) if budget_str else None

                # Extract location
                location_match = re.search(r'(Dubai|UAE|Saudi|Indiana|Louisiana|Pennsylvania|Texas|Utah|Wyoming|Georgetown|Wichita|Lebanon|Egypt|Moon|Lunar)', text, re.I)
                location = location_match.group(1) if location_match else "Unknown"

                # Extract sector
                sector = "Unknown"
                lower_text = text.lower()
                if "hotel" in lower_text or "hospitality" in lower_text:
                    sector = "Hospitality"
                elif "data center" in lower_text or "ai" in lower_text or "gigawatt" in lower_text:
                    sector = "Data Centers"
                elif "airport" in lower_text or "high-rise" in lower_text or "tower" in lower_text:
                    sector = "Infrastructure / High-Rise"
                elif "lunar" in lower_text or "moon" in lower_text:
                    sector = "Space / Lunar"

                # Extract dates
                start_match = re.search(r'(start|begin|break ground|construction start|announced|planned) (\d{4}(?:-\d{2}-\d{2})?)', text, re.I)
                start_str = start_match.group(2) if start_match else None
                start_date = datetime.datetime.strptime(start_str, '%Y-%m-%d').date() if start_str and '-' in start_str else (datetime.datetime.strptime(start_str, '%Y').date() if start_str else None)

                end_match = re.search(r'(complete|finish|open|completion|deliver) (\d{4}(?:-\d{2}-\d{2})?)', text, re.I)
                end_str = end_match.group(2) if end_match else None
                end_date = datetime.datetime.strptime(end_str, '%Y-%m-%d').date() if end_str and '-' in end_str else (datetime.datetime.strptime(end_str, '%Y').date() if end_str else None)

                duration = ((end_date - start_date).days / 30.4375) if start_date and end_date else None

                progress = None
                capex_curve = None
                if duration and start_date:
                    progress = min(max(((datetime.date.today() - start_date).days / (duration * 30.4375)) * 100, 0), 100)
                    capex_curve = calculate_s_curve(budget or (existing[1] if existing else None), duration)

                if existing:
                    project_id = existing[0]
                    updates = {}
                    if budget and not existing[1]:
                        updates["budget_usd"] = budget
                    if start_date and not existing[2]:
                        updates["construction_start_date"] = start_date
                    if end_date and not existing[3]:
                        updates["construction_completion_date"] = end_date
                    if duration:
                        updates["duration_months"] = duration
                    if progress is not None:
                        updates["progress_percent"] = progress
                    if capex_curve is not None:
                        updates["capex_curve"] = capex_curve
                    if updates:
                        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
                        session.execute(
                            text(f"UPDATE projects SET {set_clause}, last_updated = CURRENT_DATE WHERE id = :id"),
                            {**updates, "id": project_id}
                        )
                        updated_projects += 1
                        print(f"Updated project: {title} | Progress: {progress}% | Capex Curve: {capex_curve}")
                else:
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
                    print(f"Inserted new project: {title} | Budget: {budget} | Duration: {duration} | Progress: {progress}% | Capex Curve: {capex_curve}")

            except Exception as e:
                print(f"Error processing '{title}': {str(e)}")

    session.commit()
    print(f"Daily run finished. Added {new_projects} new | Updated {updated_projects} existing projects.")
except Exception as e:
    print(f"Unexpected error: {str(e)}")
    session.rollback()
finally:
    session.close()
