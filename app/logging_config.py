import contextlib
import json
import logging
from copy import deepcopy
from logging import config
from typing import Any

from pythonjsonlogger.orjson import OrjsonFormatter


class JsonBodyFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, "body"):
            with contextlib.suppress(ValueError, TypeError):
                record.body = json.loads(record.body)
        return True


class IgnoreExcludedPathsFilter(logging.Filter):
    excluded_log_paths = {
        "GET /metrics",
        "GET /healthz",
        "GET /livez",
    }

    def filter(self, record):
        message = record.getMessage()
        return not any(path in message for path in self.excluded_log_paths)


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        from app.core.request_context import get_request_id

        if request_id := get_request_id():
            record.request_id = request_id
        return True


class IsoMsOrjsonFormatter(OrjsonFormatter):
    default_time_format = "%Y-%m-%dT%H:%M:%S"
    default_msec_format = "%s.%03d"


LOGGING_DICT: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "app.logging_config.IsoMsOrjsonFormatter",
            "format": "%(status_code)s %(path)s %(levelname)s %(asctime)s %(name)s %(message)s %(request_id)s",
        },
        "simple": {
            "()": "logging.Formatter",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "filters": {
        "ignore_excluded_paths": {
            "()": IgnoreExcludedPathsFilter,
        },
        "json_body": {
            "()": JsonBodyFilter,
        },
        "request_id": {
            "()": RequestIdFilter,
        },
    },
    "handlers": {
        "console": {
            "formatter": "json",
            "filters": ["ignore_excluded_paths", "json_body", "request_id"],
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "simple_console": {
            "formatter": "simple",
            "filters": [
                "ignore_excluded_paths",
                "request_id",
            ],
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {},
}


def configure_logging(
    root_log_level: str,
    logging_dict: dict[str, Any] | None = None,
    app_log_level_map: dict[str, str] | None = None,
    log_dev: bool = False,
) -> None:
    logging_dict = logging_dict or deepcopy(LOGGING_DICT)
    logging_config = deepcopy(logging_dict)

    handler_name = "simple_console" if log_dev else "console"

    if app_log_level_map:
        for app_name, log_level in app_log_level_map.items():
            if app_name not in logging_config["loggers"]:
                logging_config["loggers"][app_name] = {}
            logging_config["loggers"][app_name]["level"] = log_level
            logging_config["loggers"][app_name]["handlers"] = [handler_name]
            logging_config["loggers"][app_name]["propagate"] = False
    logging_config["root"] = {
        "level": root_log_level,
        "handlers": [handler_name],
    }

    config.dictConfig(logging_config)
    logging.captureWarnings(True)
