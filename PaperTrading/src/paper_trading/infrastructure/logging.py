"""Safe structured application logging."""

import json
import logging
from logging.config import dictConfig


class JsonFormatter(logging.Formatter):
    """Serialize common, non-secret log fields as valid JSON."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            },
            ensure_ascii=False,
        )


def configure_logging(level: str) -> None:
    """Configure JSON logging without serializing settings or credentials."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "paper_trading.infrastructure.logging.JsonFormatter",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                }
            },
            "handlers": {"default": {"class": "logging.StreamHandler", "formatter": "json"}},
            "root": {"handlers": ["default"], "level": level.upper()},
        }
    )
    logging.captureWarnings(True)
