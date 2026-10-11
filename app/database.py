"""SQLAlchemy engine, session, and declarative base."""

from sqlalchemy import create_engine, inspect, text
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


def upgrade_sqlite_schema() -> None:
    """Add review fields to existing local SQLite databases without data loss."""
    if engine.dialect.name != "sqlite" or "tickets" not in inspect(engine).get_table_names():
        return

    existing_columns = {column["name"] for column in inspect(engine).get_columns("tickets")}
    additions = {
        "analyzed_at": "DATETIME",
        "reviewed_at": "DATETIME",
        "review_action": "VARCHAR(20)",
        "ai_category": "VARCHAR(100)",
        "ai_urgency": "VARCHAR(20)",
    }
    with engine.begin() as connection:
        for name, column_type in additions.items():
            if name not in existing_columns:
                connection.execute(text(f"ALTER TABLE tickets ADD COLUMN {name} {column_type}"))

