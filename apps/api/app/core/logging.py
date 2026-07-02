import json
import logging
import sys
from datetime import UTC, datetime

# Attributes every stdlib LogRecord carries; anything else passed via
# `extra={...}` is application-specific context we want to surface in the
# structured output.
_STANDARD_RECORD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__.keys())


class JsonFormatter(logging.Formatter):
    """Renders each log record as a single-line JSON object.

    Fields passed via `extra={...}` (e.g. job_id, stage) are included
    alongside the standard timestamp/level/logger/message fields, which is
    what makes this "structured" — callers attach machine-parseable context
    instead of interpolating it into a free-text message.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_FIELDS:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure structured (JSON) logging for the app."""
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
