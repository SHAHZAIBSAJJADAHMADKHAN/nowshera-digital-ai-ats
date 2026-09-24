from uuid import UUID

import httpx

from app.schemas.admin_jobs import JobCreate, JobResponse, JobUpdate


class AdminJobNotFoundError(Exception):
    """Raised when the requested job does not exist."""


class AdminJobConflictError(Exception):
    """Raised when the database rejects a job lifecycle or business operation."""


class AdminJobOperationError(Exception):
    """Raised when the trusted job integration cannot complete an operation."""


class AdminJobService:
    def __init__(self, client):
        self.client = client

    def list_jobs(self, limit: int = 50, offset: int = 0) -> list[JobResponse]:
        try:
            return [JobResponse.model_validate(job) for job in self.client.list_jobs(limit, offset)]
        except (ValueError, httpx.HTTPError) as error:
            raise AdminJobOperationError("Job listing is unavailable") from error

    def get_job(self, job_id: UUID | str) -> JobResponse:
        try:
            return JobResponse.model_validate(self.client.get_job(str(job_id)))
        except LookupError as error:
            raise AdminJobNotFoundError("Job not found") from error
        except (ValueError, httpx.HTTPError) as error:
            raise AdminJobOperationError("Job retrieval is unavailable") from error

    def create_job(self, admin_id: str, data: JobCreate) -> JobResponse:
        try:
            job_id = self.client.create_draft_job(admin_id, data.model_dump(mode="json"))
            return self.get_job(job_id)
        except AdminJobNotFoundError as error:
            raise AdminJobOperationError("Created job could not be retrieved") from error
        except (ValueError, httpx.HTTPError) as error:
            raise AdminJobConflictError("Job could not be created") from error

    def update_job(self, admin_id: str, job_id: UUID | str, data: JobUpdate) -> JobResponse:
        current = self.get_job(job_id)
        merged = current.model_copy(update=data.model_dump(exclude_unset=True))
        business_fields = {
            "title": merged.title,
            "department": merged.department,
            "location": merged.location,
            "job_type": merged.job_type,
            "description": merged.description,
            "requirements": merged.requirements,
            "application_deadline": merged.application_deadline,
            "openings": merged.openings,
        }
        try:
            self.client.update_draft_job(admin_id, str(job_id), JobCreate.model_validate(business_fields).model_dump(mode="json"))
        except (ValueError, httpx.HTTPError) as error:
            raise AdminJobConflictError("Job could not be updated") from error
        return self.get_job(job_id)

    def open_job(self, admin_id: str, job_id: UUID | str) -> JobResponse:
        self.get_job(job_id)
        try:
            self.client.open_job_rpc(admin_id, str(job_id))
        except (ValueError, httpx.HTTPError) as error:
            raise AdminJobConflictError("Job could not be opened") from error
        return self.get_job(job_id)

    def close_job(self, admin_id: str, job_id: UUID | str) -> JobResponse:
        self.get_job(job_id)
        try:
            self.client.close_job_rpc(admin_id, str(job_id))
        except (ValueError, httpx.HTTPError) as error:
            raise AdminJobConflictError("Job could not be closed") from error
        return self.get_job(job_id)
