from fastapi import HTTPException

class AdminRecruiterService:
    def __init__(self, client): self.client=client
    def list(self, limit:int, offset:int): return self.client.list_recruiters(limit,offset)
    def create(self, admin_id:str, data):
        try: user=self.client.invite_recruiter(data.email)
        except ValueError: raise HTTPException(409,'Recruiter email already exists')
        try: self.client.provision(admin_id,user['id'],data.full_name,data.email,data.phone)
        except Exception:
            self.client.delete_auth_user(user['id'])
            raise HTTPException(502,'Recruiter provisioning failed')
        return self.client.get_recruiter(user['id'])
    def deactivate(self, admin_id:str, recruiter_id:str):
        self._require_recruiter(recruiter_id)
        try: changed=self.client.deactivate(admin_id,recruiter_id)
        except (LookupError, ValueError): raise HTTPException(404,'Recruiter not found')
        return {'id':recruiter_id,'is_active':False,'changed':changed}
    def reactivate(self, admin_id:str, recruiter_id:str):
        self._require_recruiter(recruiter_id)
        try: changed=self.client.reactivate(admin_id,recruiter_id)
        except (LookupError, ValueError): raise HTTPException(404,'Recruiter not found')
        return {'recruiter':self._require_recruiter(recruiter_id),'changed':changed}
    def update(self, admin_id:str, recruiter_id:str, data):
        recruiter=self._require_recruiter(recruiter_id)
        changes=data.model_dump(exclude_unset=True)
        full_name=changes.get('full_name',recruiter['full_name'])
        phone=changes['phone'] if 'phone' in changes else recruiter.get('phone')
        try: self.client.update_recruiter(admin_id,recruiter_id,full_name,phone)
        except (LookupError, ValueError): raise HTTPException(404,'Recruiter not found')
        return self._require_recruiter(recruiter_id)
    def _require_recruiter(self, recruiter_id:str):
        try: recruiter=self.client.get_recruiter(recruiter_id)
        except (LookupError, IndexError): raise HTTPException(404,'Recruiter not found')
        if recruiter.get('role')!='recruiter': raise HTTPException(404,'Recruiter not found')
        return recruiter
