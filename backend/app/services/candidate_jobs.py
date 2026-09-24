from uuid import UUID
import httpx
from pydantic import ValidationError
from app.schemas.candidate_jobs import CandidateJobDetailResponse, CandidateJobListResponse
class CandidateJobNotFoundError(Exception): pass
class CandidateJobOperationError(Exception): pass
class CandidateJobService:
    def __init__(self,client): self.client=client
    def list_jobs(self):
        try: return [CandidateJobListResponse.model_validate(x) for x in self.client.list_candidate_jobs()]
        except (KeyError,TypeError,ValueError,ValidationError,httpx.HTTPError) as e: raise CandidateJobOperationError() from e
    def get_job(self,job_id:UUID|str):
        try: return CandidateJobDetailResponse.model_validate(self.client.get_candidate_job(str(job_id)))
        except LookupError as e: raise CandidateJobNotFoundError() from e
        except (KeyError,TypeError,ValueError,ValidationError,httpx.HTTPError) as e: raise CandidateJobOperationError() from e
