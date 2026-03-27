import json
import logging


def configure_logger(name, level="INFO"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    logger.propagate = False
    return logger


def log_event(logger, level, event, **fields):
    payload = {"event": event, **fields}
    getattr(logger, level.lower())(json.dumps(payload, default=str, sort_keys=True))
