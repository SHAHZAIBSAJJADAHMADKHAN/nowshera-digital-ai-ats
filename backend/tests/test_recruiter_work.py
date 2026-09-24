from datetime import datetime,timezone
from uuid import UUID
from fastapi.testclient import TestClient
from app.api.v1.recruiter_work import get_service
from app.core.authorization import CurrentUser,get_current_user
from app.main import app
from app.schemas.recruiter_work import Job
from app.services.recruiter_work import NotFound,Service
R='11111111-1111-1111-1111-111111111111';J=UUID('22222222-2222-2222-2222-222222222222')
APP=UUID('33333333-3333-3333-3333-333333333333')
CV=UUID('44444444-4444-4444-4444-444444444444')
INTERVIEW=UUID('55555555-5555-5555-5555-555555555555')
NOW=datetime(2026,1,1,tzinfo=timezone.utc)
class S:
 def __init__(self):self.calls=[]
 def jobs(self,r):
  self.calls.append(r);return [Job(id=J,title='J',department='D',location='L',job_type='full-time',description='d',requirements='r',application_deadline=datetime(2027,1,1,tzinfo=timezone.utc),openings=1,status='closed',created_at=datetime(2026,1,1,tzinfo=timezone.utc),closed_at=None)]
class DetailClient:
 def __init__(self,interviews=None,authorized=True):self.interviews=interviews;self.authorized=authorized;self.calls=[]
 def recruiter_app(self,a):
  self.calls.append(('app',a));return {'id':APP,'job_id':J,'stage':'interview','applied_at':NOW,'profiles':{'full_name':'Test Candidate','email':'candidate@example.invalid','phone':None},'candidate_cvs':{'id':CV,'original_filename':'cv.pdf','uploaded_at':NOW},'application_stage_history':[{'stage':'applied','changed_at':NOW}],'interviews':self.interviews}
 def recruiter_job(self,r,j):
  self.calls.append(('job',r,j))
  if not self.authorized:raise LookupError('Resource not found')
  return {'id':J,'title':'Engineer','department':'Tech','location':'Nowshera','job_type':'full-time','description':'d','requirements':'r','application_deadline':datetime(2027,1,1,tzinfo=timezone.utc),'openings':1,'status':'open','created_at':NOW,'closed_at':None}

def test_recruiter_jobs_uses_authenticated_actor_and_safe_shape():
 s=S();app.dependency_overrides[get_current_user]=lambda:CurrentUser(R,'recruiter',True,'r@example.com');app.dependency_overrides[get_service]=lambda:s
 x=TestClient(app).get('/api/v1/recruiter/jobs?recruiter_id=other');app.dependency_overrides.clear()
 assert x.status_code==200 and s.calls==[R] and 'created_by' not in x.text

def test_application_detail_returns_persisted_interview_information():
 interview={'id':INTERVIEW,'starts_at':datetime(2026,9,25,10,tzinfo=timezone.utc),'ends_at':datetime(2026,9,25,11,tzinfo=timezone.utc),'location':'Nowshera','meeting_link':None}
 result=Service(DetailClient(interviews=[interview])).app(R,APP)
 assert result.interview is not None
 assert result.interview.id==INTERVIEW
 assert result.interview.starts_at==interview['starts_at']
 assert result.interview.ends_at==interview['ends_at']
 assert result.interview.location=='Nowshera'
 assert result.interview.meeting_link is None

def test_application_detail_without_interview_still_returns_detail():
 result=Service(DetailClient(interviews=[])).app(R,APP)
 assert result.id==APP and result.interview is None and result.job.id==J

def test_application_detail_keeps_assignment_authorization_required():
 try:
  Service(DetailClient(interviews=[],authorized=False)).app(R,APP)
 except NotFound:
  pass
 else:
  raise AssertionError('Expected assigned recruiter check to reject detail access')

def test_recruiter_routes_reject_wrong_roles_and_malformed_ids():
 app.dependency_overrides[get_current_user]=lambda:CurrentUser(R,'candidate',True,'c@example.com')
 assert TestClient(app).get('/api/v1/recruiter/jobs').status_code==403
 app.dependency_overrides[get_current_user]=lambda:CurrentUser(R,'admin',True,'a@example.com')
 assert TestClient(app).get('/api/v1/recruiter/jobs').status_code==403
 app.dependency_overrides[get_current_user]=lambda:CurrentUser(R,'recruiter',True,'r@example.com')
 app.dependency_overrides[get_service]=lambda:S()
 assert TestClient(app).get('/api/v1/recruiter/jobs/not-a-uuid').status_code==422
 app.dependency_overrides.clear()
