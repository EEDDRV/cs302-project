"""Composition root: only production location assembling outer implementations."""
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from config import BASE_DIR, get_config
from frameworks_and_drivers.sqlite_gateway import SQLiteGateway
from interface_adapters.model_solver import ExistingSolverAdapter
from interface_adapters.http_controller import register_routes
from use_cases.solve_captcha import SolveCaptchaInteractor
from governance.observable import ObservableSolve
from governance.events import AuditEvents
from governance.model_review import ModelReleaseInteractor


def build_app():
    """Assemble and configure the prototype application."""
    settings = get_config()
    (BASE_DIR / "logs").mkdir(exist_ok=True)
    logger = logging.getLogger("prompt_platoon.audit")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(BASE_DIR / "logs" / "run.jsonl", maxBytes=2_000_000, backupCount=2)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    gateway = SQLiteGateway(settings)
    solver = ExistingSolverAdapter()
    events = AuditEvents(logger, gateway)
    core = SolveCaptchaInteractor(gateway, gateway, solver, events, settings["MAX_IMAGE_BYTES"],
                                  settings["MAX_INFERENCE_MS"], settings["MAX_CASE_COST_USD"],
                                  settings["ESTIMATED_CASE_COST_USD"])
    observed = ObservableSolve(core, events)
    releases = ModelReleaseInteractor(gateway, events)
    web_app = Flask(__name__, template_folder=str(BASE_DIR / "templates"),
                    static_folder=str(BASE_DIR / "static"))
    web_app.config["MAX_CONTENT_LENGTH"] = settings["MAX_IMAGE_BYTES"] + 64 * 1024
    web_app.json.sort_keys = False
    register_routes(web_app, observed, releases, solver, BASE_DIR / "samples",
                    settings["MAX_IMAGE_BYTES"])
    return web_app


app = build_app()

if __name__ == "__main__":
    settings = get_config()
    app.run(host=settings["HOST"], port=settings["PORT"], debug=settings["DEBUG"])
