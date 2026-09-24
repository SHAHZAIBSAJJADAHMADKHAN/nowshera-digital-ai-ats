from typing import Literal
from uuid import UUID
from pydantic import BaseModel

class RecruiterHireResponse(BaseModel):
    id: UUID
    job_id: UUID
    stage: Literal['hired']
    job_status: Literal['open', 'closed']
