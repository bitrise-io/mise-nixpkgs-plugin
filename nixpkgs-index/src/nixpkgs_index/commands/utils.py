"""Shared utilities for CLI commands."""

import logging
import sys
from datetime import timedelta

import colorlog


def setup_logging(verbosity: int) -> None:
    """Configure logging based on verbosity level."""
    if verbosity >= 1:
        level = logging.DEBUG
    else:
        level = logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    formatter = colorlog.ColoredFormatter(
        fmt="%(log_color)s%(asctime)s [%(levelname)s]%(reset)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
    handler.setFormatter(formatter)

    root_logger.handlers.clear()
    root_logger.addHandler(handler)


def parse_interval(interval_str: str) -> timedelta:
    """Parse interval strings like '1h', '6h', '1d', '7d', '30d'."""
    if not interval_str:
        raise ValueError("Interval string cannot be empty")

    unit = interval_str[-1]
    try:
        amount = int(interval_str[:-1])
    except ValueError:
        raise ValueError(f"Invalid interval format: {interval_str}")

    if unit == "h":
        return timedelta(hours=amount)
    elif unit == "d":
        return timedelta(days=amount)
    else:
        raise ValueError(
            f"Unknown interval unit: {unit}. Supported units: h (hours), d (days)"
        )
