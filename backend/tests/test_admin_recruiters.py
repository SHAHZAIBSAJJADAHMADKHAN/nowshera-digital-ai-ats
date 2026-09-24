import pytest
from fastapi import HTTPException
from app.schemas.admin_recruiters import RecruiterCreate
from app.services.admin_recruiters import AdminRecruiterService

class Client:
    def __init__(self, fail=''): self.fail=fail; self.deleted=[]; self.provisioned=[]
    def invite_recruiter(self, email):
        if self.fail=='invite': raise ValueError()
        return {'id':'new-recruiter'}
    def provision(self,*args):
        self.provisioned.append(args)
        if self.fail=='provision': raise RuntimeError()
    def delete_auth_user(self,id): self.deleted.append(id)
    def get_recruiter(self,id): return {'id':id,'role':'recruiter','is_active':True}
    def deactivate(self,*args):
        if self.fail=='missing': raise LookupError()
        return True
    def list_recruiters(self,*_): return [{'role':'recruiter'}]

def test_creation_forces_recruiter_profile_and_safe_response():
    client=Client(); result=AdminRecruiterService(client).create('admin',RecruiterCreate(full_name='Recruiter',email='recruiter@example.com'))
    assert result['role']=='recruiter' and client.provisioned[0][0]=='admin'
def test_duplicate_and_compensation():
    with pytest.raises(HTTPException) as error: AdminRecruiterService(Client('invite')).create('admin',RecruiterCreate(full_name='R',email='r@example.com'))
    assert error.value.status_code==409
    client=Client('provision')
    with pytest.raises(HTTPException): AdminRecruiterService(client).create('admin',RecruiterCreate(full_name='R',email='r@example.com'))
    assert client.deleted==['new-recruiter']
def test_deactivate_is_safe_and_not_found_is_404():
    assert AdminRecruiterService(Client()).deactivate('admin','r')['is_active'] is False
    with pytest.raises(HTTPException) as error: AdminRecruiterService(Client('missing')).deactivate('admin','r')
    assert error.value.status_code==404
