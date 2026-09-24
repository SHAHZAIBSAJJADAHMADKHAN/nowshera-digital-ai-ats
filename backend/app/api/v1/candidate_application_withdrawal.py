from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authorization import CurrentUser, require_candidate
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.candidate_application_withdrawal import CandidateApplicationWithdrawalResponse
from app.services.candidate_application_withdrawal import (
    CandidateApplicationWithdrawalService,
    CandidateWithdrawalConflictError,
    CandidateWithdrawalNotFoundError,
    CandidateWithdrawalOperationError,
)


router = APIRouter(prefix="/candidate/applications", tags=["candidate application withdrawal"])


def get_service(client: SupabaseAdminClient = Depends(get_supabase_admin_client)) -> CandidateApplicationWithdrawalService:
    return CandidateApplicationWithdrawalService(client)


@router.post("/{application_id}/withdraw", response_model=CandidateApplicationWithdrawalResponse)
def withdraw_application(
    application_id: UUID,
    current_user: CurrentUser = Depends(require_candidate),
    service: CandidateApplicationWithdrawalService = Depends(get_service),
) -> CandidateApplicationWithdrawalResponse:
    try:
        return service.withdraw_application(current_user.user_id, application_id)
    except CandidateWithdrawalNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found") from error
    except CandidateWithdrawalConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This application cannot be withdrawn.") from error
    except CandidateWithdrawalOperationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Candidate application service is unavailable") from error
