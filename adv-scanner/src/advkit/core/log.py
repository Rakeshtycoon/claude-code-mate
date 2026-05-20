"""Centralised logging for the advkit pipeline.

A single named logger (``advkit``) is shared by every module so that the
CLI can raise/lower verbosity in one place. Parser stages emit DEBUG-level
breadcrumbs that are invaluable when a real-world .adv file deviates from
the reverse-engineered layout.
"""
from __future__ import annotations

import logging
import sys

_LOGGER_NAME = "advkit"
_CONFIGURED = False


def get_logger(name: str | None = None) -> logging.Logger:
    """Return the shared ``advkit`` logger (or a child of it)."""
    base = logging.getLogger(_LOGGER_NAME)
    return base if name is None else base.getChild(name)


def configure(verbose: bool = False, quiet: bool = False) -> None:
    """Install a stderr handler. Safe to call more than once."""
    global _CONFIGURED
    logger = logging.getLogger(_LOGGER_NAME)
    if _CONFIGURED:
        level = logging.DEBUG if verbose else logging.WARNING if quiet else logging.INFO
        logger.setLevel(level)
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                           datefmt="%H:%M:%S")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else logging.WARNING if quiet else logging.INFO)
    _CONFIGURED = True
