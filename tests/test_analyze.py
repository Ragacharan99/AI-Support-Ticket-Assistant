"""Analysis endpoint success, state-transition, and failure tests."""

import importlib

from app.models import Ticket, TicketStatus
from app.services.ai_analyzer import AnalysisError, AnalysisResult

main_module = importlib.import_module("app.main")


def _create_ticket(client) -> int:
    response = client.post("/tickets", json={"subject": "Checkout fails", "body": "My card is declined."})
    assert response.status_code == 201
    return response.json()["id"]


def test_analyze_saves_result_and_audit_fields(client):
    ticket_id = _create_ticket(client)

    response = client.post(f"/tickets/{ticket_id}/analyze")

    assert response.status_code == 200
    ticket = response.json()
    assert ticket["status"] == "analyzed"
    assert ticket["category"] == ticket["ai_category"] == "technical"
    assert ticket["urgency"] == ticket["ai_urgency"] == "high"
    assert ticket["analyzed_at"] is not None
    assert ticket["ai_summary"]
    assert ticket["ai_suggested_reply"]


def test_analyze_missing_ticket_returns_404(client):
    assert client.post("/tickets/99999/analyze").status_code == 404


def test_analyze_twice_returns_409(client):
    ticket_id = _create_ticket(client)
    assert client.post(f"/tickets/{ticket_id}/analyze").status_code == 200
    assert client.post(f"/tickets/{ticket_id}/analyze").status_code == 409


def test_analysis_failure_returns_502_without_changing_ticket(client, db_session, monkeypatch):
    ticket_id = _create_ticket(client)

    def fail_analysis(subject: str, body: str) -> AnalysisResult:
        raise AnalysisError("provider unavailable")

    monkeypatch.setattr(main_module, "analyze_ticket", fail_analysis)
    response = client.post(f"/tickets/{ticket_id}/analyze")
    db_session.expire_all()
    ticket = db_session.get(Ticket, ticket_id)

    assert response.status_code == 502
    assert ticket.status == TicketStatus.new
    assert ticket.category is None
    assert ticket.ai_category is None
    assert ticket.analyzed_at is None
