from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authorization import CurrentUser, require_recruiter
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.recruiter_pipeline import RecruiterApplicationTransitionRequest, RecruiterApplicationTransitionResponse
from app.services.recruiter_pipeline import RecruiterPipelineConflictError, RecruiterPipelineNotFoundError, RecruiterPipelineOperationError, RecruiterPipelineService

router = APIRouter(prefix='/recruiter/applications', tags=['recruiter pipeline'])

def get_service(client: SupabaseAdminClient = Depends(get_supabase_admin_client)) -> RecruiterPipelineService:
    return RecruiterPipelineService(client)

@router.patch('/{application_id}/stage', response_model=RecruiterApplicationTransitionResponse)
def transition_application_stage(application_id: UUID, data: RecruiterApplicationTransitionRequest, user: CurrentUser = Depends(require_recruiter), service: RecruiterPipelineService = Depends(get_service)):
    try:
        return service.transition(user.user_id, application_id, data.stage)
    except RecruiterPipelineNotFoundError as error:
        raise HTTPException(404, 'Resource not found') from error
    except RecruiterPipelineConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Application cannot transition to that stage.') from error
    except RecruiterPipelineOperationError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, 'Recruiter pipeline service is unavailable') from error
