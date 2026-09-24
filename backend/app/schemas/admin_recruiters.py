from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

class RecruiterCreate(BaseModel):
    full_name: str = Field(min_length=1,max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None,max_length=50)


class RecruiterUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=50)

    @field_validator("full_name")
    @classmethod
    def full_name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value.strip() if value is not None else None

    @field_validator("phone")
    @classmethod
    def phone_must_not_be_blank_when_present(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def must_update_at_least_one_allowed_field(self) -> "RecruiterUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one editable recruiter field is required")
        return self


class RecruiterProfileResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    phone: str | None
    role: Literal["recruiter"]
    is_active: bool
    created_at: datetime


class RecruiterReactivationResponse(BaseModel):
    recruiter: RecruiterProfileResponse
    changed: bool
