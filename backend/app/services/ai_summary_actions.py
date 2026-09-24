from uuid import UUID

import httpx

from app.schemas.recruiter_ai_summary import AIResultIngestionRequest, RecruiterAISummaryResponse
from app.services.recruiter_ai_summary import RecruiterAISummaryNotFoundError, RecruiterAISummaryOperationError, RecruiterAISummaryService


class AISummaryRetryConflictError(Exception):
    pass


class AISummaryRetryOperationError(Exception):
    pass


class AISummaryActionsService:
    def __init__(self, client):
        self.client = client

    def retry(self, actor_id: str, application_id: UUID) -> None:
        try:
            self.client.retry_ai_summary(actor_id, str(application_id))
        except ValueError as error:
            raise AISummaryRetryConflictError() from error
        except (KeyError, TypeError, httpx.HTTPError) as error:
            raise AISummaryRetryOperationError() from error

    def ingest(self, application_id: UUID, data: AIResultIngestionRequest) -> None:
        try:
            summary = data.summary
            self.client.save_ai_summary_result(
                str(application_id), data.status,
                summary.profile_summary if summary else None,
                summary.requirements_analysis.requirements_mentioned if summary else None,
                summary.requirements_analysis.requirements_not_found if summary else None,
                summary.interview_questions if summary else None,
                data.error,
            )
        except ValueError as error:
            raise AISummaryRetryConflictError() from error
        except (KeyError, TypeError, httpx.HTTPError) as error:
            raise AISummaryRetryOperationError() from error


class AdminAISummaryService:
    def __init__(self, client):
        self.client = client

    def get_summary(self, application_id: UUID) -> RecruiterAISummaryResponse:
        try:
            row = self.client.admin_ai_summary(str(application_id))
            if row is None:
                return RecruiterAISummaryResponse(application_id=application_id, status="unavailable", summary_available=False)
            return RecruiterAISummaryService(self.client)._result(application_id, row)
        except LookupError as error:
            raise RecruiterAISummaryNotFoundError() from error
        except (KeyError, TypeError, ValueError, httpx.HTTPError) as error:
            raise RecruiterAISummaryOperationError() from error
