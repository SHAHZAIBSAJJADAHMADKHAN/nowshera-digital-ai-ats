from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import AuthenticatedPrincipal, get_authenticated_principal
from app.core.authorization import CurrentUser, require_candidate
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.candidate_profile import CandidateProfileResponse, CandidateProfileUpdate
from app.services.candidate_profile import CandidateProfileBootstrapConflictError, CandidateProfileBootstrapValidationError, CandidateProfileNotFoundError, CandidateProfileOperationError, CandidateProfileService


router = APIRouter(prefix="/candidate/profile", tags=["candidate profile"])
T = TypeVar("T")


def get_service(client: SupabaseAdminClient = Depends(get_supabase_admin_client)) -> CandidateProfileService:
    return CandidateProfileService(client)


def _call_service(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except CandidateProfileNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate profile not found") from error
    except CandidateProfileOperationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Candidate profile service is unavailable") from error


@router.get("", response_model=CandidateProfileResponse)
def get_profile(
    current_user: CurrentUser = Depends(require_candidate),
    service: CandidateProfileService = Depends(get_service),
) -> CandidateProfileResponse:
    return _call_service(lambda: service.get_profile(current_user.user_id))


@router.patch("", response_model=CandidateProfileResponse)
def update_profile(
    data: CandidateProfileUpdate,
    current_user: CurrentUser = Depends(require_candidate),
    service: CandidateProfileService = Depends(get_service),
) -> CandidateProfileResponse:
    return _call_service(lambda: service.update_profile(current_user.user_id, data))


@router.post("/bootstrap", response_model=CandidateProfileResponse)
def bootstrap_profile(
    principal: AuthenticatedPrincipal = Depends(get_authenticated_principal),
    service: CandidateProfileService = Depends(get_service),
) -> CandidateProfileResponse:
    try:
        return service.bootstrap_profile(principal)
    except CandidateProfileBootstrapConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Existing ATS profile cannot be bootstrapped as a candidate") from error
    except CandidateProfileBootstrapValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Candidate registration data is incomplete") from error
    except CandidateProfileOperationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Candidate profile service is unavailable") from error
