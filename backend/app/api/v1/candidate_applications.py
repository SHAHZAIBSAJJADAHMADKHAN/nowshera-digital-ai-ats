from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authorization import CurrentUser, require_candidate
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.candidate_applications import CandidateApplicationCreate, CandidateApplicationResponse
from app.services.candidate_applications import (
    CandidateApplicationConflictError,
    CandidateApplicationCVError,
    CandidateApplicationOperationError,
    CandidateApplicationService,
    CandidateApplicationUnavailableError,
)


router = APIRouter(prefix="/candidate/jobs", tags=["candidate applications"])


def get_service(
    client: SupabaseAdminClient = Depends(get_supabase_admin_client),
) -> CandidateApplicationService:
    return CandidateApplicationService(client)


@router.post("/{job_id}/applications", response_model=CandidateApplicationResponse, status_code=status.HTTP_201_CREATED)
def submit_application(
    job_id: UUID,
    data: CandidateApplicationCreate,
    current_user: CurrentUser = Depends(require_candidate),
    service: CandidateApplicationService = Depends(get_service),
) -> CandidateApplicationResponse:
    try:
        return service.submit_application(current_user.user_id, job_id, data.cv_id)
    except CandidateApplicationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have an active application for this job.") from error
    except CandidateApplicationUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This job is not available for applications.") from error
    except CandidateApplicationCVError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected CV is not available.") from error
    except CandidateApplicationOperationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Candidate application service is unavailable") from error
