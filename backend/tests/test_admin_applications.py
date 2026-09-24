from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.admin_applications import get_service
from app.core.authorization import CurrentUser, get_current_user
from app.main import app
from app.services.admin_applications import AdminApplicationNotFoundError, AdminApplicationsService


ADMIN = "11111111-1111-1111-1111-111111111111"
APP = UUID("22222222-2222-2222-2222-222222222222")
JOB = UUID("33333333-3333-3333-3333-333333333333")
CV = UUID("44444444-4444-4444-4444-444444444444")
CANDIDATE = UUID("55555555-5555-5555-5555-555555555555")
INTERVIEW = UUID("66666666-6666-6666-6666-666666666666")
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def raw_application(*, interviews=None, ai_summaries=None):
    return {
        "id": APP,
        "stage": "interview",
        "applied_at": NOW,
        "profiles": {"id": CANDIDATE, "full_name": "Test Candidate", "email": "candidate@example.invalid", "phone": "+920000000"},
        "jobs": {"id": JOB, "title": "Engineer", "department": "Tech", "location": "Nowshera", "job_type": "full-time", "description": "Build", "requirements": "Python", "application_deadline": datetime(2027, 1, 1, tzinfo=timezone.utc)},
        "candidate_cvs": {"id": CV, "original_filename": "cv.pdf", "uploaded_at": NOW},
        "application_stage_history": [{"stage": "applied", "changed_at": NOW}, {"stage": "interview", "changed_at": datetime(2026, 1, 2, tzinfo=timezone.utc)}],
        "interviews": interviews if interviews is not None else [{"id": INTERVIEW, "starts_at": datetime(2026, 9, 25, 10, tzinfo=timezone.utc), "ends_at": datetime(2026, 9, 25, 11, tzinfo=timezone.utc), "location": "Nowshera", "meeting_link": None}],
        "ai_summaries": ai_summaries if ai_summaries is not None else [{"application_id": APP, "status": "completed", "profile_summary": ["a", "b", "c"], "requirements_found": ["Python"], "requirements_not_found": ["Go"], "interview_questions": ["q1", "q2", "q3"]}],
    }


class Client:
    def __init__(self, *, interviews=None, ai_summaries=None):
        self.interviews = interviews
        self.ai_summaries = ai_summaries
        self.signed = []

    def admin_applications(self):
        row = raw_application(interviews=[], ai_summaries=[])
        return [row]

    def admin_application(self, application_id):
        if application_id == "not-found":
            raise LookupError("Application not found")
        return raw_application(interviews=self.interviews, ai_summaries=self.ai_summaries)

    def admin_application_cv(self, application_id):
        return {"cv_id": CV, "original_filename": "cv.pdf", "storage_path": "private/cv.pdf"}

    def sign_candidate_cv(self, path, expires_in):
        self.signed.append((path, expires_in))
        return "https://signed.example.invalid/cv"


class FakeService:
    def list_applications(self):
        return AdminApplicationsService(Client()).list_applications()

    def get_application(self, application_id):
        if str(application_id) == "99999999-9999-9999-9999-999999999999":
            raise AdminApplicationNotFoundError()
        return AdminApplicationsService(Client()).get_application(application_id)

    def cv_access(self, application_id):
        return AdminApplicationsService(Client()).cv_access(application_id)


@pytest.fixture(autouse=True)
def clean():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def api(role="admin", service=None):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(ADMIN, role, True, "admin@example.invalid")
    app.dependency_overrides[get_service] = lambda: service or FakeService()
    return TestClient(app)


def test_admin_application_list_requires_admin_role():
    assert api("candidate").get("/api/v1/admin/applications").status_code == 403
    assert api("recruiter").get("/api/v1/admin/applications").status_code == 403


def test_admin_application_list_returns_safe_contract():
    response = api().get("/api/v1/admin/applications")
    assert response.status_code == 200
    item = response.json()[0]
    assert set(item) == {"id", "stage", "applied_at", "candidate", "job", "cv"}
    assert set(item["candidate"]) == {"id", "full_name", "email", "phone"}
    assert "storage_path" not in response.text and "recruiter_notes" not in response.text


def test_admin_application_detail_returns_interview_and_ai_summary():
    detail = AdminApplicationsService(Client()).get_application(APP)
    assert detail.interview and detail.interview.id == INTERVIEW
    assert detail.ai_summary and detail.ai_summary.summary_available is True
    assert [item.stage for item in detail.stage_history] == ["applied", "interview"]


def test_admin_application_detail_without_interview_or_ai_still_works():
    detail = AdminApplicationsService(Client(interviews=[], ai_summaries=[])).get_application(APP)
    assert detail.interview is None and detail.ai_summary is None


def test_admin_application_detail_route_rejects_non_admin_and_hides_missing_resource():
    path = f"/api/v1/admin/applications/{APP}"
    assert api("candidate").get(path).status_code == 403
    missing = "99999999-9999-9999-9999-999999999999"
    assert api().get(f"/api/v1/admin/applications/{missing}").status_code == 404


def test_admin_application_cv_access_signs_private_snapshot_without_exposing_path():
    client = Client()
    result = AdminApplicationsService(client).cv_access(APP)
    assert result.url == "https://signed.example.invalid/cv"
    assert result.expires_in == 60
    assert client.signed == [("private/cv.pdf", 60)]
    assert not hasattr(result, "storage_path")
