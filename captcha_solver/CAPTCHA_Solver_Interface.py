from abc import ABC, abstractmethod

class Captcha_Solver_Interface(ABC):
    """Defines the contract for CAPTCHA solver adapters."""

    @abstractmethod
    def solve(self, data: bytes) -> str:
        """Return the predicted CAPTCHA solution."""
        pass
