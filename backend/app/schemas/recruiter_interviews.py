from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class RecruiterInterviewScheduleRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    starts_at: datetime
    location: str | None = None
    meeting_link: str | None = None
class RecruiterInterviewScheduleResponse(BaseModel):
    id: UUID
    application_id: UUID
    starts_at: datetime
    ends_at: datetime
    location: str | None
    meeting_link: str | None
