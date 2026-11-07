"""Human checkpoint for consequential model activation."""
from entities.models import ApplicationError


class ModelReleaseInteractor:
    """Require distinct reviewer approval before administrative activation."""

    def __init__(self, gateway, events):
        self.gateway = gateway
        self.events = events

    def approve(self, username: str, password: str, model_id: int):
        user = self.gateway.authenticate_reviewer(username, password, "REVIEWER")
        if user is None:
            raise ApplicationError("Reviewer credentials or role are invalid.", 403, "REVIEW_DENIED")
        self.gateway.approve_model(model_id, user)
        self.events.record("model.release.approved", f"model-{model_id}", "APPROVED", model_id=model_id, reviewer_id=user)
        return {"model_id": model_id, "status": "APPROVED", "reviewer_id": user}

    def activate(self, username: str, password: str, model_id: int):
        user = self.gateway.authenticate_reviewer(username, password, "ADMIN")
        if user is None:
            raise ApplicationError("Administrator credentials or role are invalid.", 403, "ACTIVATION_DENIED")
        reviewer = self.gateway.approved_by(model_id)
        if reviewer is None or reviewer == user:
            self.events.record("model.release.blocked", f"model-{model_id}", "HITL_BLOCKED", model_id=model_id)
            raise ApplicationError("Model release requires prior approval by a different reviewer.", 409, "HITL_BLOCKED")
        self.gateway.activate_model(model_id, user)
        self.events.record("model.release.activated", f"model-{model_id}", "ACTIVATED", model_id=model_id, actor_id=user)
        return {"model_id": model_id, "status": "ACTIVATED"}
