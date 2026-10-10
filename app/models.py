"""Database models."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class TicketStatus(str, Enum):
    new = "new"
    analyzed = "analyzed"
    reviewed = "reviewed"
    resolved = "resolved"


class Urgency(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Ticket(Base):
    """A customer support ticket and its AI/review metadata."""

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        SqlEnum(TicketStatus), default=TicketStatus.new, nullable=False
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    urgency: Mapped[Urgency | None] = mapped_column(SqlEnum(Urgency), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_suggested_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

