from pathlib import Path
from uuid import UUID, uuid4

import httpx
from pydantic import ValidationError

from app.schemas.candidate_cvs import CandidateCVAccessResponse, CandidateCVResponse
from app.services.candidate_profile import CandidateProfileNotFoundError, CandidateProfileOperationError

MAX_CV_BYTES = 2_097_152
CV_ACCESS_TTL_SECONDS = 60


class CandidateCVValidationError(Exception):
    """Raised for safe, client-correctable CV upload validation failures."""


class CandidateCVService:
    def __init__(self, client):
        self.client = client

    def list_cvs(self, candidate_id: UUID | str) -> list[CandidateCVResponse]:
        try:
            records = self.client.list_candidate_cvs(str(candidate_id))
            if not isinstance(records, list):
                raise ValueError("Candidate CV listing returned a non-list result")
            return [CandidateCVResponse.model_validate(record) for record in records]
        except (KeyError, TypeError, ValueError, ValidationError, httpx.HTTPError) as error:
            raise CandidateProfileOperationError("Candidate CV metadata is unavailable") from error

    def upload_cv(self, candidate_id: UUID | str, filename: str | None, content_type: str | None, content: bytes) -> CandidateCVResponse:
        if not content:
            raise CandidateCVValidationError("CV file must not be empty")
        if len(content) > MAX_CV_BYTES:
            raise CandidateCVValidationError("CV file exceeds the 2 MiB limit")
        if content_type != "application/pdf":
            raise CandidateCVValidationError("CV file must be a PDF")
        if not content.startswith(b"%PDF-"):
            raise CandidateCVValidationError("CV file must contain PDF data")
        safe_name = Path(filename or "cv.pdf").name or "cv.pdf"
        object_path = f"candidates/{candidate_id}/{uuid4()}.pdf"
        try:
            self.client.upload_candidate_cv(object_path, content)
        except (ValueError, httpx.HTTPError) as error:
            raise CandidateProfileOperationError("Candidate CV upload is unavailable") from error
        try:
            record = self.client.register_candidate_cv(str(candidate_id), object_path, safe_name, len(content))
            return CandidateCVResponse.model_validate(record)
        except (KeyError, TypeError, ValueError, ValidationError, httpx.HTTPError) as error:
            try:
                self.client.delete_candidate_cv_object(object_path)
            except (ValueError, httpx.HTTPError):
                pass
            raise CandidateProfileOperationError("Candidate CV upload is unavailable") from error

    def get_cv_access(self, candidate_id: UUID | str, cv_id: UUID | str) -> CandidateCVAccessResponse:
        try:
            record = self.client.get_candidate_cv(str(candidate_id), str(cv_id))
        except LookupError as error:
            raise CandidateProfileNotFoundError("Candidate CV not found") from error
        except (KeyError, TypeError, ValueError, httpx.HTTPError) as error:
            raise CandidateProfileOperationError("Candidate CV access is unavailable") from error
        try:
            return CandidateCVAccessResponse(url=self.client.sign_candidate_cv(record['storage_path'], CV_ACCESS_TTL_SECONDS), expires_in=CV_ACCESS_TTL_SECONDS, cv_id=record['id'], original_filename=record['original_filename'])
        except (KeyError, TypeError, ValueError, httpx.HTTPError) as error:
            raise CandidateProfileOperationError("Candidate CV access is unavailable") from error
