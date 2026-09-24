from uuid import UUID

import httpx
from pydantic import ValidationError

from app.schemas.recruiter_notes import RecruiterNoteResponse


class RecruiterNotesNotFoundError(Exception):
    pass


class RecruiterNotesOperationError(Exception):
    pass


class RecruiterNotesService:
    def __init__(self, client):
        self.client = client

    def list_notes(self, recruiter_id: str, application_id: UUID) -> list[RecruiterNoteResponse]:
        try:
            application = self.client.recruiter_app(str(application_id))
            self.client.recruiter_job(recruiter_id, application["job_id"])
            rows = self.client.list_recruiter_notes(str(application_id))
            return [
                RecruiterNoteResponse.model_validate({
                    "id": row["id"],
                    "content": row["note"],
                    "created_at": row["created_at"],
                })
                for row in rows
            ]
        except LookupError as error:
            raise RecruiterNotesNotFoundError() from error
        except (KeyError, TypeError, ValueError, ValidationError, httpx.HTTPError) as error:
            raise RecruiterNotesOperationError() from error

    def create_note(self, recruiter_id: str, application_id: UUID, content: str) -> RecruiterNoteResponse:
        try:
            row = self.client.add_recruiter_note(recruiter_id, str(application_id), content)
            return RecruiterNoteResponse.model_validate({
                "id": row["id"],
                "content": row["note"],
                "created_at": row["created_at"],
            })
        except LookupError as error:
            raise RecruiterNotesNotFoundError() from error
        except (KeyError, TypeError, ValueError, ValidationError, httpx.HTTPError) as error:
            raise RecruiterNotesOperationError() from error
