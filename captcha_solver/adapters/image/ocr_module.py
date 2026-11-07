# ocr_module.py

import io
from pathlib import Path

import numpy as np
from PIL import Image

import torch
import torch.nn as nn
import torch.nn.functional as F


CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
BLANK_IDX = 0
IDX_TO_CHAR = {i + 1: ch for i, ch in enumerate(CHARS)}


class ConvBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, pool=None, dropout=0.0):
        super().__init__()
        layers = [
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        ]
        if dropout > 0:
            layers.append(nn.Dropout2d(dropout))
        self.layers = nn.Sequential(*layers)
        self.pool = nn.MaxPool2d(pool) if pool is not None else None

    def forward(self, x):
        x = self.layers(x)
        if self.pool is not None:
            x = self.pool(x)
        return x


class SmallCRNN(nn.Module):
    def __init__(self, num_classes: int, img_height: int, img_width: int, rnn_hidden: int = 64):
        super().__init__()

        self.cnn = nn.Sequential(
            ConvBlock(1, 32, pool=(2, 2), dropout=0.05),
            ConvBlock(32, 48, pool=(2, 2), dropout=0.05),
            ConvBlock(48, 64, pool=(2, 1), dropout=0.10),
            ConvBlock(64, 64, pool=(2, 1), dropout=0.10),
        )

        with torch.no_grad():
            dummy = torch.zeros(1, 1, img_height, img_width)
            feats = self.cnn(dummy)
            _, c, h, _ = feats.shape

        feature_dim = c * h

        self.rnn_input_proj = nn.Linear(feature_dim, 96)
        self.gru = nn.GRU(
            input_size=96,
            hidden_size=rnn_hidden,
            num_layers=2,
            bidirectional=True,
            dropout=0.1,
            batch_first=False,
        )
        self.classifier = nn.Linear(rnn_hidden * 2, num_classes)

    def forward(self, x):
        feats = self.cnn(x)                           # [B, C, Hf, Wf]
        b, c, h, w = feats.shape
        feats = feats.permute(3, 0, 1, 2).contiguous()  # [Wf, B, C, Hf]
        feats = feats.view(w, b, c * h)                 # [Wf, B, C*Hf]
        feats = self.rnn_input_proj(feats)              # [Wf, B, 96]
        seq, _ = self.gru(feats)                        # [Wf, B, 2H]
        logits = self.classifier(seq)                   # [Wf, B, C]
        return F.log_softmax(logits, dim=2)


def _get_device(device: str = "auto") -> torch.device:
    if device == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(device)


def _preprocess_image_bytes(image_bytes: bytes, img_height: int, img_width: int) -> torch.Tensor:
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    img = img.resize((img_width, img_height), Image.Resampling.BILINEAR)

    arr = np.asarray(img, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(arr).unsqueeze(0)  # [1, H, W]

    # Match training normalization
    tensor = (tensor - 0.5) / 0.5

    return tensor.unsqueeze(0)  # [1, 1, H, W]


def _greedy_ctc_decode(log_probs: torch.Tensor) -> list[str]:
    pred = log_probs.argmax(dim=2)  # [T, B]
    decoded_strings = []

    for b in range(pred.size(1)):
        seq = pred[:, b].tolist()
        decoded = []
        prev = None

        for idx in seq:
            if idx != prev and idx != BLANK_IDX:
                decoded.append(IDX_TO_CHAR.get(idx, ""))
            prev = idx

        decoded_strings.append("".join(decoded))

    return decoded_strings


def load_ocr_model(checkpoint_path: str = "artifacts/best_model.pt", device: str = "auto") -> dict:
    """
    Load OCR model into memory once and return everything needed for inference.

    Returns:
        dict with:
            model
            device
            img_height
            img_width
            chars
            checkpoint_path
    """
    checkpoint_path = Path(checkpoint_path)
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    torch_device = _get_device(device)
    checkpoint = torch.load(checkpoint_path, map_location=torch_device)

    chars = checkpoint["chars"]
    img_height = checkpoint["img_height"]
    img_width = checkpoint["img_width"]
    rnn_hidden = checkpoint["rnn_hidden"]

    if chars != CHARS:
        raise ValueError(
            f"Checkpoint charset does not match module charset.\n"
            f"Checkpoint: {chars}\n"
            f"Module:     {CHARS}"
        )

    model = SmallCRNN(
        num_classes=len(CHARS) + 1,
        img_height=img_height,
        img_width=img_width,
        rnn_hidden=rnn_hidden,
    ).to(torch_device)

    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    return {
        "model": model,
        "device": torch_device,
        "img_height": img_height,
        "img_width": img_width,
        "chars": chars,
        "checkpoint_path": str(checkpoint_path),
    }


def predict_ocr_from_bytes(model_bundle: dict, image_bytes: bytes) -> str:
    """
    Run OCR on raw image bytes, such as requests.get(...).content.
    """
    if not image_bytes:
        raise ValueError("image_bytes is empty")

    model = model_bundle["model"]
    device = model_bundle["device"]
    img_height = model_bundle["img_height"]
    img_width = model_bundle["img_width"]

    x = _preprocess_image_bytes(image_bytes, img_height, img_width).to(device)

    with torch.no_grad():
        log_probs = model(x).cpu()

    decoded_strings = _greedy_ctc_decode(log_probs)
    return decoded_strings[0]


def predict_ocr_text(model_bundle: dict, image_bytes: bytes) -> str:
    """
    Convenience alias.
    """
    return predict_ocr_from_bytes(model_bundle, image_bytes)