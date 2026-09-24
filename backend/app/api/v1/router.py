from fastapi import APIRouter, Depends

from app.core.authorization import CurrentUser, get_current_user
from app.api.v1.admin_dashboard import router as admin_dashboard_router
from app.api.v1.candidate_cvs import router as candidate_cv_router
from app.api.v1.candidate_applications import router as candidate_application_router
from app.api.v1.candidate_application_tracking import router as candidate_application_tracking_router
from app.api.v1.candidate_application_withdrawal import router as candidate_application_withdrawal_router
from app.api.v1.candidate_jobs import router as candidate_job_router
from app.api.v1.candidate_profile import router as candidate_profile_router
from app.api.v1.admin_job_assignments import router as admin_job_assignment_router
from app.api.v1.admin_jobs import router as admin_job_router
from app.api.v1.admin_recruiters import router as admin_recruiter_router
from app.api.v1.admin_applications import router as admin_application_router
from app.api.v1.recruiter_work import router as recruiter_work_router
from app.api.v1.recruiter_notes import router as recruiter_notes_router
from app.api.v1.recruiter_ai_summary import router as recruiter_ai_summary_router
from app.api.v1.recruiter_pipeline import router as recruiter_pipeline_router
from app.api.v1.recruiter_hiring import router as recruiter_hiring_router
from app.api.v1.recruiter_interviews import router as recruiter_interviews_router
from app.api.v1.internal_automation_events import router as internal_automation_events_router
from app.api.v1.ai_summary_actions import admin_router as admin_ai_summary_router, recruiter_router as recruiter_ai_summary_actions_router, internal_router as internal_ai_summary_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(admin_dashboard_router)
api_v1_router.include_router(candidate_profile_router)
api_v1_router.include_router(candidate_cv_router)
api_v1_router.include_router(candidate_application_router)
api_v1_router.include_router(candidate_application_tracking_router)
api_v1_router.include_router(candidate_application_withdrawal_router)
api_v1_router.include_router(candidate_job_router)
api_v1_router.include_router(admin_job_assignment_router)
api_v1_router.include_router(admin_job_router)
api_v1_router.include_router(admin_recruiter_router)
api_v1_router.include_router(admin_application_router)
api_v1_router.include_router(recruiter_work_router)
api_v1_router.include_router(recruiter_notes_router)
api_v1_router.include_router(recruiter_ai_summary_router)
api_v1_router.include_router(recruiter_pipeline_router)
api_v1_router.include_router(recruiter_hiring_router)
api_v1_router.include_router(recruiter_interviews_router)
api_v1_router.include_router(internal_automation_events_router)
api_v1_router.include_router(recruiter_ai_summary_actions_router)
api_v1_router.include_router(admin_ai_summary_router)
api_v1_router.include_router(internal_ai_summary_router)


@api_v1_router.get("/auth/me")
async def auth_me(user: CurrentUser = Depends(get_current_user)) -> dict[str, str | bool | None]:
    return {"user_id": user.user_id, "email": user.email, "role": user.role, "is_active": user.is_active}
