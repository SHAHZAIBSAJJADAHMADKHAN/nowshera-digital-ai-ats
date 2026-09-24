from collections.abc import Callable
from typing import TypeVar

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.authorization import CurrentUser, require_candidate
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.candidate_cvs import CandidateCVAccessResponse, CandidateCVResponse
from app.services.candidate_cvs import CandidateCVService, CandidateCVValidationError, MAX_CV_BYTES
from app.services.candidate_profile import CandidateProfileNotFoundError, CandidateProfileOperationError


router = APIRouter(prefix="/candidate/cvs", tags=["candidate CV metadata"])
T = TypeVar("T")


def get_service(client: SupabaseAdminClient = Depends(get_supabase_admin_client)) -> CandidateCVService:
    return CandidateCVService(client)


def _call_service(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except CandidateProfileNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate CV not found") from error
    except CandidateProfileOperationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Candidate CV metadata service is unavailable") from error


@router.post("", response_model=CandidateCVResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile,
    current_user: CurrentUser = Depends(require_candidate),
    service: CandidateCVService = Depends(get_service),
) -> CandidateCVResponse:
    content = await file.read(MAX_CV_BYTES + 1)
    try:
        return _call_service(lambda: service.upload_cv(current_user.user_id, file.filename, file.content_type, content))
    except CandidateCVValidationError as error:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE if len(content) > MAX_CV_BYTES else status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

@router.get("/{cv_id}/access", response_model=CandidateCVAccessResponse)
def get_cv_access(cv_id: UUID, current_user: CurrentUser = Depends(require_candidate), service: CandidateCVService = Depends(get_service)) -> CandidateCVAccessResponse:
    return _call_service(lambda: service.get_cv_access(current_user.user_id, cv_id))


@router.get("", response_model=list[CandidateCVResponse])
def list_cvs(
    current_user: CurrentUser = Depends(require_candidate),
    service: CandidateCVService = Depends(get_service),
) -> list[CandidateCVResponse]:
    return _call_service(lambda: service.list_cvs(current_user.user_id))
