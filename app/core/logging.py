"""Centralized logging configuration for the application."""

import logging
import logging.config
import os
from contextvars import ContextVar
from pathlib import Path
from typing import Any

request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Inject per-request correlation id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()
        return True


def _build_logging_config(*, log_to_file: bool, log_file: str) -> dict[str, Any]:
    handlers: dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "filters": ["request_id"],
            "stream": "ext://sys.stdout",
        },
    }
    app_handlers = ["console"]
    if log_to_file:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filters": ["request_id"],
            "filename": log_file,
            "maxBytes": 10485760,
            "backupCount": 10,
        }
        app_handlers.append("file")

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - [req=%(request_id)s] - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": (
                    "%(asctime)s - %(name)s - %(levelname)s - [req=%(request_id)s] - "
                    "%(pathname)s:%(lineno)d - %(funcName)s() - %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "filters": {
            "request_id": {
                "()": "app.core.logging.RequestIdFilter",
            }
        },
        "handlers": handlers,
        "loggers": {
            "app": {
                "level": "DEBUG",
                "handlers": app_handlers,
                "propagate": False,
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
    }


def setup_logging() -> None:
    """Apply dictConfig and optionally create the rotating log directory."""
    log_to_file = os.environ.get("LOG_TO_FILE", "true").lower() in {"1", "true", "yes"}
    log_file = os.environ.get("LOG_FILE", "logs/app.log")

    if log_to_file:
        Path(log_file).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(
        _build_logging_config(log_to_file=log_to_file, log_file=log_file)
    )


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger under the 'app' hierarchy."""
    return logging.getLogger(name)
