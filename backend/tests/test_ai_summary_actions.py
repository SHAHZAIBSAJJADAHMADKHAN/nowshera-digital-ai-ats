from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.ai.summary_contract import AI_SUMMARY_INSTRUCTION
from app.api.v1.ai_summary_actions import get_actions, get_admin_service, get_processing_service
from app.core.config import Settings, get_settings
from app.core.authorization import CurrentUser, get_current_user
from app.main import app
from app.schemas.recruiter_ai_summary import RecruiterAISummaryResponse

ACTOR = "11111111-1111-1111-1111-111111111111"
APP = UUID("22222222-2222-2222-2222-222222222222")


class Actions:
    def __init__(self): self.retries=[]; self.results=[]
    def retry(self, actor, application): self.retries.append((actor, application))
    def ingest(self, application, data): self.results.append((application, data))


class Admin:
    def get_summary(self, application):
        return RecruiterAISummaryResponse(application_id=application,status="completed",summary_available=True,profile_bullets=["a","b","c"],requirements_found=["Python"],requirements_not_found=["Go"],interview_questions=["q1","q2","q3"])


class Processor:
    def __init__(self): self.processed=[]
    def process(self, application): self.processed.append(application)


@pytest.fixture(autouse=True)
def clean():
    app.dependency_overrides.clear(); yield; app.dependency_overrides.clear()


def client(role="recruiter"):
    actions=Actions(); app.dependency_overrides[get_current_user]=lambda: CurrentUser(ACTOR,role,True,"synthetic@example.invalid")
    app.dependency_overrides[get_actions]=lambda: actions
    app.dependency_overrides[get_admin_service]=lambda: Admin()
    return TestClient(app), actions


def valid_summary():
    return {"status":"completed","summary":{"profile_summary":["Python experience","API work","Testing experience"],"requirements_analysis":{"requirements_mentioned":["Python"],"requirements_not_found":["Go"]},"interview_questions":["q1","q2","q3"]}}


def test_internal_result_accepts_valid_structured_summary():
    c, actions=client(); app.dependency_overrides[get_settings]=lambda: Settings(internal_automation_key="synthetic-key")
    response=c.post(f"/api/v1/internal/ai-summaries/{APP}/result",headers={"X-Internal-Automation-Key":"synthetic-key"},json=valid_summary())
    assert response.status_code==204 and actions.results[0][0]==APP


@pytest.mark.parametrize("payload",[
    {"status":"completed","summary":{"profile_summary":["a","b","c"],"requirements_analysis":{"requirements_mentioned":[],"requirements_not_found":[]},"interview_questions":["q1","q2"]}},
    {"status":"completed","summary":{"profile_summary":["a","b","c"],"requirements_analysis":{"requirements_mentioned":[],"requirements_not_found":[]},"interview_questions":["q1","q2","q3"]},"score":99},
    {"status":"failed"},
])
def test_internal_result_rejects_malformed_summary(payload):
    c, _=client(); app.dependency_overrides[get_settings]=lambda: Settings(internal_automation_key="synthetic-key")
    assert c.post(f"/api/v1/internal/ai-summaries/{APP}/result",headers={"X-Internal-Automation-Key":"synthetic-key"},json=payload).status_code==422


def test_browser_authentication_cannot_ingest_ai_result():
    c, actions=client()
    assert c.post(f"/api/v1/internal/ai-summaries/{APP}/result",headers={"Authorization":"Bearer browser"},json=valid_summary()).status_code==401
    assert actions.results==[]


def test_browser_jwt_cannot_invoke_trusted_processing_and_key_can():
    c, _=client(); processor=Processor()
    app.dependency_overrides[get_settings]=lambda: Settings(internal_automation_key="synthetic-key")
    app.dependency_overrides[get_processing_service]=lambda: processor
    path=f"/api/v1/internal/ai-summaries/{APP}/process"
    assert c.post(path, headers={"Authorization":"Bearer browser"}).status_code == 401
    assert processor.processed == []
    assert c.post(path, headers={"X-Internal-Automation-Key":"synthetic-key"}).status_code == 204
    assert processor.processed == [APP]


@pytest.mark.parametrize("role,expected",[("recruiter",204),("admin",204),("candidate",403)])
def test_retry_role_gate(role,expected):
    c, actions=client(role)
    path=f"/api/v1/{'admin' if role=='admin' else 'recruiter'}/applications/{APP}/ai-summary/retry"
    response=c.post(path)
    assert response.status_code==expected
    assert (len(actions.retries)==1)==(expected==204)


def test_admin_can_read_and_candidate_cannot():
    assert client("admin")[0].get(f"/api/v1/admin/applications/{APP}/ai-summary").status_code==200
    assert client("candidate")[0].get(f"/api/v1/admin/applications/{APP}/ai-summary").status_code==403


def test_prompt_contract_has_injection_and_decision_safety_guards():
    text=AI_SUMMARY_INSTRUCTION.lower()
    for phrase in ("untrusted data","prompt-injection","score","ranking","hire/reject recommendation","age, gender, religion, or marital status"):
        assert phrase in text
