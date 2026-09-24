from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.recruiter_pipeline import get_service
from app.core.authorization import CurrentUser, get_current_user
from app.main import app

R = '11111111-1111-1111-1111-111111111111'
A = UUID('22222222-2222-2222-2222-222222222222')


class Service:
    def __init__(self, error=None): self.calls = []; self.error = error
    def transition(self, recruiter_id, application_id, stage):
        self.calls.append((recruiter_id, application_id, stage))
        if self.error: raise self.error
        return {'id': application_id, 'stage': stage}


@pytest.fixture(autouse=True)
def clean():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def client(role='recruiter', service=None):
    service = service or Service()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(R, role, True, 'synthetic@example.invalid')
    app.dependency_overrides[get_service] = lambda: service
    return TestClient(app), service


@pytest.mark.parametrize('stage', ['shortlisted', 'offer', 'rejected'])
def test_allowlisted_targets_bind_current_recruiter(stage):
    http, service = client()
    response = http.patch(f'/api/v1/recruiter/applications/{A}/stage?recruiter_id=spoofed', json={'stage': stage})
    assert response.status_code == 200
    assert response.json() == {'id': str(A), 'stage': stage}
    assert service.calls == [(R, A, stage)]


@pytest.mark.parametrize('stage', ['applied', 'interview', 'hired', 'withdrawn', 'unknown'])
def test_non_step_one_targets_are_not_exposed(stage):
    http, service = client()
    response = http.patch(f'/api/v1/recruiter/applications/{A}/stage', json={'stage': stage})
    assert response.status_code == 422
    assert service.calls == []


@pytest.mark.parametrize('role', ['candidate', 'admin'])
def test_non_recruiters_are_denied(role):
    assert client(role)[0].patch(f'/api/v1/recruiter/applications/{A}/stage', json={'stage': 'shortlisted'}).status_code == 403


def test_extra_actor_fields_are_rejected():
    http, service = client()
    assert http.patch(f'/api/v1/recruiter/applications/{A}/stage', json={'stage': 'shortlisted', 'recruiter_id': 'spoofed'}).status_code == 422
    assert service.calls == []


def test_bad_identifier_is_rejected():
    assert client()[0].patch('/api/v1/recruiter/applications/not-a-uuid/stage', json={'stage': 'shortlisted'}).status_code == 422
