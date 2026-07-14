"""Application-wide logging setup."""
import logging
from logging.handlers import RotatingFileHandler

from config import LOG_DIR

_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger (file + console). Idempotent."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fh = RotatingFileHandler(LOG_DIR / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(logging.Formatter(_FMT))
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(_FMT))
    logger.addHandler(ch)

    logger.propagate = False
    return logger
