from uuid import UUID

import httpx
from pydantic import ValidationError

from app.schemas.admin_dashboard import AdminJobDashboardResponse


class AdminDashboardOperationError(Exception):
    """Raised when trusted dashboard data cannot be safely returned."""


class AdminDashboardService:
    def __init__(self, client):
        self.client = client

    def get_job_dashboard(self, admin_id: UUID | str) -> list[AdminJobDashboardResponse]:
        try:
            records = self.client.get_admin_job_dashboard(str(admin_id))
            if not isinstance(records, list):
                raise ValueError("Dashboard RPC returned a non-list result")
            return [AdminJobDashboardResponse.model_validate(record) for record in records]
        except (KeyError, TypeError, ValueError, ValidationError, httpx.HTTPError) as error:
            raise AdminDashboardOperationError("Dashboard data is unavailable") from error
