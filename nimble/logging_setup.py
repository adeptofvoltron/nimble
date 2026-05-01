from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
LOG_PATH: Path = Path.home() / ".nimble" / "nimble.log"


def configure_logging(log_path: Path, debug: bool) -> None:
    root = logging.getLogger()
    if any(type(h).__name__ == "RotatingFileHandler" for h in root.handlers):
        root.setLevel(logging.DEBUG if debug else logging.INFO)
        return
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
        )
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    except OSError as exc:
        fallback = logging.StreamHandler()
        fallback.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(fallback)
        root.setLevel(logging.DEBUG if debug else logging.INFO)
        root.warning(
            "Failed to open log file %s: %s — falling back to stderr", log_path, exc
        )
        return
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)
