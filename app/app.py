import streamlit as st
import os
import pandas as pd
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Capex Tracker", layout="wide")

st.title("Capex Tracker Dashboard")
st.write("Recent large Capex construction projects (> $10M). Updated daily from web searches.")

# DB connection
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

# Fetch projects
df = pd.read_sql(
    text("""
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
        LIMIT 100
    """),
    engine
)

# Format budget
df['budget_formatted'] = df['budget_usd'].apply(
    lambda x: f"${x:,.0f}" if pd.notnull(x) else "N/A"
)

# Make link clickable
df['source'] = df['link'].apply(lambda x: f"[View]({x})" if x else "N/A")

st.subheader("Recent Projects")
st.dataframe(
    df[['name', 'budget_formatted', 'industry_sector', 'country', 'progress_percent', 'announcement_date', 'source']],
    hide_index=True,
    column_config={
        "source": st.column_config.LinkColumn("Source", display_text="View")
    }
)

# Search & Filter
st.subheader("Search & Filter")
col1, col2, col3 = st.columns(3)
with col1:
    keyword = st.text_input("Keyword (e.g., hotel, data center, Dubai, Meta)")
with col2:
    sector = st.selectbox("Sector", ["All"] + sorted(df['industry_sector'].dropna().unique().tolist()))
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
        filtered_df[['name', 'budget_formatted', 'industry_sector', 'country', 'progress_percent', 'announcement_date', 'source']],
        hide_index=True,
        column_config={"source": st.column_config.LinkColumn("Source")}
    )

# Export
if not df.empty:
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Export All to CSV",
        data=csv,
        file_name="capex_projects.csv",
        mime="text/csv"
    )

# Trends
st.subheader("Trends")
if not df.empty:
    col1, col2 = st.columns(2)
    with col1:
        st.write("Projects by Sector")
        sector_counts = df['industry_sector'].value_counts()
        st.bar_chart(sector_counts)

    with col2:
        st.write("Average Budget by Sector (million USD)")
        avg_budget = df.groupby('industry_sector')['budget_usd'].mean() / 1_000_000
        st.bar_chart(avg_budget)
else:
    st.info("No data yet — wait for daily run or trigger manually.")

st.info("Subscribe for premium: advanced forecasts, notifications, full export.")
