"""
Database connection and session management.
"""
from sqlmodel import SQLModel, Session, create_engine
from app.config import DATABASE_URL

# Create database engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get database session - use as dependency in FastAPI."""
    with Session(engine) as session:
        yield session
