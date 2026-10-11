"""Human review API rules and preservation of AI audit values."""

from app.models import Ticket, TicketStatus, Urgency


def _analyzed_ticket(db_session) -> Ticket:
    ticket = Ticket(
        subject="Password reset",
        body="I cannot access my account.",
        status=TicketStatus.analyzed,
        category="account",
        urgency=Urgency.high,
        ai_category="account",
        ai_urgency=Urgency.high,
        ai_suggested_reply="Hello, we are checking your reset link.",
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket


def test_approved_review_copies_ai_reply(client, db_session):
    ticket = _analyzed_ticket(db_session)
    response = client.post(f"/tickets/{ticket.id}/review", json={"action": "approved", "reviewer": "Mina"})

    assert response.status_code == 200
    result = response.json()
    assert result["final_reply"] == ticket.ai_suggested_reply
    assert result["status"] == "reviewed"
    assert result["review_action"] == "approved"


def test_edited_review_requires_final_reply(client, db_session):
    ticket = _analyzed_ticket(db_session)
    response = client.post(f"/tickets/{ticket.id}/review", json={"action": "edited", "reviewer": "Mina"})

    assert response.status_code == 422


def test_rejected_review_works(client, db_session):
    ticket = _analyzed_ticket(db_session)
    response = client.post(f"/tickets/{ticket.id}/review", json={"action": "rejected", "reviewer": "Mina"})

    assert response.status_code == 200
    assert response.json()["review_action"] == "rejected"
    assert response.json()["final_reply"] is None


def test_review_not_analyzed_ticket_returns_409(client):
    created = client.post("/tickets", json={"subject": "New", "body": "Needs review"})
    response = client.post(
        f"/tickets/{created.json()['id']}/review", json={"action": "rejected", "reviewer": "Mina"}
    )

    assert response.status_code == 409


def test_human_urgency_correction_preserves_ai_urgency(client, db_session):
    ticket = _analyzed_ticket(db_session)
    response = client.post(
        f"/tickets/{ticket.id}/review",
        json={"action": "rejected", "reviewer": "Mina", "urgency": "medium"},
    )

    assert response.status_code == 200
    assert response.json()["urgency"] == "medium"
    assert response.json()["ai_urgency"] == "high"


def test_invalid_human_category_returns_422(client, db_session):
    ticket = _analyzed_ticket(db_session)
    response = client.post(
        f"/tickets/{ticket.id}/review",
        json={"action": "rejected", "reviewer": "Mina", "category": "shipping"},
    )

    assert response.status_code == 422
