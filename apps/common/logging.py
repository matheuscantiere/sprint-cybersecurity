import json
import logging
import re

_SENSITIVE_RE = re.compile(
    r"(?i)(password|token|authorization|secret|api_key)\s*[=:]\s*\S+",
)


class SensitiveDataFilter(logging.Filter):
    """Redact sensitive key=value pairs from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            try:
                record.msg = _SENSITIVE_RE.sub(r"\1=[REDACTED]", record.getMessage())
                record.args = ()
            except Exception:  # noqa: S110
                pass
        else:
            record.msg = _SENSITIVE_RE.sub(r"\1=[REDACTED]", str(record.msg))
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("request_id", "user_id", "path", "method", "status"):
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        return json.dumps(log_entry)
