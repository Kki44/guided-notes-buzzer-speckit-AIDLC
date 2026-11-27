from pathlib import Path
from threading import Lock

from flask import Flask

from .activity import EventOrder
from .config import settings
from .routes import api
from .sheets import GoogleSheets
from .store import Store


def create_app(overrides=None):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_mapping(
        settings(), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
        MAX_CONTENT_LENGTH=128 * 1024,
        DATABASE=Path(app.instance_path) / "buzzer.sqlite3",
    )
    if overrides:
        app.config.update(overrides)
    store = Store(app.config["DATABASE"])
    app.extensions["store"] = store
    with store.read() as db:
        sequence = db.execute("SELECT COALESCE(MAX(sequence), 0) FROM submissions").fetchone()[0]
    app.extensions["event_order"] = EventOrder(initial=sequence)
    app.extensions["sheets"] = GoogleSheets()
    app.extensions["export_lock"] = Lock()
    app.register_blueprint(api)

    @app.url_defaults
    def version_static_assets(endpoint, values):
        if endpoint == "static" and "filename" in values:
            path = Path(app.static_folder) / values["filename"]
            if path.is_file():
                values.setdefault("v", str(path.stat().st_mtime_ns))

    return app
