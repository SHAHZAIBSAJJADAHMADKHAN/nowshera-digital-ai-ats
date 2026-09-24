from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from app.api.v1.recruiter_ai_summary import get_service
from app.core.authorization import CurrentUser,get_current_user
from app.core.auth import get_jwt_verifier
from app.main import app
from app.schemas.recruiter_ai_summary import RecruiterAISummaryResponse
from app.services.recruiter_ai_summary import RecruiterAISummaryNotFoundError,RecruiterAISummaryOperationError

R='11111111-1111-1111-1111-111111111111'; A=UUID('22222222-2222-2222-2222-222222222222')
class S:
 def __init__(self,status='completed',error=None):self.status=status;self.error=error;self.calls=[]
 def get_summary(self,r,a):
  self.calls.append((r,a))
  if self.error:raise self.error
  if self.status=='completed':return RecruiterAISummaryResponse(application_id=a,status='completed',summary_available=True,profile_bullets=['a','b','c'],requirements_found=['Python'],requirements_not_found=['Go'],interview_questions=['q1','q2','q3'])
  return RecruiterAISummaryResponse(application_id=a,status=self.status,summary_available=False)
@pytest.fixture(autouse=True)
def clean():app.dependency_overrides.clear();yield;app.dependency_overrides.clear()
def client(role='recruiter',s=None):
 s=s or S();app.dependency_overrides[get_current_user]=lambda:CurrentUser(R,role,True,'x@example.invalid');app.dependency_overrides[get_service]=lambda:s;return TestClient(app),s
def test_unauthenticated():
 app.dependency_overrides[get_jwt_verifier]=lambda:object();assert TestClient(app).get(f'/api/v1/recruiter/applications/{A}/ai-summary').status_code==401
@pytest.mark.parametrize('role',['candidate','admin'])
def test_wrong_roles(role):assert client(role)[0].get(f'/api/v1/recruiter/applications/{A}/ai-summary').status_code==403
def test_completed_allowlist_and_actor():
 c,s=client();x=c.get(f'/api/v1/recruiter/applications/{A}/ai-summary?recruiter_id=bad');assert x.status_code==200 and s.calls==[(R,A)] and set(x.json())=={'application_id','status','is_ai_generated','summary_available','profile_bullets','requirements_found','requirements_not_found','interview_questions'}
@pytest.mark.parametrize('state',['pending','processing','failed','unavailable'])
def test_nonavailable_states_are_safe(state):
 x=client(s=S(state))[0].get(f'/api/v1/recruiter/applications/{A}/ai-summary').json();assert x['status']==state and x['is_ai_generated'] and not x['summary_available'] and x['profile_bullets'] is None
@pytest.mark.parametrize('err,code',[(RecruiterAISummaryNotFoundError(),404),(RecruiterAISummaryOperationError(),503)])
def test_safe_errors(err,code):
 x=client(s=S(error=err))[0].get(f'/api/v1/recruiter/applications/{A}/ai-summary');assert x.status_code==code and 'supabase' not in x.text.lower()
def test_bad_id():assert client()[0].get('/api/v1/recruiter/applications/bad/ai-summary').status_code==422
