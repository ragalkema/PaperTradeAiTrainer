"""Structured JSON logging configuration."""

import logging
from logging.config import dictConfig


def configure_logging(level: str) -> None:
    """Configure JSON logs while leaving secret values out of log records."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "format": (
                        '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
                        '"logger":"%(name)s","message":"%(message)s"}'
                    )
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                }
            },
            "root": {"handlers": ["default"], "level": level.upper()},
        }
    )
    logging.captureWarnings(True)
