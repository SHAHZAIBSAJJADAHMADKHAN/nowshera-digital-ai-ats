from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authorization import CurrentUser, require_admin
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.admin_dashboard import AdminJobDashboardResponse
from app.services.admin_dashboard import AdminDashboardOperationError, AdminDashboardService


router = APIRouter(prefix="/admin/dashboard", tags=["admin dashboard"])
T = TypeVar("T")


def get_service(client: SupabaseAdminClient = Depends(get_supabase_admin_client)) -> AdminDashboardService:
    return AdminDashboardService(client)


def _call_service(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except AdminDashboardOperationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dashboard service is unavailable",
        ) from error


@router.get("/jobs", response_model=list[AdminJobDashboardResponse])
def get_job_dashboard(
    current_user: CurrentUser = Depends(require_admin),
    service: AdminDashboardService = Depends(get_service),
) -> list[AdminJobDashboardResponse]:
    return _call_service(lambda: service.get_job_dashboard(current_user.user_id))
