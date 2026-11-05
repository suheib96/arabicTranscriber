"""Small rotating operational log. No input paths, URLs, transcript or credentials."""

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_logger = logging.getLogger("arabic_transcriber.runtime")
_logger.addHandler(logging.NullHandler())
_FIELDS = {"status", "phase", "elapsed_s", "available_mb", "rss_mb", "pid", "device", "error_type"}


def configure():
    if any(isinstance(h, RotatingFileHandler) for h in _logger.handlers):
        return
    if sys.platform == "darwin":
        root = Path.home() / "Library/Logs/ArabicTranscriber"
    else:
        root = (
            Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/state"))
            / "ArabicTranscriber/logs"
        )
    try:
        root.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            root / "runtime.log", maxBytes=512_000, backupCount=2, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        _logger.addHandler(handler)
        _logger.setLevel(logging.INFO)
        _logger.propagate = False
    except OSError:
        pass  # Logging must never stop a transcription.


def event(name, **fields):
    _logger.info(
        json.dumps(
            {"event": name, **{k: v for k, v in fields.items() if k in _FIELDS}}, ensure_ascii=False
        )
    )
