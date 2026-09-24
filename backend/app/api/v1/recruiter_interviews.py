from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,status
from app.core.authorization import CurrentUser,require_recruiter
from app.integrations.supabase_admin import SupabaseAdminClient,get_supabase_admin_client
from app.schemas.recruiter_interviews import RecruiterInterviewScheduleRequest,RecruiterInterviewScheduleResponse
from app.services.recruiter_interviews import Service,NotFound,Conflict,Operation
router=APIRouter(prefix='/recruiter/applications',tags=['recruiter interviews'])
def get_service(c:SupabaseAdminClient=Depends(get_supabase_admin_client)):return Service(c)
@router.post('/{application_id}/interview',response_model=RecruiterInterviewScheduleResponse)
def schedule(application_id:UUID,data:RecruiterInterviewScheduleRequest,u:CurrentUser=Depends(require_recruiter),s:Service=Depends(get_service)):
 try:return s.schedule(u.user_id,application_id,data)
 except NotFound as e:raise HTTPException(404,'Resource not found') from e
 except Conflict as e:raise HTTPException(status.HTTP_409_CONFLICT,'Interview cannot be scheduled.') from e
 except Operation as e:raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,'Recruiter interview service is unavailable') from e
