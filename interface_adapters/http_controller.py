"""Humble Flask delivery adapter. Business decisions reside in interactors."""
import io
import os
import uuid
from pathlib import Path
from flask import jsonify, render_template, request, send_from_directory, abort
from PIL import Image, UnidentifiedImageError
from entities.models import ApplicationError, SolveCommand

ALLOWED_FORMATS = {"PNG", "JPEG", "GIF", "WEBP", "BMP"}
SAMPLE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def register_routes(app, solve_use_case, release_use_case, solver_adapter, samples_dir: Path,
                    max_image_bytes: int):
    """Bind transport routes to existing Flask and application services."""

    def sample_names():
        samples_dir.mkdir(exist_ok=True)
        return sorted(path.name for path in samples_dir.iterdir()
                      if path.is_file() and path.suffix.lower() in SAMPLE_EXTENSIONS and not path.is_symlink())

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/samples")
    def samples():
        return render_template("samples.html", samples=sample_names())

    @app.get("/samples/image/<path:filename>")
    def sample_image(filename):
        if filename not in sample_names():
            abort(404)
        return send_from_directory(samples_dir, filename, as_attachment=request.args.get("download") == "1")

    @app.get("/api/health")
    def health():
        try:
            solver_adapter.ready()
        except Exception:
            app.logger.exception("Model readiness check failed")
            return jsonify({"ready": False, "message": "Solver unavailable"}), 503
        return jsonify({"ready": True, "message": "Image solver ready"})

    @app.post("/api/solve")
    def solve():
        header = request.headers.get("Authorization", "")
        token = header[7:].strip() if header.lower().startswith("bearer ") else ""
        if not token:
            return jsonify({"error": "Bearer token required.", "code": "UNAUTHORIZED"}), 401
        image = request.files.get("image")
        if image is None or not image.filename:
            return jsonify({"error": "Choose an image file first."}), 400
        content = image.read(max_image_bytes + 1)
        if not content or len(content) > max_image_bytes:
            return jsonify({"error": "Image must be 5 MB or smaller."}), 413
        try:
            with Image.open(io.BytesIO(content)) as image_info:
                if image_info.format not in ALLOWED_FORMATS:
                    return jsonify({"error": "Use PNG, JPEG, GIF, WEBP, or BMP."}), 400
                image_info.verify()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            return jsonify({"error": "The file is not a valid supported image."}), 400
        correlation_id = str(uuid.uuid4())
        cmd = SolveCommand(token, request.form.get("captcha_type", "image"), content, correlation_id)
        result = solve_use_case.execute(cmd)
        response = jsonify({"result": result.prediction, "captcha_type": result.captcha_type,
                            "processing_time_ms": result.processing_time_ms})
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    def require_basic():
        basic = request.authorization
        if basic is None or basic.type.lower() != "basic":
            raise ApplicationError("Reviewer credentials required.", 401, "REVIEW_DENIED")
        return basic.username, basic.password

    @app.post("/api/admin/models/<int:model_id>/approve")
    def approve_model(model_id):
        username, password = require_basic()
        return jsonify(release_use_case.approve(username, password, model_id))

    @app.post("/api/admin/models/<int:model_id>/activate")
    def activate_model(model_id):
        username, password = require_basic()
        return jsonify(release_use_case.activate(username, password, model_id))

    @app.errorhandler(ApplicationError)
    def controlled_error(error):
        return jsonify({"error": str(error), "code": error.code}), error.status

    @app.errorhandler(413)
    def too_large(_):
        return jsonify({"error": "Image must be 5 MB or smaller."}), 413

    @app.errorhandler(Exception)
    def internal_error(error):
        if hasattr(error, "code") and isinstance(error.code, int):
            return error
        app.logger.exception("Unhandled HTTP request failure")
        return jsonify({"error": "Service temporarily unavailable.", "code": "INTERNAL_ERROR"}), 503

    return app
