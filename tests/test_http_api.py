"""Flask adapter integration tests using only fake dependencies."""
import io
from pathlib import Path
import pytest
pytest.importorskip("flask")
from PIL import Image
from flask import Flask
from interface_adapters.http_controller import register_routes
from tests.testing_api import TestingApi


class ReadySolver:
    def ready(self):
        return True


class NoopRelease:
    def approve(self, *_):
        return {}

    def activate(self, *_):
        return {}


def test_real_http_route_calls_testing_api(tmp_path):
    test_api = TestingApi()
    base = Path(__file__).resolve().parents[1]
    flask_app = Flask(__name__, template_folder=str(base / "templates"), static_folder=str(base / "static"))
    register_routes(flask_app, test_api.app, NoopRelease(), ReadySolver(),
                    base / "samples", 5 * 1024 * 1024)
    client = flask_app.test_client()
    buffer = io.BytesIO()
    Image.new("RGB", (64, 32), "white").save(buffer, format="PNG")
    response = client.post("/api/solve", headers={"Authorization": "Bearer valid-token"},
                           data={"captcha_type": "image", "image": (io.BytesIO(buffer.getvalue()), "x.png")})
    assert response.status_code == 200
    assert response.json["result"] == "TEST123"
    assert response.headers["X-Correlation-ID"]
    denied = client.post("/api/solve", data={"image": (io.BytesIO(buffer.getvalue()), "x.png")})
    assert denied.status_code == 401
