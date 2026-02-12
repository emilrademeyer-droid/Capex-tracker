import streamlit as st
import os
import pandas as pd
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Capex Tracker", layout="wide")

st.title("Capex Tracker Dashboard")
st.write("Recent large Capex construction projects (> $10M). Data updated daily.")

# DB connection
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

# Fetch projects
query = """
    SELECT 
        name,
        budget_usd,
        industry_sector,
        country,
        progress_percent,
        announcement_date,
        link
    FROM projects 
    ORDER BY last_updated DESC 
    LIMIT 50
"""
df = pd.read_sql(text(query), engine)

# Format budget
df['budget_formatted'] = df['budget_usd'].apply(lambda x: f"${x:,.0f}" if pd.notnull(x) else "N/A")

# Make link clickable
df['link'] = df['link'].apply(lambda x: f"[Link]({x})" if x else "N/A")

st.subheader("Recent Projects")
st.dataframe(
    df[['name', 'budget_formatted', 'industry_sector', 'country', 'progress_percent', 'announcement_date', 'link']],
    hide_index=True,
    column_config={
        "link": st.column_config.LinkColumn("Source", display_text="Link")
    }
)

# Search & Filter
st.subheader("Search & Filter")
col1, col2, col3 = st.columns(3)
with col1:
    keyword = st.text_input("Keyword (e.g., hotel, data center, Dubai)")
with col2:
    sector = st.selectbox("Sector", ["All"] + df['industry_sector'].dropna().unique().tolist())
with col3:
    budget_min = st.number_input("Min Budget (million USD)", min_value=0.0, value=10.0)

if st.button("Apply Filter"):
    filtered_df = df.copy()
    if keyword:
        filtered_df = filtered_df[filtered_df['name'].str.contains(keyword, case=False, na=False)]
    if sector != "All":
        filtered_df = filtered_df[filtered_df['industry_sector'] == sector]
    if budget_min:
        filtered_df = filtered_df[filtered_df['budget_usd'] >= budget_min * 1_000_000]
    st.dataframe(
        filtered_df[['name', 'budget_formatted', 'industry_sector', 'country', 'progress_percent', 'announcement_date', 'link']],
        hide_index=True,
        column_config={"link": st.column_config.LinkColumn("Source")}
    )

# Export
if st.button("Export to CSV"):
    csv = df.to_csv(index=False)
    st.download_button("Download CSV", csv, "capex_projects.csv", "text/csv")

# Basic trends
st.subheader("Trends")
col1, col2 = st.columns(2)
with col1:
    st.write("Projects by Sector")
    sector_counts = df['industry_sector'].value_counts()
    st.bar_chart(sector_counts)

with col2:
    st.write("Average Budget by Sector (million USD)")
    avg_budget = df.groupby('industry_sector')['budget_usd'].mean() / 1_000_000
    st.bar_chart(avg_budget)

st.info("Subscribe for premium features: advanced forecasts, notifications, export history.")
