"""Boundary tests with fake adapters; no model or database required."""
import pytest
from entities.models import ApplicationError
from tests.testing_api import TestingApi, FakeSolver


def test_success_and_redacted_observability():
    api = TestingApi()
    result = api.solve()
    assert result.prediction == "TEST123"
    assert api.solver.calls == [("image", b"fake-image-bytes")]
    assert api.store.completed[0][1] == "SUCCESS"
    assert [evt[0] for evt in api.events.events] == ["captcha.solve.started", "captcha.solve.completed"]
    assert "valid-token" not in repr(api.events.events)
    assert "fake-image-bytes" not in repr(api.events.events)


def test_authentication_off_ramp_never_calls_model():
    api = TestingApi()
    with pytest.raises(ApplicationError) as error:
        api.solve(token="invalid")
    assert error.value.status == 401
    assert not api.solver.calls


def test_unsupported_type_never_calls_model():
    api = TestingApi()
    with pytest.raises(ApplicationError) as error:
        api.solve(kind="audio")
    assert error.value.code == "UNSUPPORTED_TYPE"
    assert not api.solver.calls


def test_cost_guardrail_fails_closed():
    api = TestingApi(estimated_case_cost_usd=0.01, max_case_cost_usd=0)
    with pytest.raises(ApplicationError) as error:
        api.solve()
    assert error.value.code == "COST_GUARDRAIL"
    assert not api.solver.calls


def test_model_failure_is_controlled_and_recorded():
    api = TestingApi(solver=FakeSolver(failure=RuntimeError("internal secret")))
    with pytest.raises(ApplicationError) as error:
        api.solve()
    assert error.value.code == "MODEL_FAILURE"
    assert "internal secret" not in str(error.value)
    assert api.store.completed[0][1] == "MODEL_FAILURE"


def test_model_output_guardrail_proves_off_ramp():
    api = TestingApi(solver=FakeSolver(result=""))
    with pytest.raises(ApplicationError) as error:
        api.solve()
    assert error.value.code == "MODEL_GUARDRAIL"
    assert api.store.completed[0][1] == "MODEL_GUARDRAIL"
    assert any(e[0] == "captcha.solve.rejected" for e in api.events.events)


def test_quota_denial_prevents_inference():
    api = TestingApi()
    api.store.rejection = ApplicationError("Limit reached", 429, "MONTHLY_QUOTA")
    with pytest.raises(ApplicationError) as error:
        api.solve()
    assert error.value.status == 429
    assert not api.solver.calls


def test_model_swap_changes_only_outer_adapter():
    first = TestingApi(solver=FakeSolver(result="FIRST"))
    second = TestingApi(solver=FakeSolver(result="SECOND"))
    assert first.solve().prediction == "FIRST"
    assert second.solve().prediction == "SECOND"
    assert type(first.app.inner) is type(second.app.inner)
