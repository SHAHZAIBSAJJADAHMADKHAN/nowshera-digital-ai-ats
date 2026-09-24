from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authorization import CurrentUser, require_admin
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.admin_job_assignments import AssignedRecruiterResponse, AssignmentResult
from app.services.admin_job_assignments import AdminJobAssignmentService
from app.services.admin_jobs import AdminJobConflictError, AdminJobNotFoundError, AdminJobOperationError


router = APIRouter(prefix="/admin/jobs", tags=["admin job assignments"])
T = TypeVar("T")


def get_service(client: SupabaseAdminClient = Depends(get_supabase_admin_client)) -> AdminJobAssignmentService:
    return AdminJobAssignmentService(client)


def _call_service(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except AdminJobNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job or recruiter not found") from error
    except AdminJobConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recruiter assignment conflicts with its current state") from error
    except AdminJobOperationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Recruiter assignment service is unavailable") from error


@router.get("/{job_id}/recruiters", response_model=list[AssignedRecruiterResponse])
def list_assigned_recruiters(
    job_id: UUID,
    _: CurrentUser = Depends(require_admin),
    service: AdminJobAssignmentService = Depends(get_service),
) -> list[AssignedRecruiterResponse]:
    return _call_service(lambda: service.list_assigned_recruiters(job_id))


@router.post("/{job_id}/recruiters/{recruiter_id}", response_model=AssignmentResult)
def assign_recruiter(
    job_id: UUID,
    recruiter_id: UUID,
    current_user: CurrentUser = Depends(require_admin),
    service: AdminJobAssignmentService = Depends(get_service),
) -> AssignmentResult:
    return _call_service(lambda: service.assign_recruiter(current_user.user_id, job_id, recruiter_id))


@router.delete("/{job_id}/recruiters/{recruiter_id}", response_model=AssignmentResult)
def unassign_recruiter(
    job_id: UUID,
    recruiter_id: UUID,
    current_user: CurrentUser = Depends(require_admin),
    service: AdminJobAssignmentService = Depends(get_service),
) -> AssignmentResult:
    return _call_service(lambda: service.unassign_recruiter(current_user.user_id, job_id, recruiter_id))
