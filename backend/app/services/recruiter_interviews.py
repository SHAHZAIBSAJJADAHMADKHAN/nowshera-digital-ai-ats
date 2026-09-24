from uuid import UUID
import httpx
from pydantic import ValidationError
from app.schemas.recruiter_interviews import RecruiterInterviewScheduleRequest,RecruiterInterviewScheduleResponse
class NotFound(Exception):pass
class Conflict(Exception):pass
class Operation(Exception):pass
class Service:
 def __init__(self,c):self.c=c
 def schedule(self,r,a,data:RecruiterInterviewScheduleRequest):
  try:
   app=self.c.recruiter_app(str(a));self.c.recruiter_job(r,app['job_id'])
   return RecruiterInterviewScheduleResponse.model_validate(self.c.schedule_interview(r,str(a),data.starts_at.isoformat(),data.location,data.meeting_link))
  except LookupError as e:raise NotFound() from e
  except ValueError as e:raise Conflict() from e
  except (KeyError,TypeError,ValidationError,httpx.HTTPError) as e:raise Operation() from e
