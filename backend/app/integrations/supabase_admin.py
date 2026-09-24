import httpx
from datetime import datetime, timezone
from fastapi import Depends

from app.core.config import Settings, get_settings

class SupabaseAdminClient:
    def __init__(self,url:str,secret:str): self.url=url.rstrip('/'); self.headers={'apikey':secret,'Authorization':f'Bearer {secret}'}
    def _request(self,method,path,**kwargs):
        response=httpx.request(method,f'{self.url}{path}',headers=self.headers,timeout=10,**kwargs)
        if response.status_code in (400,409,422): raise ValueError('conflict')
        response.raise_for_status(); return response
    def list_recruiters(self,limit,offset):
        return self._request('GET','/rest/v1/profiles',params={'role':'eq.recruiter','select':'id,full_name,email,phone,role,is_active,created_at','limit':limit,'offset':offset,'order':'created_at.desc'}).json()
    def invite_recruiter(self,email): return self._request('POST','/auth/v1/invite',params={'redirect_to':'http://localhost:5173/set-password'},json={'email':email}).json()
    def provision(self,admin_id,recruiter_id,name,email,phone): self._request('POST','/rest/v1/rpc/provision_recruiter_profile',json={'p_admin_id':admin_id,'p_recruiter_id':recruiter_id,'p_full_name':name,'p_email':email,'p_phone':phone})
    def deactivate(self,admin_id,recruiter_id): return self._request('POST','/rest/v1/rpc/deactivate_recruiter',json={'p_admin_id':admin_id,'p_recruiter_id':recruiter_id}).json()
    def reactivate(self,admin_id,recruiter_id): return self._request('POST','/rest/v1/rpc/reactivate_recruiter',json={'p_admin_id':admin_id,'p_recruiter_id':recruiter_id}).json()
    def update_recruiter(self,admin_id,recruiter_id,full_name,phone): self._request('POST','/rest/v1/rpc/update_recruiter_profile',json={'p_admin_id':admin_id,'p_recruiter_id':recruiter_id,'p_full_name':full_name,'p_phone':phone})
    def get_recruiter(self,recruiter_id):
        rows=self._request('GET','/rest/v1/profiles',params={'id':f'eq.{recruiter_id}','select':'id,full_name,email,phone,role,is_active,created_at'}).json()
        if not rows: raise LookupError('Recruiter not found')
        return rows[0]
    def delete_auth_user(self,user_id): self._request('DELETE',f'/auth/v1/admin/users/{user_id}')
    def list_jobs(self,limit,offset):
        return self._request('GET','/rest/v1/jobs',params={'select':'id,title,department,location,job_type,description,requirements,application_deadline,openings,status,created_by,closed_at,created_at,updated_at','limit':limit,'offset':offset,'order':'created_at.desc'}).json()
    def get_job(self,job_id):
        jobs=self._request('GET','/rest/v1/jobs',params={'id':f'eq.{job_id}','select':'id,title,department,location,job_type,description,requirements,application_deadline,openings,status,created_by,closed_at,created_at,updated_at'}).json()
        if not jobs: raise LookupError('Job not found')
        return jobs[0]
    def create_draft_job(self,admin_id,data):
        return self._request('POST','/rest/v1/rpc/create_draft_job',json={'p_admin_id':admin_id,'p_title':data['title'],'p_department':data['department'],'p_location':data['location'],'p_job_type':data['job_type'],'p_description':data['description'],'p_requirements':data['requirements'],'p_deadline':data['application_deadline'],'p_openings':data['openings']}).json()
    def update_draft_job(self,admin_id,job_id,data):
        self._request('POST','/rest/v1/rpc/update_draft_job',json={'p_admin_id':admin_id,'p_job_id':job_id,'p_title':data['title'],'p_department':data['department'],'p_location':data['location'],'p_job_type':data['job_type'],'p_description':data['description'],'p_requirements':data['requirements'],'p_deadline':data['application_deadline'],'p_openings':data['openings']})
    def open_job_rpc(self,admin_id,job_id):
        self._request('POST','/rest/v1/rpc/open_job',json={'p_admin_id':admin_id,'p_job_id':job_id})
    def close_job_rpc(self,admin_id,job_id):
        return self._request('POST','/rest/v1/rpc/close_job',json={'p_admin_id':admin_id,'p_job_id':job_id}).json()
    def get_admin_job_dashboard(self,admin_id):
        return self._request('POST','/rest/v1/rpc/get_admin_job_dashboard',json={'p_admin_id':admin_id}).json()
    def list_assigned_recruiters(self,job_id):
        return self._request('GET','/rest/v1/job_recruiters',params={'job_id':f'eq.{job_id}','select':'recruiter_id,assigned_at,profiles!job_recruiters_recruiter_id_fkey(id,full_name,email,is_active)','order':'assigned_at.asc'}).json()
    def get_assignment_recruiter(self,recruiter_id):
        recruiters=self._request('GET','/rest/v1/profiles',params={'id':f'eq.{recruiter_id}','select':'id,full_name,email,role,is_active'}).json()
        if not recruiters: raise LookupError('Recruiter not found')
        return recruiters[0]
    def get_candidate_profile(self,candidate_id):
        profiles=self._request('GET','/rest/v1/profiles',params={'id':f'eq.{candidate_id}','role':'eq.candidate','select':'id,full_name,email,phone,created_at,updated_at'}).json()
        if not profiles: raise LookupError('Candidate profile not found')
        return profiles[0]
    def get_profile_identity(self,user_id):
        profiles=self._request('GET','/rest/v1/profiles',params={'id':f'eq.{user_id}','select':'id,role'}).json()
        return profiles[0] if profiles else None
    def get_auth_user(self,user_id):
        return self._request('GET',f'/auth/v1/admin/users/{user_id}').json()
    def bootstrap_candidate_profile(self,candidate_id,full_name,email):
        self._request('POST','/rest/v1/rpc/bootstrap_candidate_profile',json={'p_candidate_id':candidate_id,'p_full_name':full_name,'p_email':email})
    def update_candidate_profile(self,candidate_id,data):
        response=self._request('PATCH','/rest/v1/profiles',params={'id':f'eq.{candidate_id}','role':'eq.candidate'},json=data)
        if response.status_code != 204: raise ValueError('Candidate profile update failed')
    def list_candidate_cvs(self,candidate_id):
        return self._request('GET','/rest/v1/candidate_cvs',params={'candidate_id':f'eq.{candidate_id}','select':'id,original_filename,mime_type,file_size_bytes,uploaded_at','order':'uploaded_at.desc'}).json()
    def list_candidate_jobs(self):
        return self._request('GET','/rest/v1/jobs',params={'status':'eq.open','application_deadline':'gt.'+datetime.now(timezone.utc).isoformat(),'select':'id,title,department,location,job_type,application_deadline,openings','order':'application_deadline.asc,id.asc','limit':100}).json()
    def get_candidate_job(self,job_id):
        rows=self._request('GET','/rest/v1/jobs',params={'id':f'eq.{job_id}','status':'eq.open','application_deadline':'gt.'+datetime.now(timezone.utc).isoformat(),'select':'id,title,department,location,job_type,description,requirements,application_deadline,openings,created_at'}).json()
        if not rows: raise LookupError('Job not found')
        return rows[0]
    def submit_candidate_application(self,candidate_id,job_id,cv_id):
        response=httpx.post(f'{self.url}/rest/v1/rpc/submit_application',headers=self.headers,json={'p_candidate_id':candidate_id,'p_job_id':job_id,'p_cv_id':cv_id},timeout=10)
        if response.status_code >= 400:
            try: code=response.json().get('code')
            except (TypeError, ValueError): code=None
            from app.services.candidate_applications import CandidateApplicationConflictError, CandidateApplicationCVError, CandidateApplicationUnavailableError
            if code == '23505': raise CandidateApplicationConflictError()
            if code == '23514': raise CandidateApplicationUnavailableError()
            if code == '23503': raise CandidateApplicationCVError()
            response.raise_for_status()
        application_id=response.json()
        if not isinstance(application_id,str): raise ValueError('Invalid application RPC result')
        rows=self._request('GET','/rest/v1/applications',params={'id':f'eq.{application_id}','candidate_id':f'eq.{candidate_id}','select':'id,job_id,cv_id,stage,applied_at'}).json()
        if not rows: raise ValueError('Application result unavailable')
        return rows[0]
    def list_candidate_applications(self,candidate_id):
        return self._request('GET','/rest/v1/applications',params={'candidate_id':f'eq.{candidate_id}','select':'id,stage,applied_at,jobs!applications_job_id_fkey(id,title,department,location,job_type,application_deadline),candidate_cvs!applications_cv_belongs_to_candidate_fkey(id,original_filename,uploaded_at)','order':'applied_at.desc,id.desc','limit':100}).json()
    def get_candidate_application(self,candidate_id,application_id):
        rows=self._request('GET','/rest/v1/applications',params={'id':f'eq.{application_id}','candidate_id':f'eq.{candidate_id}','select':'id,stage,applied_at,jobs!applications_job_id_fkey(id,title,department,location,job_type,description,requirements,application_deadline),candidate_cvs!applications_cv_belongs_to_candidate_fkey(id,original_filename,uploaded_at),application_stage_history(stage:to_stage,changed_at),interviews(starts_at,ends_at,location,meeting_link)','application_stage_history.order':'changed_at.asc'}).json()
        if not rows: raise LookupError('Application not found')
        return rows[0]
    def withdraw_candidate_application(self,candidate_id,application_id):
        response=httpx.post(f'{self.url}/rest/v1/rpc/withdraw_application',headers=self.headers,json={'p_candidate_id':candidate_id,'p_application_id':application_id},timeout=10)
        if response.status_code >= 400:
            try: code=response.json().get('code')
            except (TypeError, ValueError): code=None
            from app.services.candidate_application_withdrawal import CandidateWithdrawalConflictError, CandidateWithdrawalNotFoundError
            if code == '23503': raise CandidateWithdrawalNotFoundError()
            if code == '23514': raise CandidateWithdrawalConflictError()
            response.raise_for_status()
        rows=self._request('GET','/rest/v1/applications',params={'id':f'eq.{application_id}','candidate_id':f'eq.{candidate_id}','select':'id,stage,withdrawn_at'}).json()
        if not rows: raise ValueError('Withdrawal result unavailable')
        return rows[0]
    def recruiter_jobs(self,r):
        rows=self._request('GET','/rest/v1/job_recruiters',params={'recruiter_id':f'eq.{r}','select':'jobs(id,title,department,location,job_type,description,requirements,application_deadline,openings,status,created_at,closed_at)','order':'assigned_at.desc','limit':100}).json(); return [x['jobs'] for x in rows]
    def recruiter_job(self,r,j):
        rows=self._request('GET','/rest/v1/job_recruiters',params={'recruiter_id':f'eq.{r}','job_id':f'eq.{j}','select':'jobs(id,title,department,location,job_type,description,requirements,application_deadline,openings,status,created_at,closed_at)'}).json()
        if not rows:raise LookupError('Resource not found')
        return rows[0]['jobs']
    def recruiter_apps(self,j):
        return self._request('GET','/rest/v1/applications',params={'job_id':f'eq.{j}','select':'id,job_id,stage,applied_at,profiles!applications_candidate_id_fkey(full_name,email,phone),candidate_cvs!applications_cv_belongs_to_candidate_fkey(id,original_filename,uploaded_at)','order':'applied_at.desc,id.desc','limit':100}).json()
    def recruiter_app(self,a):
        rows=self._request('GET','/rest/v1/applications',params={'id':f'eq.{a}','select':'id,job_id,stage,applied_at,profiles!applications_candidate_id_fkey(full_name,email,phone),candidate_cvs!applications_cv_belongs_to_candidate_fkey(id,original_filename,uploaded_at),application_stage_history(stage:to_stage,changed_at),interviews(id,starts_at,ends_at,location,meeting_link)'}).json()
        if not rows:raise LookupError('Resource not found')
        return rows[0]
    def recruiter_app_cv(self,a):
        rows=self._request('GET','/rest/v1/applications',params={'id':f'eq.{a}','select':'job_id,cv_id,candidate_cvs!applications_cv_belongs_to_candidate_fkey(original_filename,storage_path)'}).json()
        if not rows:raise LookupError('Resource not found')
        x=rows[0]; x.update(x.pop('candidate_cvs')); return x
    def admin_applications(self):
        return self._request('GET','/rest/v1/applications',params={'select':'id,stage,applied_at,profiles!applications_candidate_id_fkey(id,full_name,email,phone),jobs!applications_job_id_fkey(id,title,department,location,job_type),candidate_cvs!applications_cv_belongs_to_candidate_fkey(id,original_filename,uploaded_at)','order':'applied_at.desc,id.desc','limit':500}).json()
    def admin_application(self,a):
        rows=self._request('GET','/rest/v1/applications',params={'id':f'eq.{a}','select':'id,stage,applied_at,profiles!applications_candidate_id_fkey(id,full_name,email,phone),jobs!applications_job_id_fkey(id,title,department,location,job_type,description,requirements,application_deadline),candidate_cvs!applications_cv_belongs_to_candidate_fkey(id,original_filename,uploaded_at),application_stage_history(stage:to_stage,changed_at),interviews(id,starts_at,ends_at,location,meeting_link),ai_summaries(application_id,status,profile_summary,requirements_found,requirements_not_found,interview_questions)','application_stage_history.order':'changed_at.asc'}).json()
        if not rows:raise LookupError('Application not found')
        return rows[0]
    def admin_application_cv(self,a):
        rows=self._request('GET','/rest/v1/applications',params={'id':f'eq.{a}','select':'cv_id,candidate_cvs!applications_cv_belongs_to_candidate_fkey(original_filename,storage_path)'}).json()
        if not rows:raise LookupError('Application not found')
        x=rows[0]; x.update(x.pop('candidate_cvs')); return x
    def upload_candidate_cv(self,path,content):
        response=httpx.post(f'{self.url}/storage/v1/object/candidate-cvs/{path}',headers={**self.headers,'Content-Type':'application/pdf','x-upsert':'false'},content=content,timeout=20)
        response.raise_for_status()
    def delete_candidate_cv_object(self,path):
        self._request('DELETE','/storage/v1/object/candidate-cvs/'+path)
    def register_candidate_cv(self,candidate_id,path,filename,size):
        response=httpx.post(f'{self.url}/rest/v1/candidate_cvs',headers={**self.headers,'Prefer':'return=representation'},json={'candidate_id':candidate_id,'storage_path':path,'original_filename':filename,'mime_type':'application/pdf','file_size_bytes':size},timeout=10)
        if response.status_code in (400,409,422): raise ValueError('conflict')
        response.raise_for_status(); return response.json()[0]
    def get_candidate_cv(self,candidate_id,cv_id):
        rows=self._request('GET','/rest/v1/candidate_cvs',params={'id':f'eq.{cv_id}','candidate_id':f'eq.{candidate_id}','select':'id,original_filename,storage_path'}).json()
        if not rows: raise LookupError('Candidate CV not found')
        return rows[0]
    def sign_candidate_cv(self,path,expires_in):
        response=httpx.post(f'{self.url}/storage/v1/object/sign/candidate-cvs/{path}',headers=self.headers,json={'expiresIn':expires_in},timeout=10)
        response.raise_for_status(); signed=response.json().get('signedURL')
        if not isinstance(signed,str) or not signed: raise ValueError('Signing failed')
        return f'{self.url}/storage/v1{signed}' if signed.startswith('/') else signed
    def resolve_ai_work_item(self, application_id):
        rows=self._request('GET','/rest/v1/applications',params={'id':f'eq.{application_id}','select':'id,job_id,cv_id,jobs!applications_job_id_fkey(title,requirements),candidate_cvs!applications_cv_belongs_to_candidate_fkey(id,storage_path,original_filename,mime_type,file_size_bytes)','limit':1}).json()
        if not rows: raise LookupError('Application not found')
        row=rows[0]; job=row.pop('jobs', None); cv=row.pop('candidate_cvs', None)
        if not isinstance(job,dict) or not isinstance(cv,dict) or str(cv.get('id')) != str(row.get('cv_id')): raise ValueError('Invalid application CV snapshot')
        row.update(job_title=job.get('title'), job_requirements=job.get('requirements'), cv_storage_path=cv.get('storage_path'), cv_filename=cv.get('original_filename'), cv_mime_type=cv.get('mime_type'), cv_file_size_bytes=cv.get('file_size_bytes'))
        return row
    def download_candidate_cv(self, path):
        response=httpx.get(f'{self.url}/storage/v1/object/candidate-cvs/{path}',headers=self.headers,timeout=20)
        response.raise_for_status(); return response.content
    def assign_recruiter_to_job_rpc(self,admin_id,job_id,recruiter_id):
        return self._request('POST','/rest/v1/rpc/assign_recruiter_to_job',json={'p_admin_id':admin_id,'p_job_id':job_id,'p_recruiter_id':recruiter_id}).json()
    def unassign_recruiter_from_job_rpc(self,admin_id,job_id,recruiter_id):
        return self._request('POST','/rest/v1/rpc/unassign_recruiter_from_job',json={'p_admin_id':admin_id,'p_job_id':job_id,'p_recruiter_id':recruiter_id}).json()
    def list_recruiter_notes(self,application_id):
        return self._request('GET','/rest/v1/recruiter_notes',params={'application_id':f'eq.{application_id}','select':'id,note,created_at','order':'created_at.asc,id.asc','limit':100}).json()
    def add_recruiter_note(self,recruiter_id,application_id,note):
        response=httpx.post(f'{self.url}/rest/v1/rpc/add_recruiter_note',headers=self.headers,json={'p_recruiter_id':recruiter_id,'p_application_id':application_id,'p_note':note},timeout=10)
        if response.status_code >= 400:
            try: code=response.json().get('code')
            except (TypeError, ValueError): code=None
            if code == '23503': raise LookupError('Resource not found')
            response.raise_for_status()
        rows=response.json()
        if not isinstance(rows,list) or len(rows) != 1: raise ValueError('Invalid recruiter note RPC result')
        return rows[0]
    def recruiter_ai_summary(self,application_id):
        rows=self._request('GET','/rest/v1/ai_summaries',params={'application_id':f'eq.{application_id}','select':'application_id,status,profile_summary,requirements_found,requirements_not_found,interview_questions','limit':1}).json()
        return rows[0] if rows else None
    def admin_ai_summary(self,application_id):
        application=self._request('GET','/rest/v1/applications',params={'id':f'eq.{application_id}','select':'id','limit':1}).json()
        if not application: raise LookupError('Resource not found')
        return self.recruiter_ai_summary(application_id)
    def retry_ai_summary(self,actor_id,application_id):
        self._request('POST','/rest/v1/rpc/retry_ai_summary',json={'p_actor_id':actor_id,'p_application_id':application_id})
    def save_ai_summary_result(self,application_id,result_status,profile_summary,requirements_found,requirements_not_found,interview_questions,error_message):
        self._request('POST','/rest/v1/rpc/save_ai_summary_result',json={'p_application_id':application_id,'p_status':result_status,'p_profile_summary':profile_summary,'p_requirements_found':requirements_found,'p_requirements_not_found':requirements_not_found,'p_interview_questions':interview_questions,'p_error_message':error_message})
    def transition_recruiter_application(self,recruiter_id,application_id,target_stage):
        self._request('POST','/rest/v1/rpc/transition_recruiter_application',json={'p_recruiter_id':recruiter_id,'p_application_id':application_id,'p_target_stage':target_stage})
        rows=self._request('GET','/rest/v1/applications',params={'id':f'eq.{application_id}','select':'id,stage','limit':1}).json()
        if not rows: raise LookupError('Resource not found')
        return rows[0]
    def hire_application(self,recruiter_id,application_id):
        self._request('POST','/rest/v1/rpc/hire_application',json={'p_recruiter_id':recruiter_id,'p_application_id':application_id})
        rows=self._request('GET','/rest/v1/applications',params={'id':f'eq.{application_id}','select':'id,job_id,stage','limit':1}).json()
        if not rows: raise LookupError('Resource not found')
        job=self._request('GET','/rest/v1/jobs',params={'id':f'eq.{rows[0]["job_id"]}','select':'status','limit':1}).json()
        if not job: raise LookupError('Resource not found')
        rows[0]['job_status']=job[0]['status']; return rows[0]
    def schedule_interview(self,recruiter_id,application_id,starts_at,location,meeting_link):
        response=httpx.post(f'{self.url}/rest/v1/rpc/schedule_interview',headers=self.headers,json={'p_recruiter_id':recruiter_id,'p_application_id':application_id,'p_starts_at':starts_at,'p_location':location,'p_meeting_link':meeting_link},timeout=10)
        if response.status_code in (400,409,422): raise ValueError('conflict')
        response.raise_for_status(); interview_id=response.json()
        rows=self._request('GET','/rest/v1/interviews',params={'id':f'eq.{interview_id}','select':'id,application_id,starts_at,ends_at,location,meeting_link','limit':1}).json()
        if not rows: raise LookupError('Resource not found')
        return rows[0]
    def claim_automation_events(self,event_types,limit):
        return self._request('POST','/rest/v1/rpc/claim_email_delivery_events',json={'p_event_types':event_types,'p_limit':limit}).json()
    def claim_ai_summary_events(self,limit):
        return self._request('POST','/rest/v1/rpc/claim_ai_summary_events',json={'p_limit':limit}).json()
    def complete_automation_event(self,event_id):
        response=self._request('POST','/rest/v1/rpc/complete_automation_event',json={'p_event_id':event_id})
        rows=response.json()
        if not isinstance(rows,list) or len(rows)!=1: raise ValueError('Invalid automation completion result')
        return rows[0]
    def fail_automation_event(self,event_id,error_message):
        response=self._request('POST','/rest/v1/rpc/fail_automation_event',json={'p_event_id':event_id,'p_error':error_message})
        rows=response.json()
        if not isinstance(rows,list) or len(rows)!=1: raise ValueError('Invalid automation failure result')
        return rows[0]


def get_supabase_admin_client(settings:Settings=Depends(get_settings)):
    if not settings.supabase_url or not settings.supabase_secret_key: raise RuntimeError('Admin integration is not configured')
    return SupabaseAdminClient(settings.supabase_url,settings.supabase_secret_key)
