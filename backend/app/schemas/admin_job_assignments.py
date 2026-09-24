from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class AssignedRecruiterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    full_name: str
    email: EmailStr
    is_active: bool
    assigned_at: datetime


class AssignmentResult(BaseModel):
    changed: bool
