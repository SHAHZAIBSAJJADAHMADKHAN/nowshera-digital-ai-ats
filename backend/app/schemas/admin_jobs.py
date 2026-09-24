from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


JobType = Literal["full-time", "part-time", "internship"]
JobStatus = Literal["draft", "open", "closed"]


class _JobBusinessFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    department: str = Field(min_length=1)
    location: str = Field(min_length=1)
    job_type: JobType
    description: str = Field(min_length=1)
    requirements: str = Field(min_length=1)
    application_deadline: datetime
    openings: int = Field(gt=0)

    @field_validator("title", "department", "location", "description", "requirements")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("application_deadline")
    @classmethod
    def deadline_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("must be timezone-aware")
        return value


class JobCreate(_JobBusinessFields):
    pass


class JobUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1)
    department: str | None = Field(default=None, min_length=1)
    location: str | None = Field(default=None, min_length=1)
    job_type: JobType | None = None
    description: str | None = Field(default=None, min_length=1)
    requirements: str | None = Field(default=None, min_length=1)
    application_deadline: datetime | None = None
    openings: int | None = Field(default=None, gt=0)

    @field_validator("title", "department", "location", "description", "requirements")
    @classmethod
    def text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("application_deadline")
    @classmethod
    def deadline_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("must be timezone-aware")
        return value


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    department: str
    location: str
    job_type: JobType
    description: str
    requirements: str
    application_deadline: datetime
    openings: int
    status: JobStatus
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
