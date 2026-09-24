from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CandidateCVResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int = Field(gt=0, le=2_097_152)
    uploaded_at: datetime

class CandidateCVAccessResponse(BaseModel):
    url: str
    expires_in: int = Field(ge=1, le=300)
    cv_id: UUID
    original_filename: str
