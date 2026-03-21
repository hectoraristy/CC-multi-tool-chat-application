"""Centralized logging configuration.

Call ``setup_logging()`` once at application startup (e.g. inside the
FastAPI lifespan) to apply a consistent format and level across all
modules that use ``logging.getLogger(__name__)``.
"""

from __future__ import annotations

import logging
import sys

from config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        stream=sys.stdout,
        force=True,
    )
