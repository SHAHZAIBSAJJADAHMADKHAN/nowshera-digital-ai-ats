from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authorization import CurrentUser, require_recruiter
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.recruiter_ai_summary import RecruiterAISummaryResponse
from app.services.recruiter_ai_summary import RecruiterAISummaryNotFoundError, RecruiterAISummaryOperationError, RecruiterAISummaryService

router = APIRouter(prefix="/recruiter/applications", tags=["recruiter AI summaries"])
def get_service(client: SupabaseAdminClient = Depends(get_supabase_admin_client)): return RecruiterAISummaryService(client)

@router.get("/{application_id}/ai-summary", response_model=RecruiterAISummaryResponse)
def get_ai_summary(application_id: UUID, user: CurrentUser = Depends(require_recruiter), service: RecruiterAISummaryService = Depends(get_service)):
    try: return service.get_summary(user.user_id, application_id)
    except RecruiterAISummaryNotFoundError as error: raise HTTPException(404, "Resource not found") from error
    except RecruiterAISummaryOperationError as error: raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Recruiter AI summary service is unavailable") from error
