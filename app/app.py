import streamlit as st
import os
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Capex Tracker", layout="wide")

st.title("Capex Tracker Dashboard")
st.write("Welcome! This is your construction projects tracker.")
st.write("Current status: Database connection test...")

# Try to connect to database (Render provides this URL automatically)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    try:
        # Fix postgres:// → postgresql:// for SQLAlchemy
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            st.success("Database connection successful! (SELECT 1 worked)")
    except Exception as e:
        st.error(f"Database connection failed: {str(e)}")
        st.info("The tables are not created yet – we will add that in the next step.")
else:
    st.warning("No DATABASE_URL found. This is normal during local testing, but on Render it should appear automatically.")
