from uuid import UUID

import httpx

from app.schemas.admin_job_assignments import AssignedRecruiterResponse, AssignmentResult
from app.services.admin_jobs import AdminJobConflictError, AdminJobNotFoundError, AdminJobOperationError


class AdminJobAssignmentService:
    def __init__(self, client):
        self.client = client

    def _get_job(self, job_id: UUID | str) -> None:
        try:
            self.client.get_job(str(job_id))
        except LookupError as error:
            raise AdminJobNotFoundError("Job not found") from error
        except (ValueError, httpx.HTTPError) as error:
            raise AdminJobOperationError("Job retrieval is unavailable") from error

    def _get_recruiter(self, recruiter_id: UUID | str, require_active: bool) -> None:
        try:
            recruiter = self.client.get_assignment_recruiter(str(recruiter_id))
        except LookupError as error:
            raise AdminJobNotFoundError("Recruiter not found") from error
        except (ValueError, httpx.HTTPError) as error:
            raise AdminJobOperationError("Recruiter retrieval is unavailable") from error
        if recruiter["role"] != "recruiter":
            raise AdminJobConflictError("Target profile is not a recruiter")
        if require_active and not recruiter["is_active"]:
            raise AdminJobConflictError("Recruiter is inactive")

    def list_assigned_recruiters(self, job_id: UUID | str) -> list[AssignedRecruiterResponse]:
        self._get_job(job_id)
        try:
            assignments = self.client.list_assigned_recruiters(str(job_id))
            return [
                AssignedRecruiterResponse.model_validate({
                    "id": assignment["recruiter_id"],
                    "full_name": assignment["profiles"]["full_name"],
                    "email": assignment["profiles"]["email"],
                    "is_active": assignment["profiles"]["is_active"],
                    "assigned_at": assignment["assigned_at"],
                })
                for assignment in assignments
            ]
        except (ValueError, KeyError, TypeError, httpx.HTTPError) as error:
            raise AdminJobOperationError("Recruiter assignments are unavailable") from error

    def assign_recruiter(self, admin_id: str, job_id: UUID | str, recruiter_id: UUID | str) -> AssignmentResult:
        self._get_job(job_id)
        self._get_recruiter(recruiter_id, require_active=True)
        try:
            changed = self.client.assign_recruiter_to_job_rpc(admin_id, str(job_id), str(recruiter_id))
        except (ValueError, httpx.HTTPError) as error:
            raise AdminJobConflictError("Recruiter could not be assigned") from error
        return AssignmentResult(changed=changed)

    def unassign_recruiter(self, admin_id: str, job_id: UUID | str, recruiter_id: UUID | str) -> AssignmentResult:
        self._get_job(job_id)
        self._get_recruiter(recruiter_id, require_active=False)
        try:
            changed = self.client.unassign_recruiter_from_job_rpc(admin_id, str(job_id), str(recruiter_id))
        except (ValueError, httpx.HTTPError) as error:
            raise AdminJobConflictError("Recruiter could not be unassigned") from error
        return AssignmentResult(changed=changed)
