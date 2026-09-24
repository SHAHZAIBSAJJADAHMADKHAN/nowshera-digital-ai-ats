from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


EmailEventType = Literal[
    "application_received",
    "interview_invitation",
    "application_hired",
    "application_rejected",
]
AutomationEventStatus = Literal["pending", "processing", "completed", "failed"]


class AutomationEventClaimRequest(BaseModel):
    event_types: list[EmailEventType] = Field(min_length=1, max_length=4)
    limit: int = Field(default=10, ge=1, le=25)


class AIEventClaimRequest(BaseModel):
    """No event type is accepted: this boundary is AI-only by design."""
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=10, ge=1, le=25)


class ClaimedAIProcessingEvent(BaseModel):
    event_id: UUID
    application_id: UUID
    attempt_count: int
    created_at: datetime


class AIEventClaimResponse(BaseModel):
    events: list[ClaimedAIProcessingEvent]


class ClaimedAutomationEvent(BaseModel):
    event_id: UUID
    event_type: EmailEventType
    aggregate_type: str
    aggregate_id: UUID
    payload: dict
    attempt_count: int
    created_at: datetime


class ClaimedEmailDeliveryEvent(ClaimedAutomationEvent):
    recipient_email: str
    candidate_name: str
    job_title: str
    interview_starts_at: datetime | None = None
    interview_location: str | None = None
    interview_meeting_link: str | None = None


class AutomationEventClaimResponse(BaseModel):
    events: list[ClaimedEmailDeliveryEvent]


class AutomationEventFailureRequest(BaseModel):
    error: str = Field(min_length=1, max_length=500)


class AutomationEventDeliveryResponse(BaseModel):
    event_id: UUID
    status: AutomationEventStatus
    attempt_count: int
    processed_at: datetime | None
    available_at: datetime
