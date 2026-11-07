
import importlib
import pkgutil

from . import adapters
from .CAPTCHA_Solver_Interface import Captcha_Solver_Interface


class SolverFactory:
    """Discovers and initializes CAPTCHA solver adapters."""

    def __init__(self):
        self._solvers = {}
        self._discover()

    def _discover(self):
        """Automatically discover installed adapters."""
        for module in pkgutil.iter_modules(adapters.__path__):
            if not module.ispkg:
                continue

            adapter = importlib.import_module(
                f"{adapters.__name__}.{module.name}"
            )

            captcha_type = adapter.CAPTCHA_TYPE
            solver_class = adapter.SOLVER_CLASS

            if not issubclass(solver_class, Captcha_Solver_Interface):
                raise TypeError(
                    f"{module.name} does not implement the solver interface"
                )

            if captcha_type in self._solvers:
                raise ValueError(
                    f"Duplicate CAPTCHA type: {captcha_type}"
                )

            self._solvers[captcha_type] = solver_class()

    def get_solver(self, captcha_type: str) -> Captcha_Solver_Interface:
        """Return the adapter associated with a CAPTCHA type."""
        if captcha_type not in self._solvers:
            raise ValueError(
                f"Unsupported CAPTCHA type: {captcha_type}"
            )

        return self._solvers[captcha_type]
