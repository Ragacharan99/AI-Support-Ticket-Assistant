"""Database-derived metrics endpoint tests with exact expected aggregates."""

from datetime import datetime, timedelta

from app.models import ReviewAction, Ticket, TicketStatus, Urgency


def test_metrics_empty_database_returns_zeroes_and_null_timings(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json() == {
        "counts": {"total": 0, "by_status": {"new": 0, "analyzed": 0, "reviewed": 0, "resolved": 0}},
        "review_actions": {
            "approved": {"count": 0, "percentage": 0.0},
            "edited": {"count": 0, "percentage": 0.0},
            "rejected": {"count": 0, "percentage": 0.0},
        },
        "ai_agreement": {"category_percentage": 0.0, "urgency_percentage": 0.0},
        "timing": {
            "time_to_resolution": {"avg_seconds": None, "median_seconds": None},
            "human_review_time": {"avg_seconds": None, "median_seconds": None},
        },
    }


def test_metrics_known_dataset(client, db_session):
    start = datetime(2025, 1, 1, 9, 0, 0)
    db_session.add_all(
        [
            Ticket(
                subject="approved", body="A", status=TicketStatus.reviewed, category="billing", ai_category="billing",
                urgency=Urgency.high, ai_urgency=Urgency.high, review_action=ReviewAction.approved,
                created_at=start, analyzed_at=start + timedelta(seconds=10), reviewed_at=start + timedelta(seconds=100),
            ),
            Ticket(
                subject="edited", body="B", status=TicketStatus.reviewed, category="technical", ai_category="account",
                urgency=Urgency.medium, ai_urgency=Urgency.medium, review_action=ReviewAction.edited,
                created_at=start, analyzed_at=start + timedelta(seconds=20), reviewed_at=start + timedelta(seconds=220),
            ),
            Ticket(
                subject="rejected", body="C", status=TicketStatus.reviewed, category="account", ai_category="account",
                urgency=Urgency.low, ai_urgency=Urgency.high, review_action=ReviewAction.rejected,
                created_at=start, analyzed_at=start + timedelta(seconds=50), reviewed_at=start + timedelta(seconds=350),
            ),
            Ticket(subject="new", body="D", status=TicketStatus.new),
        ]
    )
    db_session.commit()

    metrics = client.get("/metrics").json()

    assert metrics["counts"] == {"total": 4, "by_status": {"new": 1, "analyzed": 0, "reviewed": 3, "resolved": 0}}
    assert metrics["review_actions"] == {
        "approved": {"count": 1, "percentage": 33.33},
        "edited": {"count": 1, "percentage": 33.33},
        "rejected": {"count": 1, "percentage": 33.33},
    }
    assert metrics["ai_agreement"] == {"category_percentage": 66.67, "urgency_percentage": 66.67}
    assert metrics["timing"] == {
        "time_to_resolution": {"avg_seconds": 223.33, "median_seconds": 220.0},
        "human_review_time": {"avg_seconds": 196.67, "median_seconds": 200.0},
    }
