from pathlib import Path

from captcha_solver.CAPTCHA_Solver_Interface import Captcha_Solver_Interface
from .ocr_module import load_ocr_model, predict_ocr_from_bytes


class Image_Captcha_Solver(Captcha_Solver_Interface):
    """Adapter for image-based CAPTCHA recognition."""

    def __init__(self):
        model_path = Path(__file__).parent / "captcha_model.pt"
        self.ocr_model = load_ocr_model(str(model_path))

    def solve(self, data: bytes) -> str:
        return predict_ocr_from_bytes(self.ocr_model, data)
