"""Pydantic request and response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import ReviewAction, TicketStatus, Urgency


class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    body: str
    created_at: datetime
    status: TicketStatus
    category: str | None
    urgency: Urgency | None
    ai_category: str | None
    ai_urgency: Urgency | None
    ai_summary: str | None
    ai_suggested_reply: str | None
    analyzed_at: datetime | None
    final_reply: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_action: ReviewAction | None


class TicketReview(BaseModel):
    """A human reviewer decision for an analyzed ticket."""

    action: ReviewAction
    reviewer: str = Field(min_length=1, max_length=100)
    final_reply: str | None = Field(default=None, min_length=1)
    category: Literal["billing", "technical", "account", "feature_request", "other"] | None = None
    urgency: Urgency | None = None

    @model_validator(mode="after")
    def edited_tickets_need_a_final_reply(self) -> "TicketReview":
        if self.action == ReviewAction.edited and self.final_reply is None:
            raise ValueError("final_reply is required when action is 'edited'")
        return self

