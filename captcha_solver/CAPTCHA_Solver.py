
from .solver_factory import SolverFactory


class Captcha_Solver:
    """Public entry point for CAPTCHA solving."""

    def __init__(self):
        self._factory = SolverFactory()

    def solve(self, captcha_type: str, data: bytes) -> str:
        """Select an adapter and return its prediction."""
        solver = self._factory.get_solver(captcha_type)
        return solver.solve(data)
