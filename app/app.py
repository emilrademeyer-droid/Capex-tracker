import streamlit as st
import os
from sqlalchemy import create_engine, text
import pandas as pd

st.set_page_config(page_title="Capex Tracker", layout="wide")

st.title("Capex Tracker Dashboard")
st.write("Recent large Capex construction projects (> $10M).")

# DB connection
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

# Fetch recent projects
df = pd.read_sql(
    text("SELECT name, budget_usd, industry_sector, country, progress_percent, announcement_date, link FROM projects ORDER BY last_updated DESC LIMIT 50"),
    engine
)

st.subheader("Recent Projects")
st.dataframe(df, hide_index=True)

# Query interface
st.subheader("Search Projects")
keyword = st.text_input("Keyword (e.g., hotel, data center, Dubai)")
sector = st.selectbox("Sector", ["All", "Hospitality", "Data Centers", "Infrastructure / High-Rise", "Space / Lunar", "Unknown"])
budget_min = st.number_input("Minimum Budget (million USD)", min_value=10.0, value=10.0)

if st.button("Search"):
    query = "SELECT name, budget_usd, industry_sector, country, progress_percent, announcement_date, link FROM projects WHERE 1=1"
    params = {}
    if keyword:
        query += " AND (name ILIKE :keyword OR country ILIKE :keyword)"
        params["keyword"] = f"%{keyword}%"
    if sector != "All":
        query += " AND industry_sector = :sector"
        params["sector"] = sector
    if budget_min:
        query += " AND budget_usd >= :budget_min * 1000000"
        params["budget_min"] = budget_min
    query += " ORDER BY last_updated DESC LIMIT 50"
    df_search = pd.read_sql(text(query), engine, params=params)
    st.dataframe(df_search, hide_index=True)

# Trends (basic)
st.subheader("Trends")
col1, col2 = st.columns(2)
with col1:
    st.write("Projects by Sector")
    sector_counts = pd.read_sql("SELECT industry_sector, COUNT(*) as count FROM projects GROUP BY industry_sector", engine)
    st.bar_chart(sector_counts.set_index("industry_sector"))

with col2:
    st.write("Average Budget by Sector (million USD)")
    avg_budget = pd.read_sql("SELECT industry_sector, AVG(budget_usd / 1000000) as avg_budget FROM projects GROUP BY industry_sector", engine)
    st.bar_chart(avg_budget.set_index("industry_sector"))

st.info("Subscribe for premium features: advanced forecasts, export, notifications.")
