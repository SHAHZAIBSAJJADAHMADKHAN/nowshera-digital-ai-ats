from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.recruiter_ai_summary import RecruiterAISummaryResponse

Stage = Literal["applied", "shortlisted", "interview", "offer", "hired", "rejected", "withdrawn"]
JobType = Literal["full-time", "part-time", "internship"]


class AdminApplicationCandidate(BaseModel):
    id: UUID
    full_name: str
    email: str
    phone: str | None


class AdminApplicationJobSummary(BaseModel):
    id: UUID
    title: str
    department: str
    location: str
    job_type: JobType


class AdminApplicationJobDetail(AdminApplicationJobSummary):
    description: str
    requirements: str
    application_deadline: datetime


class AdminApplicationCV(BaseModel):
    id: UUID
    original_filename: str
    uploaded_at: datetime


class AdminApplicationStageHistory(BaseModel):
    stage: Stage
    changed_at: datetime


class AdminApplicationInterview(BaseModel):
    id: UUID
    starts_at: datetime
    ends_at: datetime | None
    location: str | None
    meeting_link: str | None


class AdminApplicationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    stage: Stage
    applied_at: datetime
    candidate: AdminApplicationCandidate
    job: AdminApplicationJobSummary
    cv: AdminApplicationCV


class AdminApplicationDetail(AdminApplicationListItem):
    job: AdminApplicationJobDetail
    stage_history: list[AdminApplicationStageHistory]
    interview: AdminApplicationInterview | None = None
    ai_summary: RecruiterAISummaryResponse | None = None


class AdminApplicationCVAccess(BaseModel):
    url: str
    expires_in: int
    application_id: UUID
    cv_id: UUID
    original_filename: str
