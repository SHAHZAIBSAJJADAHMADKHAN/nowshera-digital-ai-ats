from uuid import UUID

import httpx
from pydantic import ValidationError

from app.schemas.candidate_profile import CandidateProfileResponse, CandidateProfileUpdate


class CandidateProfileNotFoundError(Exception):
    """Raised when the authenticated candidate has no application profile."""


class CandidateProfileOperationError(Exception):
    """Raised when a trusted candidate profile operation cannot complete."""


class CandidateProfileService:
    def __init__(self, client):
        self.client = client

    def get_profile(self, candidate_id: UUID | str) -> CandidateProfileResponse:
        try:
            return CandidateProfileResponse.model_validate(self.client.get_candidate_profile(str(candidate_id)))
        except LookupError as error:
            raise CandidateProfileNotFoundError("Candidate profile not found") from error
        except (KeyError, TypeError, ValueError, ValidationError, httpx.HTTPError) as error:
            raise CandidateProfileOperationError("Candidate profile is unavailable") from error

    def update_profile(self, candidate_id: UUID | str, data: CandidateProfileUpdate) -> CandidateProfileResponse:
        try:
            self.client.update_candidate_profile(str(candidate_id), data.model_dump(exclude_unset=True))
        except LookupError as error:
            raise CandidateProfileNotFoundError("Candidate profile not found") from error
        except (KeyError, TypeError, ValueError, httpx.HTTPError) as error:
            raise CandidateProfileOperationError("Candidate profile update is unavailable") from error
        return self.get_profile(candidate_id)
