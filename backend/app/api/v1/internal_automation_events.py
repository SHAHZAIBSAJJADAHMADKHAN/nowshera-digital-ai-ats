from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.automation_auth import require_internal_automation
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.automation_events import (
    AIEventClaimRequest,
    AIEventClaimResponse,
    AutomationEventClaimRequest,
    AutomationEventClaimResponse,
    AutomationEventDeliveryResponse,
    AutomationEventFailureRequest,
)
from app.services.automation_events import (
    AutomationEventConflictError,
    AutomationEventOperationError,
    AutomationEventService,
)

router = APIRouter(
    prefix="/internal/automation-events",
    tags=["internal automation"],
    dependencies=[Depends(require_internal_automation)],
)


def get_service(
    client: SupabaseAdminClient = Depends(get_supabase_admin_client),
) -> AutomationEventService:
    return AutomationEventService(client)


def get_ai_service(
    client: SupabaseAdminClient = Depends(get_supabase_admin_client),
) -> AutomationEventService:
    return AutomationEventService(client)


@router.post("/ai/claim", response_model=AIEventClaimResponse)
def claim_ai_events(
    data: AIEventClaimRequest,
    service: AutomationEventService = Depends(get_ai_service),
) -> AIEventClaimResponse:
    try:
        return service.claim_ai_summary_events(data.limit)
    except AutomationEventConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "AI automation events cannot be claimed") from error
    except AutomationEventOperationError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI automation event service is unavailable") from error


@router.post("/claim", response_model=AutomationEventClaimResponse)
def claim_events(
    data: AutomationEventClaimRequest,
    service: AutomationEventService = Depends(get_service),
) -> AutomationEventClaimResponse:
    try:
        return service.claim(data.event_types, data.limit)
    except AutomationEventConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "Automation events cannot be claimed") from error
    except AutomationEventOperationError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Automation event service is unavailable") from error


@router.post("/{event_id}/complete", response_model=AutomationEventDeliveryResponse)
def complete_event(
    event_id: UUID,
    service: AutomationEventService = Depends(get_service),
) -> AutomationEventDeliveryResponse:
    try:
        return service.complete(event_id)
    except AutomationEventConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "Automation event cannot be completed") from error
    except AutomationEventOperationError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Automation event service is unavailable") from error


@router.post("/{event_id}/fail", response_model=AutomationEventDeliveryResponse)
def fail_event(
    event_id: UUID,
    data: AutomationEventFailureRequest,
    service: AutomationEventService = Depends(get_service),
) -> AutomationEventDeliveryResponse:
    try:
        return service.fail(event_id, data.error)
    except AutomationEventConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "Automation event cannot be failed") from error
    except AutomationEventOperationError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Automation event service is unavailable") from error
