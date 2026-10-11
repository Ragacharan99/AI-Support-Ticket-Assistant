"""Tests for the priority-ordered human review queue."""

from datetime import datetime, timedelta

from app.models import Ticket, TicketStatus, Urgency


def _ticket(subject: str, urgency: Urgency, created_at: datetime) -> Ticket:
    return Ticket(
        subject=subject,
        body="Queue test",
        status=TicketStatus.analyzed,
        urgency=urgency,
        ai_category="technical",
        ai_urgency=urgency,
        created_at=created_at,
    )


def test_queue_includes_only_analyzed_tickets_in_priority_order(client, db_session):
    start = datetime(2025, 1, 1, 9, 0, 0)
    db_session.add_all(
        [
            _ticket("low", Urgency.low, start),
            _ticket("medium", Urgency.medium, start + timedelta(minutes=1)),
            _ticket("high", Urgency.high, start + timedelta(minutes=2)),
            _ticket("critical newer", Urgency.critical, start + timedelta(minutes=4)),
            _ticket("critical older", Urgency.critical, start + timedelta(minutes=3)),
            Ticket(subject="new", body="Not ready", status=TicketStatus.new, urgency=Urgency.critical),
        ]
    )
    db_session.commit()

    response = client.get("/tickets/queue")

    assert response.status_code == 200
    assert [ticket["subject"] for ticket in response.json()] == [
        "critical older",
        "critical newer",
        "high",
        "medium",
        "low",
    ]
