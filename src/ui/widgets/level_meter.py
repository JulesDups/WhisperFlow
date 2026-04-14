"""
LevelMeter — niveau audio en temps réel avec readout en dB.

20 barres verticales + chiffre dB à droite. Couleur gold jusqu'à -6dB,
rust au-delà (clipping warning).
"""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter, QPaintEvent
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from .. import theme


class _Bars(QWidget):
    """Bargraph horizontal 20 segments, smoothing exponentiel + peak hold."""

    NUM_BARS = 20
    BAR_WIDTH = 4
    BAR_GAP = 2
    BAR_HEIGHT = 18
    SMOOTHING = 0.35  # 0 = pas de lissage, 1 = gel
    PEAK_DECAY = 0.015  # baisse du peak hold par tick
    CLIP_THRESHOLD = 0.89  # ≈ -1 dBFS

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._level: float = 0.0
        self._smoothed: float = 0.0
        self._peak: float = 0.0
        self._recording = False

        w = self.NUM_BARS * (self.BAR_WIDTH + self.BAR_GAP) - self.BAR_GAP
        self.setFixedSize(w, self.BAR_HEIGHT)

        self._decay_timer = QTimer(self)
        self._decay_timer.setInterval(40)
        self._decay_timer.timeout.connect(self._decay_tick)
        self._decay_timer.start()

    def set_level(self, level: float) -> None:
        self._level = max(0.0, min(1.0, level))
        # smoothing exponentiel (attaque rapide, release lente via decay)
        if self._level > self._smoothed:
            self._smoothed = self._level  # attaque instantanée
        # peak hold
        if self._level > self._peak:
            self._peak = self._level
        self.update()

    def set_recording(self, recording: bool) -> None:
        self._recording = recording
        if not recording:
            self._smoothed *= 0.5
        self.update()

    def _decay_tick(self) -> None:
        # Release progressif
        self._smoothed *= 1.0 - self.SMOOTHING * 0.5
        if self._smoothed < 0.002:
            self._smoothed = 0.0
        self._peak = max(0.0, self._peak - self.PEAK_DECAY)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        lit_bars = int(self._smoothed * self.NUM_BARS + 0.5)
        peak_bar = int(self._peak * self.NUM_BARS + 0.5)

        gold_lit = QColor(theme.GOLD)
        gold_dim = QColor(theme.CONTRAST_HEX)
        gold_dim.setAlphaF(0.12)
        rust_lit = QColor(theme.RUST)
        cream_peak = QColor(theme.CONTRAST_HEX)
        cream_peak.setAlphaF(0.55)

        for i in range(self.NUM_BARS):
            x = i * (self.BAR_WIDTH + self.BAR_GAP)
            # Seuil rouge sur les 2 dernières barres (clipping)
            is_clip_zone = i >= self.NUM_BARS - 2

            if i < lit_bars:
                color = rust_lit if is_clip_zone and self._smoothed >= self.CLIP_THRESHOLD else gold_lit
            elif i == peak_bar - 1 and peak_bar > lit_bars:
                color = cream_peak
            else:
                color = gold_dim

            p.fillRect(x, 0, self.BAR_WIDTH, self.BAR_HEIGHT, QBrush(color))


class LevelMeter(QWidget):
    """
    Widget complet : barres + readout dB + état recording.

    API :
      - set_level(float 0-1)
      - set_recording(bool)
    """

    MIN_DB = -60.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("levelMeter")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(theme.SPACE_3)

        self._bars = _Bars(self)
        root.addWidget(self._bars, 0, Qt.AlignmentFlag.AlignVCenter)

        self._db_label = QLabel("−∞ dB")
        self._db_label.setObjectName("levelMeterDb")
        self._db_label.setMinimumWidth(64)
        self._db_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(self._db_label, 0)

        root.addStretch()

    def set_level(self, level: float) -> None:
        self._bars.set_level(level)
        self._db_label.setText(self._format_db(level))

    def set_recording(self, recording: bool) -> None:
        self._bars.set_recording(recording)
        if not recording:
            self._db_label.setText("−∞ dB")

    @classmethod
    def _format_db(cls, level: float) -> str:
        if level <= 1e-5:
            return "−∞ dB"
        db = 20.0 * math.log10(level)
        if db < cls.MIN_DB:
            return "−∞ dB"
        return f"{db:+.0f} dB"
