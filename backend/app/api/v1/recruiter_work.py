from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,status
from app.core.authorization import CurrentUser,require_recruiter
from app.integrations.supabase_admin import SupabaseAdminClient,get_supabase_admin_client
from app.schemas.recruiter_work import AppDetail,AppList,CVAccess,Job
from app.services.recruiter_work import Service,NotFound,Operation
router=APIRouter(prefix='/recruiter',tags=['recruiter assigned work'])
def get_service(c:SupabaseAdminClient=Depends(get_supabase_admin_client)):return Service(c)
def call(f):
 try:return f()
 except NotFound as e:raise HTTPException(404,'Resource not found') from e
 except Operation as e:raise HTTPException(503,'Recruiter service is unavailable') from e
@router.get('/jobs',response_model=list[Job])
def jobs(u:CurrentUser=Depends(require_recruiter),s:Service=Depends(get_service)):return call(lambda:s.jobs(u.user_id))
@router.get('/jobs/{job_id}',response_model=Job)
def job(job_id:UUID,u:CurrentUser=Depends(require_recruiter),s:Service=Depends(get_service)):return call(lambda:s.job(u.user_id,job_id))
@router.get('/jobs/{job_id}/applications',response_model=list[AppList])
def apps(job_id:UUID,u:CurrentUser=Depends(require_recruiter),s:Service=Depends(get_service)):return call(lambda:s.apps(u.user_id,job_id))
@router.get('/applications/{application_id}',response_model=AppDetail)
def app(application_id:UUID,u:CurrentUser=Depends(require_recruiter),s:Service=Depends(get_service)):return call(lambda:s.app(u.user_id,application_id))
@router.get('/applications/{application_id}/cv/access',response_model=CVAccess)
def cv(application_id:UUID,u:CurrentUser=Depends(require_recruiter),s:Service=Depends(get_service)):return call(lambda:s.cv(u.user_id,application_id))
