"""FastAPI application and ticket endpoints."""

from datetime import datetime
from pathlib import Path
from statistics import median

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.staticfiles import StaticFiles
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db, upgrade_sqlite_schema
from .models import ReviewAction, Ticket, TicketStatus, Urgency
from .schemas import TicketCreate, TicketRead, TicketReview
from .services.ai_analyzer import AnalysisError, analyze_ticket

Base.metadata.create_all(bind=engine)
upgrade_sqlite_schema()

app = FastAPI(title="Ticket Assistant API", version="0.1.0")


def _duration_summary(durations: list[float]) -> dict[str, float | None]:
    """Return rounded aggregate timings, or nulls when no complete timings exist."""
    if not durations:
        return {"avg_seconds": None, "median_seconds": None}
    return {
        "avg_seconds": round(sum(durations) / len(durations), 2),
        "median_seconds": round(median(durations), 2),
    }


@app.post("/tickets", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(ticket_in: TicketCreate, db: Session = Depends(get_db)) -> Ticket:
    """Create a new ticket with a default `new` status."""
    ticket = Ticket(**ticket_in.model_dump())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.get("/tickets", response_model=list[TicketRead])
def list_tickets(
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> list[Ticket]:
    """Return tickets, optionally filtered by status."""
    query = select(Ticket).order_by(Ticket.created_at.desc())
    if status_filter:
        query = query.where(Ticket.status == status_filter)
    return list(db.scalars(query))


@app.get("/tickets/queue", response_model=list[TicketRead])
def review_queue(db: Session = Depends(get_db)) -> list[Ticket]:
    """Return analyzed tickets in human-review priority order."""
    urgency_priority = case(
        (Ticket.urgency == Urgency.critical, 0),
        (Ticket.urgency == Urgency.high, 1),
        (Ticket.urgency == Urgency.medium, 2),
        (Ticket.urgency == Urgency.low, 3),
        else_=4,
    )
    query = (
        select(Ticket)
        .where(Ticket.status == TicketStatus.analyzed)
        .order_by(urgency_priority, Ticket.created_at.asc())
    )
    return list(db.scalars(query))


@app.get("/metrics")
def get_metrics(db: Session = Depends(get_db)) -> dict:
    """Summarize ticket workflow volume, AI agreement, and reviewed-ticket timings."""
    tickets = list(db.scalars(select(Ticket)))
    status_counts = {ticket_status.value: 0 for ticket_status in TicketStatus}
    for ticket in tickets:
        status_counts[ticket.status.value] += 1

    reviewed_tickets = [ticket for ticket in tickets if ticket.status == TicketStatus.reviewed]
    reviewed_count = len(reviewed_tickets)
    action_counts = {action.value: 0 for action in ReviewAction}
    for ticket in reviewed_tickets:
        if ticket.review_action is not None:
            action_counts[ticket.review_action.value] += 1

    category_agreements = sum(
        ticket.category is not None
        and ticket.ai_category is not None
        and ticket.category == ticket.ai_category
        for ticket in reviewed_tickets
    )
    urgency_agreements = sum(
        ticket.urgency is not None
        and ticket.ai_urgency is not None
        and ticket.urgency == ticket.ai_urgency
        for ticket in reviewed_tickets
    )
    time_to_resolution = [
        (ticket.reviewed_at - ticket.created_at).total_seconds()
        for ticket in reviewed_tickets
        if ticket.reviewed_at is not None and ticket.created_at is not None
    ]
    human_review_time = [
        (ticket.reviewed_at - ticket.analyzed_at).total_seconds()
        for ticket in reviewed_tickets
        if ticket.reviewed_at is not None and ticket.analyzed_at is not None
    ]
    percentage = lambda count, total: round((count / total * 100) if total else 0.0, 2)

    return {
        "counts": {"total": len(tickets), "by_status": status_counts},
        "review_actions": {
            action.value: {
                "count": action_counts[action.value],
                "percentage": percentage(action_counts[action.value], reviewed_count),
            }
            for action in ReviewAction
        },
        "ai_agreement": {
            "category_percentage": percentage(category_agreements, reviewed_count),
            "urgency_percentage": percentage(urgency_agreements, reviewed_count),
        },
        "timing": {
            "time_to_resolution": _duration_summary(time_to_resolution),
            "human_review_time": _duration_summary(human_review_time),
        },
    }


@app.get("/tickets/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)) -> Ticket:
    """Return a ticket by ID."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.post("/tickets/{ticket_id}/analyze", response_model=TicketRead)
def analyze_ticket_endpoint(ticket_id: int, db: Session = Depends(get_db)) -> Ticket:
    """Use the configured AI provider to analyze a new ticket."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.status != TicketStatus.new:
        raise HTTPException(status_code=409, detail="Only new tickets can be analyzed")

    try:
        analysis = analyze_ticket(ticket.subject, ticket.body)
    except AnalysisError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    ticket.category = analysis.category
    ticket.urgency = analysis.urgency
    ticket.ai_category = analysis.category
    ticket.ai_urgency = analysis.urgency
    ticket.ai_summary = analysis.summary
    ticket.ai_suggested_reply = analysis.suggested_reply
    ticket.analyzed_at = datetime.utcnow()
    ticket.status = TicketStatus.analyzed
    db.commit()
    db.refresh(ticket)
    return ticket


@app.post("/tickets/{ticket_id}/review", response_model=TicketRead)
def review_ticket(ticket_id: int, review: TicketReview, db: Session = Depends(get_db)) -> Ticket:
    """Record a human review decision for an analyzed ticket."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.status != TicketStatus.analyzed:
        raise HTTPException(status_code=409, detail="Only analyzed tickets can be reviewed")

    if review.action == ReviewAction.approved:
        ticket.final_reply = ticket.ai_suggested_reply
    elif review.action == ReviewAction.edited:
        ticket.final_reply = review.final_reply
    else:
        ticket.final_reply = review.final_reply

    if review.category is not None:
        ticket.category = review.category
    if review.urgency is not None:
        ticket.urgency = review.urgency

    ticket.reviewed_by = review.reviewer
    ticket.reviewed_at = datetime.utcnow()
    ticket.review_action = review.action
    ticket.status = TicketStatus.reviewed
    db.commit()
    db.refresh(ticket)
    return ticket


# Mount last so API routes keep precedence over the single-page application.
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
