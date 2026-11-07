"""Outer adapter for the original, unchanged CAPTCHA solver package."""
from threading import Lock


class ExistingSolverAdapter:
    """Lazy-load and serialize access to the original model instance."""

    def __init__(self):
        self._solver = None
        self._lock = Lock()

    def solve(self, captcha_type: str, content: bytes) -> str:
        with self._lock:
            if self._solver is None:
                from captcha_solver import Captcha_Solver
                self._solver = Captcha_Solver()
            return self._solver.solve(captcha_type, content)

    def ready(self) -> bool:
        with self._lock:
            if self._solver is None:
                from captcha_solver import Captcha_Solver
                self._solver = Captcha_Solver()
        return True
