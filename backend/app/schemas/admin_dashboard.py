from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.admin_jobs import JobStatus


class AdminJobDashboardResponse(BaseModel):
    """One trusted current-state dashboard aggregate returned by the jobs RPC."""

    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    title: str
    department: str
    status: JobStatus
    application_deadline: datetime
    openings: int = Field(gt=0)
    total_applied: int = Field(ge=0, strict=True)
    applied_count: int = Field(ge=0, strict=True)
    shortlisted_count: int = Field(ge=0, strict=True)
    interview_count: int = Field(ge=0, strict=True)
    offer_count: int = Field(ge=0, strict=True)
    hired_count: int = Field(ge=0, strict=True)
    rejected_count: int = Field(ge=0, strict=True)
    withdrawn_count: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def total_must_match_current_stage_counts(self) -> "AdminJobDashboardResponse":
        stage_total = (
            self.applied_count
            + self.shortlisted_count
            + self.interview_count
            + self.offer_count
            + self.hired_count
            + self.rejected_count
            + self.withdrawn_count
        )
        if self.total_applied != stage_total:
            raise ValueError("total_applied must equal the sum of current-stage counts")
        return self
