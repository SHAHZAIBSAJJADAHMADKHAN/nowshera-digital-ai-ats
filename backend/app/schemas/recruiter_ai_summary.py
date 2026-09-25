from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


AIStatus = Literal["pending", "processing", "completed", "failed", "unavailable"]


class RecruiterAISummaryResponse(BaseModel):
    application_id: UUID
    status: AIStatus
    is_ai_generated: bool = True
    summary_available: bool
    profile_bullets: list[str] | None = None
    requirements_found: list[str] | None = None
    requirements_not_found: list[str] | None = None
    interview_questions: list[str] | None = None


class AIRequirementsAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirements_mentioned: list[str]
    requirements_not_found: list[str]


class AICompletedSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_summary: list[str] = Field(min_length=3, max_length=5)
    requirements_analysis: AIRequirementsAnalysis
    interview_questions: list[str] = Field(min_length=3, max_length=3)


class AIContextResponse(BaseModel):
    """Prepared prompt available only to the trusted automation worker."""

    application_id: UUID
    prompt: str


class AIResultIngestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["completed", "failed"]
    summary: AICompletedSummary | None = None
    error: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_outcome(self):
        if self.status == "completed" and (self.summary is None or self.error is not None):
            raise ValueError("Completed AI results require only a structured summary")
        if self.status == "failed" and (self.summary is not None or self.error is None):
            raise ValueError("Failed AI results require only a safe error message")
        return self
