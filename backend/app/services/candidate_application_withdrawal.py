from uuid import UUID

import httpx
from pydantic import ValidationError

from app.schemas.candidate_application_withdrawal import CandidateApplicationWithdrawalResponse


class CandidateWithdrawalNotFoundError(Exception):
    pass


class CandidateWithdrawalConflictError(Exception):
    pass


class CandidateWithdrawalOperationError(Exception):
    pass


class CandidateApplicationWithdrawalService:
    def __init__(self, client):
        self.client = client

    def withdraw_application(self, candidate_id: UUID | str, application_id: UUID | str) -> CandidateApplicationWithdrawalResponse:
        try:
            record = self.client.withdraw_candidate_application(str(candidate_id), str(application_id))
            return CandidateApplicationWithdrawalResponse.model_validate(record)
        except CandidateWithdrawalNotFoundError:
            raise
        except CandidateWithdrawalConflictError:
            raise
        except (KeyError, TypeError, ValueError, ValidationError, httpx.HTTPError) as error:
            raise CandidateWithdrawalOperationError() from error
