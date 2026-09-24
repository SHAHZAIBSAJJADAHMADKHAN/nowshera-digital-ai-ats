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
        try: changed=self.client.deactivate(admin_id,recruiter_id)
        except LookupError: raise HTTPException(404,'Recruiter not found')
        return {'id':recruiter_id,'is_active':False,'changed':changed}
