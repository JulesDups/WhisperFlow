"""
SourceToggle — pill toggle entre MIC et URL.

Deux boutons segmentés, l'actif en gold, l'inactif en cream dim.
"""

from __future__ import annotations

from enum import Enum

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .. import theme


class SourceMode(Enum):
    MIC = "mic"
    URL = "url"


class SourceToggle(QWidget):
    """
    Toggle MIC / URL. Émet source_changed lorsque l'utilisateur bascule.
    """

    source_changed = pyqtSignal(SourceMode)

    def __init__(self, initial: SourceMode = SourceMode.MIC, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sourceToggle")
        self._mode = initial
        self._build_ui()
        self._apply_active()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(theme.SPACE_2)

        header = QLabel("SOURCE")
        header.setObjectName("sectionHeader")
        root.addWidget(header)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self._btn_mic = QPushButton("◉  MIC")
        self._btn_mic.setObjectName("sourceToggleBtn")
        self._btn_mic.setProperty("segment", "left")
        self._btn_mic.setCursor(self._btn_mic.cursor())
        self._btn_mic.setCheckable(True)
        self._btn_mic.clicked.connect(lambda: self.set_mode(SourceMode.MIC))
        row.addWidget(self._btn_mic, 1)

        self._btn_url = QPushButton("◯  URL")
        self._btn_url.setObjectName("sourceToggleBtn")
        self._btn_url.setProperty("segment", "right")
        self._btn_url.setCheckable(True)
        self._btn_url.clicked.connect(lambda: self.set_mode(SourceMode.URL))
        row.addWidget(self._btn_url, 1)

        root.addLayout(row)

    def set_mode(self, mode: SourceMode) -> None:
        if mode == self._mode:
            self._apply_active()
            return
        self._mode = mode
        self._apply_active()
        self.source_changed.emit(mode)

    def _apply_active(self) -> None:
        is_mic = self._mode == SourceMode.MIC
        self._btn_mic.setChecked(is_mic)
        self._btn_url.setChecked(not is_mic)
        self._btn_mic.setText("◉  MIC" if is_mic else "◯  MIC")
        self._btn_url.setText("◉  URL" if not is_mic else "◯  URL")
        # Force re-polish pour que QSS :checked s'applique
        for btn in (self._btn_mic, self._btn_url):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    @property
    def mode(self) -> SourceMode:
        return self._mode
