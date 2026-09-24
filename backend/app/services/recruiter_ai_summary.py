from uuid import UUID

import httpx
from pydantic import ValidationError

from app.schemas.recruiter_ai_summary import RecruiterAISummaryResponse


class RecruiterAISummaryNotFoundError(Exception): pass
class RecruiterAISummaryOperationError(Exception): pass


class RecruiterAISummaryService:
    def __init__(self, client): self.client = client

    def get_summary(self, recruiter_id: str, application_id: UUID) -> RecruiterAISummaryResponse:
        try:
            application = self.client.recruiter_app(str(application_id))
            self.client.recruiter_job(recruiter_id, application["job_id"])
            row = self.client.recruiter_ai_summary(str(application_id))
            if row is None:
                return RecruiterAISummaryResponse(application_id=application_id, status="unavailable", summary_available=False)
            return self._result(application_id, row)
        except LookupError as error: raise RecruiterAISummaryNotFoundError() from error
        except (KeyError, TypeError, ValueError, ValidationError, httpx.HTTPError) as error: raise RecruiterAISummaryOperationError() from error

    def _result(self, application_id: UUID, row: dict) -> RecruiterAISummaryResponse:
        status = row["status"]
        if status != "completed":
            return RecruiterAISummaryResponse(application_id=application_id, status=status, summary_available=False)
        result = RecruiterAISummaryResponse(
                application_id=application_id, status=status, summary_available=True,
                profile_bullets=row["profile_summary"], requirements_found=row["requirements_found"],
                requirements_not_found=row["requirements_not_found"], interview_questions=row["interview_questions"],
        )
        if not 3 <= len(result.profile_bullets or []) <= 5 or len(result.interview_questions or []) != 3:
            raise ValueError("Invalid completed summary shape")
        return result
