from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.automation_auth import require_internal_automation
from app.core.config import Settings, get_settings
from app.core.authorization import CurrentUser, require_admin, require_recruiter
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.recruiter_ai_summary import AIContextResponse, AIResultIngestionRequest, RecruiterAISummaryResponse
from app.services.ai_summary_actions import AdminAISummaryService, AISummaryActionsService, AISummaryRetryConflictError, AISummaryRetryOperationError
from app.services.ai_processing import AIProcessingOperationError, AIProcessingService, build_ai_processing_service
from app.services.recruiter_ai_summary import RecruiterAISummaryNotFoundError, RecruiterAISummaryOperationError

recruiter_router = APIRouter(prefix="/recruiter/applications", tags=["recruiter AI summaries"])
admin_router = APIRouter(prefix="/admin/applications", tags=["admin AI summaries"])
internal_router = APIRouter(prefix="/internal/ai-summaries", tags=["internal AI summaries"], dependencies=[Depends(require_internal_automation)])


def get_actions(client: SupabaseAdminClient = Depends(get_supabase_admin_client)) -> AISummaryActionsService:
    return AISummaryActionsService(client)


def get_admin_service(client: SupabaseAdminClient = Depends(get_supabase_admin_client)) -> AdminAISummaryService:
    return AdminAISummaryService(client)


def get_processing_service(client: SupabaseAdminClient = Depends(get_supabase_admin_client), settings: Settings = Depends(get_settings)) -> AIProcessingService:
    return build_ai_processing_service(client, settings)


@recruiter_router.post("/{application_id}/ai-summary/retry", status_code=status.HTTP_204_NO_CONTENT)
def recruiter_retry(application_id: UUID, user: CurrentUser = Depends(require_recruiter), service: AISummaryActionsService = Depends(get_actions)) -> None:
    _retry(service, user.user_id, application_id)


@admin_router.get("/{application_id}/ai-summary", response_model=RecruiterAISummaryResponse)
def admin_read(application_id: UUID, _: CurrentUser = Depends(require_admin), service: AdminAISummaryService = Depends(get_admin_service)) -> RecruiterAISummaryResponse:
    try:
        return service.get_summary(application_id)
    except RecruiterAISummaryNotFoundError as error:
        raise HTTPException(404, "Resource not found") from error
    except RecruiterAISummaryOperationError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI summary service is unavailable") from error


@admin_router.post("/{application_id}/ai-summary/retry", status_code=status.HTTP_204_NO_CONTENT)
def admin_retry(application_id: UUID, user: CurrentUser = Depends(require_admin), service: AISummaryActionsService = Depends(get_actions)) -> None:
    _retry(service, user.user_id, application_id)


@internal_router.post("/{application_id}/result", status_code=status.HTTP_204_NO_CONTENT)
def ingest_result(application_id: UUID, data: AIResultIngestionRequest, service: AISummaryActionsService = Depends(get_actions)) -> None:
    try:
        service.ingest(application_id, data)
    except AISummaryRetryConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "AI summary result cannot be saved") from error
    except AISummaryRetryOperationError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI summary service is unavailable") from error


@internal_router.post("/{application_id}/context", response_model=AIContextResponse)
def get_context(application_id: UUID, service: AIProcessingService = Depends(get_processing_service)) -> AIContextResponse:
    """Return the existing safe prompt to the authenticated automation worker only."""
    try:
        return service.prepare_context(application_id)
    except AIProcessingOperationError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI summary context is unavailable") from error


@internal_router.post("/{application_id}/process", status_code=status.HTTP_204_NO_CONTENT)
def process_summary(application_id: UUID, service: AIProcessingService = Depends(get_processing_service)) -> None:
    """Internal-automation-only entry point for the future claimed outbox work item."""
    try:
        service.process(application_id)
    except AIProcessingOperationError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI summary service is unavailable") from error


def _retry(service: AISummaryActionsService, actor_id: str, application_id: UUID) -> None:
    try:
        service.retry(actor_id, application_id)
    except AISummaryRetryConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "AI summary cannot be retried") from error
    except AISummaryRetryOperationError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI summary service is unavailable") from error
