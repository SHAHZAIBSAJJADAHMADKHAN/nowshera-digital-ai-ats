from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authorization import CurrentUser, require_admin
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.admin_applications import AdminApplicationCVAccess, AdminApplicationDetail, AdminApplicationListItem
from app.services.admin_applications import AdminApplicationNotFoundError, AdminApplicationOperationError, AdminApplicationsService


router = APIRouter(prefix="/admin/applications", tags=["admin applications"])
T = TypeVar("T")


def get_service(client: SupabaseAdminClient = Depends(get_supabase_admin_client)) -> AdminApplicationsService:
    return AdminApplicationsService(client)


def _call(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except AdminApplicationNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found") from error
    except AdminApplicationOperationError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Admin application service is unavailable") from error


@router.get("", response_model=list[AdminApplicationListItem])
def list_applications(_: CurrentUser = Depends(require_admin), service: AdminApplicationsService = Depends(get_service)) -> list[AdminApplicationListItem]:
    return _call(service.list_applications)


@router.get("/{application_id}", response_model=AdminApplicationDetail)
def get_application(application_id: UUID, _: CurrentUser = Depends(require_admin), service: AdminApplicationsService = Depends(get_service)) -> AdminApplicationDetail:
    return _call(lambda: service.get_application(application_id))


@router.get("/{application_id}/cv/access", response_model=AdminApplicationCVAccess)
def cv_access(application_id: UUID, _: CurrentUser = Depends(require_admin), service: AdminApplicationsService = Depends(get_service)) -> AdminApplicationCVAccess:
    return _call(lambda: service.cv_access(application_id))
