from datetime import datetime,timezone
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from app.api.v1.recruiter_interviews import get_service
from app.core.authorization import CurrentUser,get_current_user
from app.main import app
R='11111111-1111-1111-1111-111111111111';A=UUID('22222222-2222-2222-2222-222222222222');I=UUID('33333333-3333-3333-3333-333333333333')
class S:
 def __init__(self):self.calls=[]
 def schedule(self,r,a,d):self.calls.append((r,a,d));return {'id':I,'application_id':a,'starts_at':'2030-01-01T10:00:00Z','ends_at':'2030-01-01T11:00:00Z','location':d.location,'meeting_link':d.meeting_link}
@pytest.fixture(autouse=True)
def clean():app.dependency_overrides.clear();yield;app.dependency_overrides.clear()
def client(role='recruiter',s=None):
 s=s or S();app.dependency_overrides[get_current_user]=lambda:CurrentUser(R,role,True,'x@example.invalid');app.dependency_overrides[get_service]=lambda:s;return TestClient(app),s
def test_schedule_binds_actor_and_safe_fields():
 h,s=client();x=h.post(f'/api/v1/recruiter/applications/{A}/interview?recruiter_id=x',json={'starts_at':'2030-01-01T10:00:00Z','location':'Room'});assert x.status_code==200 and s.calls[0][0]==R and x.json()['application_id']==str(A)
@pytest.mark.parametrize('role',['candidate','admin'])
def test_non_recruitters_denied(role):assert client(role)[0].post(f'/api/v1/recruiter/applications/{A}/interview',json={'starts_at':'2030-01-01T10:00:00Z','location':'Room'}).status_code==403
def test_strict_body_rejects_privileged_fields():assert client()[0].post(f'/api/v1/recruiter/applications/{A}/interview',json={'starts_at':'2030-01-01T10:00:00Z','location':'Room','recruiter_id':'x'}).status_code==422
