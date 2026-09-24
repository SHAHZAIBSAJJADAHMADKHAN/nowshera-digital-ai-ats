from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authorization import CurrentUser, require_recruiter
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.recruiter_notes import RecruiterNoteCreate, RecruiterNoteResponse
from app.services.recruiter_notes import (
    RecruiterNotesNotFoundError,
    RecruiterNotesOperationError,
    RecruiterNotesService,
)


router = APIRouter(prefix="/recruiter/applications", tags=["recruiter notes"])
T = TypeVar("T")


def get_service(client: SupabaseAdminClient = Depends(get_supabase_admin_client)) -> RecruiterNotesService:
    return RecruiterNotesService(client)


def _call(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except RecruiterNotesNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found") from error
    except RecruiterNotesOperationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Recruiter notes service is unavailable") from error


@router.get("/{application_id}/notes", response_model=list[RecruiterNoteResponse])
def list_notes(
    application_id: UUID,
    current_user: CurrentUser = Depends(require_recruiter),
    service: RecruiterNotesService = Depends(get_service),
) -> list[RecruiterNoteResponse]:
    return _call(lambda: service.list_notes(current_user.user_id, application_id))


@router.post("/{application_id}/notes", response_model=RecruiterNoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    application_id: UUID,
    payload: RecruiterNoteCreate,
    current_user: CurrentUser = Depends(require_recruiter),
    service: RecruiterNotesService = Depends(get_service),
) -> RecruiterNoteResponse:
    return _call(lambda: service.create_note(current_user.user_id, application_id, payload.content))
