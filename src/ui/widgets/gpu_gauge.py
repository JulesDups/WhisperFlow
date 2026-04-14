"""
GpuGauge — utilisation VRAM temps réel, hooké sur TranscriptionService.get_vram_usage().

Labels :
  GPU                     4.2 / 16.0 GB
  [▇▇▇▇░░░░░░░░░░░░]      26%
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter, QPaintEvent
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ...transcription_service import TranscriptionService
from .. import theme


class _BarTrack(QWidget):
    """Track horizontal rempli selon ratio. Couleur gold par défaut, rust en critique."""

    HEIGHT = 6
    WARN_THRESHOLD = 0.75
    CRITICAL_THRESHOLD = 0.92

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ratio = 0.0
        self.setFixedHeight(self.HEIGHT)
        self.setMinimumWidth(80)

    def set_ratio(self, ratio: float) -> None:
        self._ratio = max(0.0, min(1.0, ratio))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Track background
        track = QColor(theme.CONTRAST_HEX)
        track.setAlphaF(0.10)
        p.setBrush(QBrush(track))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, h / 2, h / 2)

        if self._ratio <= 0:
            return

        # Fill
        if self._ratio >= self.CRITICAL_THRESHOLD:
            fill_color = QColor(theme.RUST)
        elif self._ratio >= self.WARN_THRESHOLD:
            fill_color = QColor(theme.GOLD)
            fill_color.setAlphaF(0.85)
        else:
            fill_color = QColor(theme.GOLD)

        fill_w = int(w * self._ratio)
        p.setBrush(QBrush(fill_color))
        p.drawRoundedRect(0, 0, fill_w, h, h / 2, h / 2)


class GpuGauge(QWidget):
    """
    Carte GPU avec eyebrow, usage mémoire texte, bargraph et pourcentage.
    Polling régulier de TranscriptionService.get_vram_usage().
    """

    POLL_INTERVAL_MS = 2000

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("gpuGauge")
        self._has_gpu = False
        self._build_ui()
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(self.POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self.refresh)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(theme.SPACE_1)

        self._eyebrow = QLabel("GPU")
        self._eyebrow.setObjectName("eyebrow")
        root.addWidget(self._eyebrow)

        self._value = QLabel("—")
        self._value.setObjectName("metricValue")
        root.addWidget(self._value)

        self._bar = _BarTrack(self)
        root.addWidget(self._bar)

        self._percent = QLabel("")
        self._percent.setObjectName("metricHint")
        root.addWidget(self._percent)

    def start_polling(self) -> None:
        self.refresh()
        self._poll_timer.start()

    def stop_polling(self) -> None:
        self._poll_timer.stop()

    def refresh(self) -> None:
        used, total, pct = TranscriptionService.get_vram_usage()
        if total <= 0:
            self._value.setText("N/A")
            self._bar.set_ratio(0.0)
            self._percent.setText("No CUDA device")
            self._has_gpu = False
            return

        self._has_gpu = True
        self._value.setText(f"{used:.1f} / {total:.1f} GB")
        ratio = used / total
        self._bar.set_ratio(ratio)
        status = " LIVE" if ratio > 0.01 else " IDLE"
        self._percent.setText(f"{pct:.0f}%{status}")
