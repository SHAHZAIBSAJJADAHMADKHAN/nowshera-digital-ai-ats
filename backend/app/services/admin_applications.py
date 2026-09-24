from uuid import UUID

import httpx
from pydantic import ValidationError

from app.schemas.admin_applications import AdminApplicationCVAccess, AdminApplicationDetail, AdminApplicationListItem
from app.schemas.recruiter_ai_summary import RecruiterAISummaryResponse
from app.services.recruiter_ai_summary import RecruiterAISummaryService


class AdminApplicationNotFoundError(Exception):
    pass


class AdminApplicationOperationError(Exception):
    pass


class AdminApplicationsService:
    def __init__(self, client):
        self.client = client

    def list_applications(self) -> list[AdminApplicationListItem]:
        try:
            return [AdminApplicationListItem.model_validate(self._normalize(row)) for row in self.client.admin_applications()]
        except (KeyError, TypeError, ValueError, ValidationError, httpx.HTTPError) as error:
            raise AdminApplicationOperationError("Admin applications are unavailable") from error

    def get_application(self, application_id: UUID) -> AdminApplicationDetail:
        try:
            row = self._normalize(self.client.admin_application(str(application_id)))
            history = row.pop("application_stage_history", [])
            row["stage_history"] = sorted(history, key=lambda item: item["changed_at"])
            interviews = row.pop("interviews", None)
            row["interview"] = interviews[0] if isinstance(interviews, list) and interviews else interviews if isinstance(interviews, dict) else None
            summaries = row.pop("ai_summaries", None)
            summary = summaries[0] if isinstance(summaries, list) and summaries else summaries if isinstance(summaries, dict) else None
            row["ai_summary"] = self._summary(application_id, summary)
            return AdminApplicationDetail.model_validate(row)
        except LookupError as error:
            raise AdminApplicationNotFoundError() from error
        except (KeyError, TypeError, ValueError, ValidationError, httpx.HTTPError) as error:
            raise AdminApplicationOperationError("Admin application is unavailable") from error

    def cv_access(self, application_id: UUID) -> AdminApplicationCVAccess:
        try:
            row = self.client.admin_application_cv(str(application_id))
            return AdminApplicationCVAccess(
                url=self.client.sign_candidate_cv(row["storage_path"], 60),
                expires_in=60,
                application_id=application_id,
                cv_id=row["cv_id"],
                original_filename=row["original_filename"],
            )
        except LookupError as error:
            raise AdminApplicationNotFoundError() from error
        except (KeyError, TypeError, ValueError, httpx.HTTPError) as error:
            raise AdminApplicationOperationError("Admin application CV is unavailable") from error

    @staticmethod
    def _normalize(row):
        row = dict(row)
        row["candidate"] = row.pop("profiles")
        row["job"] = row.pop("jobs")
        row["cv"] = row.pop("candidate_cvs")
        return row

    def _summary(self, application_id: UUID, row) -> RecruiterAISummaryResponse | None:
        if not row:
            return None
        return RecruiterAISummaryService(self.client)._result(application_id, row)
