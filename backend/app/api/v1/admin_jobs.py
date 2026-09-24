from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authorization import CurrentUser, require_admin
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.admin_jobs import JobCreate, JobResponse, JobUpdate
from app.services.admin_jobs import (
    AdminJobConflictError,
    AdminJobNotFoundError,
    AdminJobOperationError,
    AdminJobService,
)


router = APIRouter(prefix="/admin/jobs", tags=["admin jobs"])
T = TypeVar("T")


def get_service(client: SupabaseAdminClient = Depends(get_supabase_admin_client)) -> AdminJobService:
    return AdminJobService(client)


def _call_service(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except AdminJobNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from error
    except AdminJobConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job operation conflicts with its current state") from error
    except AdminJobOperationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Job service is unavailable") from error


@router.get("", response_model=list[JobResponse])
def list_jobs(
    _: CurrentUser = Depends(require_admin),
    service: AdminJobService = Depends(get_service),
) -> list[JobResponse]:
    return _call_service(service.list_jobs)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: UUID,
    _: CurrentUser = Depends(require_admin),
    service: AdminJobService = Depends(get_service),
) -> JobResponse:
    return _call_service(lambda: service.get_job(job_id))


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    data: JobCreate,
    current_user: CurrentUser = Depends(require_admin),
    service: AdminJobService = Depends(get_service),
) -> JobResponse:
    return _call_service(lambda: service.create_job(current_user.user_id, data))


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: UUID,
    data: JobUpdate,
    current_user: CurrentUser = Depends(require_admin),
    service: AdminJobService = Depends(get_service),
) -> JobResponse:
    return _call_service(lambda: service.update_job(current_user.user_id, job_id, data))


@router.post("/{job_id}/open", response_model=JobResponse)
def open_job(
    job_id: UUID,
    current_user: CurrentUser = Depends(require_admin),
    service: AdminJobService = Depends(get_service),
) -> JobResponse:
    return _call_service(lambda: service.open_job(current_user.user_id, job_id))


@router.post("/{job_id}/close", response_model=JobResponse)
def close_job(
    job_id: UUID,
    current_user: CurrentUser = Depends(require_admin),
    service: AdminJobService = Depends(get_service),
) -> JobResponse:
    return _call_service(lambda: service.close_job(current_user.user_id, job_id))
