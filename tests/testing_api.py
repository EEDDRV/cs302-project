"""Testing API for business rules; never initializes a real AI model."""
from entities.models import CustomerIdentity, SolveCommand
from use_cases.solve_captcha import SolveCaptchaInteractor
from governance.observable import ObservableSolve


class FakeAuth:
    def identify(self, token):
        return CustomerIdentity(1, 2, 1000, 120) if token == "valid-token" else None


class FakeStore:
    def __init__(self):
        self.adapter_id = 3
        self.reservations = []
        self.completed = []
        self.rejection = None

    def available_adapter(self, captcha_type):
        return self.adapter_id if captcha_type == "image" else None

    def reserve(self, identity, captcha_type, adapter_id, correlation_id):
        if self.rejection:
            raise self.rejection
        self.reservations.append((identity, captcha_type, adapter_id, correlation_id))
        return len(self.reservations)

    def complete(self, request_id, status, prediction, duration_ms, error):
        self.completed.append((request_id, status, prediction, duration_ms, error))


class FakeSolver:
    def __init__(self, result="TEST123", failure=None):
        self.result = result
        self.failure = failure
        self.calls = []

    def solve(self, captcha_type, content):
        self.calls.append((captcha_type, content))
        if self.failure:
            raise self.failure
        return self.result


class FakeEvents:
    def __init__(self):
        self.events = []

    def record(self, event, correlation_id, status, customer_id=None, **details):
        self.events.append((event, correlation_id, status, customer_id, details))


class TestingApi:
    """Provide the M3 testing boundary with injectable fake components."""
    __test__ = False

    def __init__(self, solver=None, max_case_cost_usd=0, estimated_case_cost_usd=0, inference_budget_ms=10000):
        self.auth = FakeAuth()
        self.store = FakeStore()
        self.solver = solver or FakeSolver()
        self.events = FakeEvents()
        inner = SolveCaptchaInteractor(self.auth, self.store, self.solver, self.events,
                                       5 * 1024 * 1024, inference_budget_ms,
                                       max_case_cost_usd, estimated_case_cost_usd)
        self.app = ObservableSolve(inner, self.events)

    def solve(self, token="valid-token", kind="image", content=b"fake-image-bytes"):
        return self.app.execute(SolveCommand(token, kind, content, "test-correlation-id"))
