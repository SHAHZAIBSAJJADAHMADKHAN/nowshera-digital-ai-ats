from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authorization import CurrentUser, require_candidate
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.candidate_application_tracking import CandidateApplicationDetailResponse, CandidateApplicationListResponse
from app.services.candidate_application_tracking import (
    CandidateApplicationTrackingNotFoundError,
    CandidateApplicationTrackingOperationError,
    CandidateApplicationTrackingService,
)


router = APIRouter(prefix="/candidate/applications", tags=["candidate application tracking"])


def get_service(client: SupabaseAdminClient = Depends(get_supabase_admin_client)) -> CandidateApplicationTrackingService:
    return CandidateApplicationTrackingService(client)


@router.get("", response_model=list[CandidateApplicationListResponse])
def list_applications(
    current_user: CurrentUser = Depends(require_candidate),
    service: CandidateApplicationTrackingService = Depends(get_service),
) -> list[CandidateApplicationListResponse]:
    try:
        return service.list_applications(current_user.user_id)
    except CandidateApplicationTrackingOperationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Candidate application service is unavailable") from error


@router.get("/{application_id}", response_model=CandidateApplicationDetailResponse)
def get_application(
    application_id: UUID,
    current_user: CurrentUser = Depends(require_candidate),
    service: CandidateApplicationTrackingService = Depends(get_service),
) -> CandidateApplicationDetailResponse:
    try:
        return service.get_application(current_user.user_id, application_id)
    except CandidateApplicationTrackingNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found") from error
    except CandidateApplicationTrackingOperationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Candidate application service is unavailable") from error
