from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


RecruiterTransitionTarget = Literal['shortlisted', 'offer', 'rejected']


class RecruiterApplicationTransitionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    stage: RecruiterTransitionTarget


class RecruiterApplicationTransitionResponse(BaseModel):
    id: UUID
    stage: RecruiterTransitionTarget
