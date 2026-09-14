"""Useful local failure locations without provider text, payloads or private paths."""

import logging
import traceback
from pathlib import Path

logger = logging.getLogger("concept_to_code_learning")


def report_error(stage, error):
    frames = traceback.extract_tb(error.__traceback__)
    locations = " > ".join(f"{Path(f.filename).name}:{f.lineno}:{f.name}" for f in frames[-8:])
    logger.error("%s: %s at %s", stage, type(error).__name__, locations or "unknown")
