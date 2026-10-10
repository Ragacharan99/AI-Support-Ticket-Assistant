"""FastAPI application and ticket endpoints."""

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Ticket, TicketStatus
from .schemas import TicketCreate, TicketRead

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Ticket Assistant API", version="0.1.0")


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


@app.get("/tickets/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)) -> Ticket:
    """Return a ticket by ID."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket
