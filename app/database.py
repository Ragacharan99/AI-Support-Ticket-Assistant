"""SQLAlchemy engine, session, and declarative base."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for database models."""


def get_db():
    """Provide a request-scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

