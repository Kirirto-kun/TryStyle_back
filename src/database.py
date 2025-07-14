from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Ensure the URL uses the correct scheme for SQLAlchemy / psycopg
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set. Please provide it in your .env file.")

# Configure robust connection pool settings to prevent exhaustion
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,              # Increase from default 5 to handle more concurrent requests
    max_overflow=30,           # Increase from default 10, total 50 connections available
    pool_timeout=60,           # Increase timeout from default 30s to 60s
    pool_recycle=3600,         # Recycle connections every hour to prevent stale connections
    pool_pre_ping=True,        # Validate connections before use to catch dropped connections
    echo=False,                # Set to True for SQL debugging if needed
    connect_args={
        "connect_timeout": 10,  # Connection timeout for initial database connection
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    """
    Create a database session for scripts and background tasks.
    Must be manually closed by calling db.close().
    """
    return SessionLocal()

def get_connection_pool_status():
    """
    Get current connection pool status for monitoring.
    Returns dict with pool metrics.
    """
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in_connections": pool.checkedin(),
        "checked_out_connections": pool.checkedout(),
        "overflow_connections": pool.overflow(),
        "total_capacity": pool.size() + pool.overflow()
    }