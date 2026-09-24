from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

JobType = Literal['full-time','part-time','internship']
class CandidateJobListResponse(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: UUID; title: str; department: str; location: str; job_type: JobType; application_deadline: datetime; openings: int = Field(gt=0)
class CandidateJobDetailResponse(CandidateJobListResponse):
    description: str; requirements: str; created_at: datetime
