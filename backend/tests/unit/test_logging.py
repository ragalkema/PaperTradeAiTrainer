"""Structured logging tests."""

import json
import logging

from app.core.logging import JsonFormatter


def test_json_formatter_escapes_messages() -> None:
    record = logging.LogRecord(
        name="paper-trading",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg='paper_order_created "virtual"',
        args=(),
        exc_info=None,
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["message"] == 'paper_order_created "virtual"'
