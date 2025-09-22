import json
import logging
from datetime import datetime
from logging.config import dictConfig


# Custom JSON formatter
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Add exception info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def initialize_logging():
    # Define the logging configuration
    global log_config
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"json": {"()": JsonFormatter}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "json",
                "stream": "ext://sys.stdout",
            },
            "rotating_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": "app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "loggers": {
            "app": {
                "handlers": ["console", "rotating_file"],
                "level": "DEBUG",
                "propagate": False,
            },
        },
        "root": {"handlers": ["console"], "level": "DEBUG"},
    }

    # Apply the configuration
    dictConfig(log_config)
