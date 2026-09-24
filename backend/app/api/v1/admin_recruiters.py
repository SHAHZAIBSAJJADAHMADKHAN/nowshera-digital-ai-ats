from fastapi import APIRouter, Depends, Query
from app.core.authorization import CurrentUser, require_admin
from app.schemas.admin_recruiters import RecruiterCreate
from app.services.admin_recruiters import AdminRecruiterService
from app.integrations.supabase_admin import get_supabase_admin_client

router=APIRouter(prefix='/admin/recruiters',tags=['admin recruiters'])
def get_service(client=Depends(get_supabase_admin_client)): return AdminRecruiterService(client)
@router.get('')
def list_recruiters(_:CurrentUser=Depends(require_admin),service:AdminRecruiterService=Depends(get_service),limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0)): return service.list(limit,offset)
@router.post('',status_code=201)
def create_recruiter(data:RecruiterCreate,admin:CurrentUser=Depends(require_admin),service:AdminRecruiterService=Depends(get_service)): return service.create(admin.user_id,data)
@router.post('/{recruiter_id}/deactivate')
def deactivate_recruiter(recruiter_id:str,admin:CurrentUser=Depends(require_admin),service:AdminRecruiterService=Depends(get_service)): return service.deactivate(admin.user_id,recruiter_id)
