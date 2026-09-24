from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,status
from app.core.authorization import CurrentUser,require_candidate
from app.integrations.supabase_admin import SupabaseAdminClient,get_supabase_admin_client
from app.schemas.candidate_jobs import CandidateJobDetailResponse,CandidateJobListResponse
from app.services.candidate_jobs import CandidateJobNotFoundError,CandidateJobOperationError,CandidateJobService
router=APIRouter(prefix='/candidate/jobs',tags=['candidate jobs'])
def get_service(client:SupabaseAdminClient=Depends(get_supabase_admin_client)): return CandidateJobService(client)
@router.get('',response_model=list[CandidateJobListResponse])
def list_jobs(_:CurrentUser=Depends(require_candidate),service:CandidateJobService=Depends(get_service)):
    try:return service.list_jobs()
    except CandidateJobOperationError as e: raise HTTPException(503,'Candidate job discovery is unavailable') from e
@router.get('/{job_id}',response_model=CandidateJobDetailResponse)
def get_job(job_id:UUID,_:CurrentUser=Depends(require_candidate),service:CandidateJobService=Depends(get_service)):
    try:return service.get_job(job_id)
    except CandidateJobNotFoundError as e: raise HTTPException(404,'Job not found') from e
    except CandidateJobOperationError as e: raise HTTPException(503,'Candidate job discovery is unavailable') from e
