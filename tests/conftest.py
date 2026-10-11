"""Shared isolated database and AI mock fixtures for API tests."""

import importlib
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set this before importing the application: app.main initializes metadata on import.
# The dependency override below supplies the StaticPool database used by each test.
os.environ["DATABASE_URL"] = "sqlite://"

from app.database import Base, get_db
from app.services.ai_analyzer import AnalysisResult

main_module = importlib.import_module("app.main")


@pytest.fixture()
def db_session():
    """Create a fresh, shared in-memory SQLite database for one test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session, monkeypatch):
    """Serve requests against the test database and a non-network AI stub."""
    def override_get_db():
        yield db_session

    def fake_analyze_ticket(subject: str, body: str) -> AnalysisResult:
        return AnalysisResult(
            category="technical",
            urgency="high",
            summary=f"Summary for {subject}",
            suggested_reply=f"Reply for {body}",
        )

    main_module.app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(main_module, "analyze_ticket", fake_analyze_ticket)
    with TestClient(main_module.app) as test_client:
        yield test_client
    main_module.app.dependency_overrides.clear()
