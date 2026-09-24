from uuid import UUID

import httpx
from pydantic import ValidationError

from app.schemas.candidate_applications import CandidateApplicationResponse


class CandidateApplicationConflictError(Exception):
    pass


class CandidateApplicationUnavailableError(Exception):
    pass


class CandidateApplicationCVError(Exception):
    pass


class CandidateApplicationOperationError(Exception):
    pass


class CandidateApplicationService:
    def __init__(self, client):
        self.client = client

    def submit_application(
        self, candidate_id: UUID | str, job_id: UUID | str, cv_id: UUID | str
    ) -> CandidateApplicationResponse:
        try:
            record = self.client.submit_candidate_application(
                str(candidate_id), str(job_id), str(cv_id)
            )
            return CandidateApplicationResponse.model_validate(record)
        except CandidateApplicationConflictError:
            raise
        except CandidateApplicationUnavailableError:
            raise
        except CandidateApplicationCVError:
            raise
        except (KeyError, TypeError, ValueError, ValidationError, httpx.HTTPError) as error:
            raise CandidateApplicationOperationError() from error
