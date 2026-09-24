from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.authorization import CurrentUser, require_recruiter
from app.integrations.supabase_admin import SupabaseAdminClient, get_supabase_admin_client
from app.schemas.recruiter_hiring import RecruiterHireResponse
from app.services.recruiter_hiring import RecruiterHiringConflictError, RecruiterHiringNotFoundError, RecruiterHiringOperationError, RecruiterHiringService

router=APIRouter(prefix='/recruiter/applications',tags=['recruiter hiring'])
def get_service(client: SupabaseAdminClient=Depends(get_supabase_admin_client)): return RecruiterHiringService(client)

@router.post('/{application_id}/hire',response_model=RecruiterHireResponse)
def hire_application(application_id: UUID,user: CurrentUser=Depends(require_recruiter),service: RecruiterHiringService=Depends(get_service)):
    try: return service.hire(user.user_id,application_id)
    except RecruiterHiringNotFoundError as error: raise HTTPException(404,'Resource not found') from error
    except RecruiterHiringConflictError as error: raise HTTPException(status.HTTP_409_CONFLICT,'Application cannot be hired.') from error
    except RecruiterHiringOperationError as error: raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,'Recruiter hiring service is unavailable') from error
