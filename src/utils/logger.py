"""
WhisperFlow Desktop - Logging Configuration
Configuration centralisee du logging pour toute l'application
"""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure le logging pour l'application WhisperFlow"""
    fmt = "%(asctime)s %(levelname)-5s [%(name)s] %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
