"""
Parser package for screenplay analysis.

Vendored from ScreenPy with relative imports.
"""

from .core import ScreenplayParser
from .shot_parser import ShotHeadingParser
from .time_parser import TimeParser

__all__ = [
    "ScreenplayParser",
    "ShotHeadingParser",
    "TimeParser",
]
