from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.candidate_cvs import get_service
from app.core.authorization import CurrentUser, get_current_user
from app.main import app
from app.schemas.candidate_cvs import CandidateCVResponse
from app.services.candidate_cvs import CandidateCVService, CandidateCVValidationError, MAX_CV_BYTES
from app.services.candidate_profile import CandidateProfileOperationError

ACTOR = "11111111-1111-1111-1111-111111111111"

class Client:
    def __init__(self, fail_register=False): self.paths=[]; self.deleted=[]; self.fail_register=fail_register
    def upload_candidate_cv(self,path,content): self.paths.append(path)
    def register_candidate_cv(self,candidate_id,path,filename,size):
        if self.fail_register: raise ValueError('db')
        return {'id':str(UUID('22222222-2222-2222-2222-222222222222')),'original_filename':filename,'mime_type':'application/pdf','file_size_bytes':size,'uploaded_at':'2026-01-01T00:00:00+00:00'}
    def delete_candidate_cv_object(self,path): self.deleted.append(path)

def test_service_versions_and_compensates():
    client=Client(); service=CandidateCVService(client)
    first=service.upload_cv(ACTOR,'../../one.pdf','application/pdf',b'%PDF-1.7 a')
    second=service.upload_cv(ACTOR,'two.pdf','application/pdf',b'%PDF-1.7 b')
    assert first.original_filename=='one.pdf' and second.original_filename=='two.pdf'
    assert len(client.paths)==2 and client.paths[0]!=client.paths[1] and all(f'candidates/{ACTOR}/' in p for p in client.paths)
    failing=Client(True)
    with pytest.raises(CandidateProfileOperationError): CandidateCVService(failing).upload_cv(ACTOR,'x.pdf','application/pdf',b'%PDF-1.7')
    assert failing.deleted==failing.paths

@pytest.mark.parametrize('content_type,content',[('text/plain',b'%PDF-1.7'),('application/pdf',b''),('application/pdf',b'not pdf'),('application/pdf',b'%PDF-'+b'a'*(MAX_CV_BYTES+1))], ids=['wrong-mime','empty','bad-signature','too-large'])
def test_service_validates_pdf(content_type,content):
    with pytest.raises(CandidateCVValidationError): CandidateCVService(Client()).upload_cv(ACTOR,'x.pdf',content_type,content)

def test_exact_2mib_is_accepted():
    result=CandidateCVService(Client()).upload_cv(ACTOR,'x.pdf','application/pdf',b'%PDF-'+b'a'*(MAX_CV_BYTES-5))
    assert result.file_size_bytes==MAX_CV_BYTES

def test_upload_route_uses_actor_and_hides_path():
    class Service:
        def __init__(self): self.calls=[]
        def upload_cv(self,*args):
            self.calls.append(args)
            return CandidateCVResponse(id=UUID('22222222-2222-2222-2222-222222222222'),original_filename='x.pdf',mime_type='application/pdf',file_size_bytes=8,uploaded_at='2026-01-01T00:00:00+00:00')
    service=Service()
    app.dependency_overrides[get_current_user]=lambda: CurrentUser(ACTOR,'candidate',True,'c@example.com')
    app.dependency_overrides[get_service]=lambda: service
    response=TestClient(app).post('/api/v1/candidate/cvs?candidate_id=other',files={'file':('x.pdf',b'%PDF-1.7','application/pdf')})
    app.dependency_overrides.clear()
    assert response.status_code==201 and service.calls[0][0]==ACTOR and 'storage_path' not in response.json()

def test_access_scopes_metadata_before_60_second_signing():
    class AccessClient:
        def __init__(self): self.lookup=[]; self.signed=[]
        def get_candidate_cv(self,owner,cv_id): self.lookup.append((owner,cv_id)); return {'id':cv_id,'original_filename':'x.pdf','storage_path':'candidates/hidden/x.pdf'}
        def sign_candidate_cv(self,path,ttl): self.signed.append((path,ttl)); return 'https://signed.example/token'
    client=AccessClient()
    response=CandidateCVService(client).get_cv_access(ACTOR,'22222222-2222-2222-2222-222222222222')
    assert client.lookup[0][0]==ACTOR and client.signed==[('candidates/hidden/x.pdf',60)]
    assert response.expires_in==60 and 'storage_path' not in response.model_dump()

def test_access_route_auth_privacy_and_safe_errors():
    class Service:
        def __init__(self, error=None): self.calls=[]; self.error=error
        def get_cv_access(self,actor,cv_id):
            self.calls.append((actor,cv_id))
            if self.error: raise self.error
            from app.schemas.candidate_cvs import CandidateCVAccessResponse
            return CandidateCVAccessResponse(url='https://temporary.example/token',expires_in=60,cv_id=cv_id,original_filename='x.pdf')
    cv_id='22222222-2222-2222-2222-222222222222'
    service=Service()
    app.dependency_overrides[get_current_user]=lambda: CurrentUser(ACTOR,'candidate',True,'c@example.com')
    app.dependency_overrides[get_service]=lambda: service
    client=TestClient(app)
    response=client.get(f'/api/v1/candidate/cvs/{cv_id}/access?candidate_id=other')
    assert response.status_code==200 and set(response.json())=={'url','expires_in','cv_id','original_filename'} and service.calls[0][0]==ACTOR
    foreign=Service(__import__('app.services.candidate_profile',fromlist=['CandidateProfileNotFoundError']).CandidateProfileNotFoundError('owner'))
    app.dependency_overrides[get_service]=lambda: foreign
    assert client.get(f'/api/v1/candidate/cvs/{cv_id}/access').status_code==404 and foreign.calls
    failing=Service(CandidateProfileOperationError('SUPABASE_SECRET_KEY service_role Authorization: Bearer storage.objects https://internal'))
    app.dependency_overrides[get_service]=lambda: failing
    failure=client.get(f'/api/v1/candidate/cvs/{cv_id}/access')
    app.dependency_overrides.clear()
    assert failure.status_code==503 and 'service_role' not in failure.text.lower()
