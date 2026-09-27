import json
import logging

from apps.common.logging import JsonFormatter, SensitiveDataFilter, request_id_var


def _record(msg, **extra):
    record = logging.LogRecord("t", logging.WARNING, __file__, 1, msg, None, None)
    record.__dict__.update(extra)
    return record


def test_json_log_carries_request_id_from_context():
    request_id_var.set("req-123")
    entry = json.loads(JsonFormatter().format(_record("hello", status_code=401)))
    assert entry["request_id"] == "req-123"
    assert entry["status"] == 401


def test_bearer_token_fully_redacted():
    record = _record("authorization: Bearer abc.def.ghi")
    SensitiveDataFilter().filter(record)
    assert "abc" not in record.msg
