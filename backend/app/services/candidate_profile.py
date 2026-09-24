from uuid import UUID

import httpx
from pydantic import ValidationError

from app.core.auth import AuthenticatedPrincipal
from app.schemas.candidate_profile import CandidateProfileBootstrap, CandidateProfileResponse, CandidateProfileUpdate


class CandidateProfileNotFoundError(Exception):
    """Raised when the authenticated candidate has no application profile."""


class CandidateProfileOperationError(Exception):
    """Raised when a trusted candidate profile operation cannot complete."""


class CandidateProfileBootstrapConflictError(Exception):
    """Raised when an existing non-candidate profile cannot be bootstrapped."""


class CandidateProfileBootstrapValidationError(Exception):
    """Raised when trusted Auth data cannot form a candidate profile."""


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

    def bootstrap_profile(self, principal: AuthenticatedPrincipal) -> CandidateProfileResponse:
        candidate_id = str(principal.user_id)
        try:
            existing = self.client.get_profile_identity(candidate_id)
            if existing:
                if existing.get("role") != "candidate":
                    raise CandidateProfileBootstrapConflictError("Existing profile is not a candidate")
                return self.get_profile(candidate_id)

            auth_user = self.client.get_auth_user(candidate_id)
            if auth_user.get("id") != candidate_id:
                raise CandidateProfileBootstrapValidationError("Authenticated user mismatch")
            metadata = auth_user.get("user_metadata")
            bootstrap = CandidateProfileBootstrap(
                full_name=metadata.get("full_name") if isinstance(metadata, dict) else None,
                email=auth_user.get("email"),
            )
            self.client.bootstrap_candidate_profile(candidate_id, bootstrap.full_name, str(bootstrap.email))
            return self.get_profile(candidate_id)
        except CandidateProfileBootstrapConflictError:
            raise
        except (ValidationError, KeyError, TypeError, ValueError) as error:
            raise CandidateProfileBootstrapValidationError("Candidate profile data is invalid") from error
        except (LookupError, httpx.HTTPError) as error:
            raise CandidateProfileOperationError("Candidate profile bootstrap is unavailable") from error
