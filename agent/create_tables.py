import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Date, Numeric, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.exc import SQLAlchemyError

Base = declarative_base()

class Company(Base):
    __tablename__ = 'companies'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    type = Column(String(100))  # e.g. Owner, Contractor, Supplier
    location = Column(String(255))
    contact_info = Column(JSON)  # e.g. {"website": "...", "email": "..."}

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    owner_id = Column(Integer, ForeignKey('companies.id'))
    owner = relationship("Company", foreign_keys=[owner_id])
    gps = Column(String(100))  # "latitude,longitude"
    state = Column(String(100))
    country = Column(String(100))
    industry_sector = Column(String(100))
    architect_id = Column(Integer, ForeignKey('companies.id'))
    contractor_id = Column(Integer, ForeignKey('companies.id'))
    announcement_date = Column(Date)
    construction_start_date = Column(Date)
    construction_completion_date = Column(Date)
    client_handover_date = Column(Date)
    budget_usd = Column(Numeric(precision=18, scale=2))
    duration_months = Column(Numeric(precision=10, scale=2))
    progress_percent = Column(Numeric(precision=5, scale=2))
    capex_curve = Column(JSON)  # list of monthly spends
    last_updated = Column(Date, default=datetime.date.today)
    status = Column(String(50), default="Pending Data")

print("Starting table creation...")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: No DATABASE_URL in environment variables!")
    exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

try:
    engine = create_engine(DATABASE_URL, echo=True)  # echo=True logs SQL for debugging
    Base.metadata.create_all(engine)
    print("SUCCESS: Tables created (or already exist).")
    
    # Optional: Insert a test company to verify
    from sqlalchemy.orm import Session
    with Session(engine) as session:
        test_company = Company(name="Test Construction Ltd", type="Owner", location="Dubai, UAE")
        session.add(test_company)
        session.commit()
        print("Test company inserted successfully.")
except SQLAlchemyError as e:
    print(f"Database error: {str(e)}")
    exit(1)
except Exception as e:
    print(f"Unexpected error: {str(e)}")
    exit(1)

print("Script finished.")
