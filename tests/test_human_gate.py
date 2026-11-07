"""Review and activation use-case tests without a database."""
import pytest
from entities.models import ApplicationError
from governance.model_review import ModelReleaseInteractor
from tests.testing_api import FakeEvents


class FakeReleaseGateway:
    def __init__(self):
        self.approver = None
        self.activated = []

    def authenticate_reviewer(self, username, password, role):
        if password != "correct":
            return None
        return {("reviewer", "REVIEWER"): 11, ("admin", "ADMIN"): 12}.get((username, role))

    def approve_model(self, model_id, user):
        self.approver = user

    def approved_by(self, model_id):
        return self.approver

    def activate_model(self, model_id, user):
        self.activated.append((model_id, user))


def test_unapproved_model_cannot_activate():
    gateway = FakeReleaseGateway()
    gate = ModelReleaseInteractor(gateway, FakeEvents())
    with pytest.raises(ApplicationError) as error:
        gate.activate("admin", "correct", 3)
    assert error.value.code == "HITL_BLOCKED"
    assert not gateway.activated


def test_reviewer_approval_allows_different_admin():
    gateway = FakeReleaseGateway()
    gate = ModelReleaseInteractor(gateway, FakeEvents())
    assert gate.approve("reviewer", "correct", 3)["status"] == "APPROVED"
    assert gate.activate("admin", "correct", 3)["status"] == "ACTIVATED"
    assert gateway.activated == [(3, 12)]


def test_invalid_reviewer_is_rejected():
    gate = ModelReleaseInteractor(FakeReleaseGateway(), FakeEvents())
    with pytest.raises(ApplicationError) as error:
        gate.approve("reviewer", "wrong", 3)
    assert error.value.status == 403
