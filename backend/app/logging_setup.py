"""Structured JSON logs to stdout (§14.3). Never log headers, bodies, tokens, keys or source code."""
import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"ts": datetime.now(UTC).isoformat(), "level": record.levelname, "logger": record.name,
                   "msg": record.getMessage()}
        extra = getattr(record, "ctx", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    root = logging.getLogger()
    if any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]
    root.setLevel(logging.INFO)
