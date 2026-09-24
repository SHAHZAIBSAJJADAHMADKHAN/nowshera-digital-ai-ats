from uuid import UUID
import httpx
from pydantic import ValidationError
from app.schemas.recruiter_hiring import RecruiterHireResponse

class RecruiterHiringNotFoundError(Exception): pass
class RecruiterHiringConflictError(Exception): pass
class RecruiterHiringOperationError(Exception): pass

class RecruiterHiringService:
    def __init__(self, client): self.client=client
    def hire(self, recruiter_id: str, application_id: UUID) -> RecruiterHireResponse:
        try:
            application=self.client.recruiter_app(str(application_id))
            self.client.recruiter_job(recruiter_id, application['job_id'])
            return RecruiterHireResponse.model_validate(self.client.hire_application(recruiter_id,str(application_id)))
        except LookupError as error: raise RecruiterHiringNotFoundError() from error
        except ValueError as error: raise RecruiterHiringConflictError() from error
        except (KeyError,TypeError,ValidationError,httpx.HTTPError) as error: raise RecruiterHiringOperationError() from error
