"""Pydantic request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import TicketStatus, Urgency


class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    category: str | None = Field(default=None, max_length=100)
    urgency: Urgency | None = None


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    body: str
    created_at: datetime
    status: TicketStatus
    category: str | None
    urgency: Urgency | None
    ai_summary: str | None
    ai_suggested_reply: str | None
    final_reply: str | None
    reviewed_by: str | None

