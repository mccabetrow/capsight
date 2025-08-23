"""
Structured logging configuration for CapSight.
"""

import logging
import logging.config
import sys
from typing import Any, Dict

from app.core.config import settings


def setup_logging() -> None:
    """Setup structured logging configuration."""
    
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    if settings.LOG_FORMAT == "json":
        # JSON structured logging for production
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d}',
                    "datefmt": "%Y-%m-%dT%H:%M:%S"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": "json",
                    "stream": "ext://sys.stdout"
                }
            },
            "loggers": {
                "": {
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False
                },
                "app": {
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False
                },
                "uvicorn": {
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False
                },
                "sqlalchemy": {
                    "level": "WARNING",
                    "handlers": ["console"],
                    "propagate": False
                }
            }
        }
    else:
        # Human-readable logging for development
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": "standard",
                    "stream": "ext://sys.stdout"
                }
            },
            "loggers": {
                "": {
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False
                },
                "app": {
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False
                },
                "uvicorn": {
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False
                },
                "sqlalchemy": {
                    "level": "WARNING",
                    "handlers": ["console"],
                    "propagate": False
                }
            }
        }
    
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)
