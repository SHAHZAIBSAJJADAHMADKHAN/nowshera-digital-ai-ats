from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel
Stage=Literal['applied','shortlisted','interview','offer','hired','rejected','withdrawn']
class Job(BaseModel):
 id:UUID; title:str; department:str; location:str; job_type:str; description:str; requirements:str; application_deadline:datetime; openings:int; status:str; created_at:datetime; closed_at:datetime|None
class Candidate(BaseModel): full_name:str; email:str; phone:str|None
class CV(BaseModel): id:UUID; original_filename:str; uploaded_at:datetime
class History(BaseModel): stage:Stage; changed_at:datetime
class Interview(BaseModel): id:UUID; starts_at:datetime; ends_at:datetime|None; location:str|None; meeting_link:str|None
class AppList(BaseModel): id:UUID; job_id:UUID; stage:Stage; applied_at:datetime; candidate:Candidate; cv:CV
class AppDetail(AppList): job:Job; stage_history:list[History]; interview:Interview|None=None
class CVAccess(BaseModel): url:str; expires_in:int; application_id:UUID; cv_id:UUID; original_filename:str
