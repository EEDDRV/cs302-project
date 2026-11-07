"""Primary use case: authenticated image CAPTCHA prediction."""
import time
from entities.models import ApplicationError, SolveCommand, SolveResult
from use_cases.ports import AuthenticationPort, EventPort, RequestStorePort, SolverPort


class SolveCaptchaInteractor:
    """Coordinate policies using ports, without transport or model dependencies."""

    def __init__(self, auth: AuthenticationPort, store: RequestStorePort,
                 solver: SolverPort, events: EventPort, max_image_bytes: int,
                 inference_budget_ms: int, max_case_cost_usd: float,
                 estimated_case_cost_usd: float):
        self.auth = auth
        self.store = store
        self.solver = solver
        self.events = events
        self.max_image_bytes = max_image_bytes
        self.inference_budget_ms = inference_budget_ms
        self.max_case_cost_usd = max_case_cost_usd
        self.estimated_case_cost_usd = estimated_case_cost_usd

    def execute(self, command: SolveCommand) -> SolveResult:
        identity = self.auth.identify(command.bearer_token)
        if identity is None:
            raise ApplicationError("Invalid or expired API key.", 401, "UNAUTHORIZED")
        if command.captcha_type != "image":
            raise ApplicationError("Only the image adapter is available.", 400, "UNSUPPORTED_TYPE")
        if not command.content or len(command.content) > self.max_image_bytes:
            raise ApplicationError("Image is empty or exceeds the size limit.", 413, "IMAGE_LIMIT")
        if self.estimated_case_cost_usd > self.max_case_cost_usd:
            raise ApplicationError("Per-case cost cap exceeded.", 429, "COST_GUARDRAIL")
        adapter_id = self.store.available_adapter(command.captcha_type)
        if adapter_id is None:
            raise ApplicationError("No active image solver is registered.", 503, "ADAPTER_UNAVAILABLE")
        request_id = self.store.reserve(identity, command.captcha_type, adapter_id, command.correlation_id)
        started = time.perf_counter()
        try:
            prediction = str(self.solver.solve(command.captcha_type, command.content))
            duration = round((time.perf_counter() - started) * 1000)
            if duration > self.inference_budget_ms:
                raise ApplicationError("Inference exceeded configured resource budget.", 503, "RESOURCE_GUARDRAIL")
            if not prediction or len(prediction) > 255:
                raise ApplicationError("The model produced an invalid prediction.", 503, "MODEL_GUARDRAIL")
        except Exception as exc:
            duration = round((time.perf_counter() - started) * 1000)
            code = exc.code if isinstance(exc, ApplicationError) else "MODEL_FAILURE"
            self.store.complete(request_id, code, None, duration, code)
            self.events.record("captcha.solve.failed", command.correlation_id, code, identity.customer_id,
                               processing_time_ms=duration)
            if isinstance(exc, ApplicationError):
                raise
            raise ApplicationError("Prediction failed; check the server log.", 503, "MODEL_FAILURE") from exc
        self.store.complete(request_id, "SUCCESS", prediction, duration, None)
        self.events.record("captcha.solve.completed", command.correlation_id, "SUCCESS", identity.customer_id,
                           captcha_type=command.captcha_type, processing_time_ms=duration)
        return SolveResult(prediction, command.captcha_type, duration, command.correlation_id)
