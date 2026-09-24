from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


ApplicationStage = Literal["applied", "shortlisted", "interview", "offer", "hired", "rejected", "withdrawn"]
JobType = Literal["full-time", "part-time", "internship"]


class CandidateTrackingJobSummary(BaseModel):
    id: UUID
    title: str
    department: str
    location: str
    job_type: JobType
    application_deadline: datetime


class CandidateTrackingJobDetail(CandidateTrackingJobSummary):
    description: str
    requirements: str


class CandidateApplicationCVSnapshot(BaseModel):
    id: UUID
    original_filename: str
    uploaded_at: datetime


class CandidateApplicationStageHistory(BaseModel):
    stage: ApplicationStage
    changed_at: datetime


class CandidateApplicationInterview(BaseModel):
    starts_at: datetime
    ends_at: datetime
    location: str | None
    meeting_link: str | None


class CandidateApplicationListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    stage: ApplicationStage
    applied_at: datetime
    job: CandidateTrackingJobSummary
    cv: CandidateApplicationCVSnapshot


class CandidateApplicationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    stage: ApplicationStage
    applied_at: datetime
    job: CandidateTrackingJobDetail
    cv: CandidateApplicationCVSnapshot
    stage_history: list[CandidateApplicationStageHistory]
    interview: CandidateApplicationInterview | None
