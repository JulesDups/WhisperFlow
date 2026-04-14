"""
WhisperFlow UI — Widgets
Composants isolés et réutilisables, stylés via theme + styles QSS.
"""

from .gpu_gauge import GpuGauge
from .level_meter import LevelMeter
from .menu_button import MenuButton
from .source_toggle import SourceMode, SourceToggle
from .stats_strip import StatsStrip
from .status_bar import AppState, StatusBar
from .transcript_view import TranscriptState, TranscriptView
from .url_panel import UrlPanel

__all__ = [
    "AppState",
    "GpuGauge",
    "LevelMeter",
    "MenuButton",
    "SourceMode",
    "SourceToggle",
    "StatsStrip",
    "StatusBar",
    "TranscriptState",
    "TranscriptView",
    "UrlPanel",
]
