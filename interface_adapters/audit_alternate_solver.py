"""Deterministic outer solver adapter for an M3 architecture swap audit.

This adapter intentionally returns a fixed prediction; it is not an AI model.
It implements the same SolverPort interface as ExistingSolverAdapter.
"""


class AuditAlternateSolverAdapter:
    """Return a recognizable prediction through the regular solver port."""

    def solve(self, captcha_type: str, content: bytes) -> str:
        """Produce a fixed prediction for a valid image request.

        Args:
            captcha_type: Caller-declared CAPTCHA category.
            content: Original uploaded image bytes.

        Returns:
            A deterministic prediction suitable for proving adapter wiring.
        """
        if captcha_type != "image" or not content:
            raise ValueError("Expected nonempty image CAPTCHA content")
        return "AUDIT_SWAP_OK"

    def ready(self) -> bool:
        """Report that this deterministic adapter is ready.

        Returns:
            True because no external model must load.
        """
        return True
