import contextvars
import json
import logging
import re

_SENSITIVE_RE = re.compile(
    r"(?i)(password|token|authorization|secret|api_key)\s*[=:]\s*(?:bearer\s+)?\S+",
)

# Set by RequestIDMiddleware; lets every log line emitted while serving a request carry its id.
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
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
        request_id = getattr(record, "request_id", None) or request_id_var.get()
        if request_id:
            log_entry["request_id"] = request_id
        # django.request attaches the HttpRequest and status_code to 4xx/5xx records
        request = getattr(record, "request", None)
        if hasattr(request, "path"):
            log_entry["method"] = request.method
            log_entry["path"] = request.path
        if hasattr(record, "status_code"):
            log_entry["status"] = record.status_code
        for field in ("user_id", "path", "method", "status"):
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        return json.dumps(log_entry)
