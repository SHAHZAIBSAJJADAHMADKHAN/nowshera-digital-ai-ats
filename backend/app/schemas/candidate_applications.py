from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CandidateApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cv_id: UUID


class CandidateApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    cv_id: UUID
    stage: Literal["applied"]
    applied_at: datetime
