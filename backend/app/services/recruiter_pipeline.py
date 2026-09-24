from uuid import UUID

import httpx
from pydantic import ValidationError

from app.schemas.recruiter_pipeline import RecruiterApplicationTransitionResponse, RecruiterTransitionTarget


class RecruiterPipelineNotFoundError(Exception): pass
class RecruiterPipelineConflictError(Exception): pass
class RecruiterPipelineOperationError(Exception): pass


class RecruiterPipelineService:
    def __init__(self, client): self.client = client

    def transition(self, recruiter_id: str, application_id: UUID, stage: RecruiterTransitionTarget) -> RecruiterApplicationTransitionResponse:
        try:
            application = self.client.recruiter_app(str(application_id))
            self.client.recruiter_job(recruiter_id, application['job_id'])
            return RecruiterApplicationTransitionResponse.model_validate(
                self.client.transition_recruiter_application(recruiter_id, str(application_id), stage)
            )
        except LookupError as error:
            raise RecruiterPipelineNotFoundError() from error
        except ValueError as error:
            raise RecruiterPipelineConflictError() from error
        except (KeyError, TypeError, ValidationError, httpx.HTTPError) as error:
            raise RecruiterPipelineOperationError() from error
