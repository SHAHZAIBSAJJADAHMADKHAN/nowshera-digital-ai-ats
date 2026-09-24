from uuid import UUID

import httpx
from pydantic import ValidationError

from app.schemas.candidate_application_tracking import (
    CandidateApplicationDetailResponse,
    CandidateApplicationListResponse,
)


class CandidateApplicationTrackingNotFoundError(Exception):
    pass


class CandidateApplicationTrackingOperationError(Exception):
    pass


class CandidateApplicationTrackingService:
    def __init__(self, client):
        self.client = client

    def list_applications(self, candidate_id: UUID | str) -> list[CandidateApplicationListResponse]:
        try:
            records = self.client.list_candidate_applications(str(candidate_id))
            if not isinstance(records, list):
                raise ValueError("Application listing returned a non-list result")
            return [CandidateApplicationListResponse.model_validate(self._normalize(record)) for record in records]
        except (KeyError, TypeError, ValueError, ValidationError, httpx.HTTPError) as error:
            raise CandidateApplicationTrackingOperationError() from error

    def get_application(self, candidate_id: UUID | str, application_id: UUID | str) -> CandidateApplicationDetailResponse:
        try:
            record = self.client.get_candidate_application(str(candidate_id), str(application_id))
            normalized = self._normalize(record)
            normalized["stage_history"] = sorted(normalized.get("stage_history", []), key=lambda item: item["changed_at"])
            interview = normalized.get("interview")
            normalized["interview"] = interview[0] if isinstance(interview, list) and interview else None if isinstance(interview, list) else interview
            return CandidateApplicationDetailResponse.model_validate(normalized)
        except LookupError as error:
            raise CandidateApplicationTrackingNotFoundError() from error
        except (KeyError, TypeError, ValueError, ValidationError, httpx.HTTPError) as error:
            raise CandidateApplicationTrackingOperationError() from error

    @staticmethod
    def _normalize(record: object) -> dict:
        if not isinstance(record, dict):
            raise ValueError("Application record is invalid")
        result = dict(record)
        result["job"] = result.pop("jobs")
        result["cv"] = result.pop("candidate_cvs")
        result["stage_history"] = result.pop("application_stage_history", result.get("stage_history", []))
        result["interview"] = result.pop("interviews", result.get("interview"))
        return result
