from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from app.api.v1.recruiter_hiring import get_service
from app.core.authorization import CurrentUser,get_current_user
from app.main import app

R='11111111-1111-1111-1111-111111111111'; A=UUID('22222222-2222-2222-2222-222222222222'); J=UUID('33333333-3333-3333-3333-333333333333')
class S:
 def __init__(self,error=None):self.calls=[];self.error=error
 def hire(self,r,a):
  self.calls.append((r,a))
  if self.error:raise self.error
  return {'id':a,'job_id':J,'stage':'hired','job_status':'closed'}
@pytest.fixture(autouse=True)
def clean():app.dependency_overrides.clear();yield;app.dependency_overrides.clear()
def client(role='recruiter',s=None):
 s=s or S();app.dependency_overrides[get_current_user]=lambda:CurrentUser(R,role,True,'synthetic@example.invalid');app.dependency_overrides[get_service]=lambda:s;return TestClient(app),s
def test_hire_binds_authenticated_recruiter_and_safe_response():
 h,s=client();x=h.post(f'/api/v1/recruiter/applications/{A}/hire?recruiter_id=bad');assert x.status_code==200 and x.json()=={'id':str(A),'job_id':str(J),'stage':'hired','job_status':'closed'} and s.calls==[(R,A)]
@pytest.mark.parametrize('role',['candidate','admin'])
def test_non_recruitters_denied(role):assert client(role)[0].post(f'/api/v1/recruiter/applications/{A}/hire').status_code==403
def test_bad_id_rejected():assert client()[0].post('/api/v1/recruiter/applications/bad/hire').status_code==422
