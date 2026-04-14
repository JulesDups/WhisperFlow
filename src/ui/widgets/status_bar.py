"""
StatusBar — ligne d'état unique et source de vérité pour l'état de l'app.

Un point lumineux pulsé + un label de statut. Remplace l'ancien status_label
et l'ancienne titlebar status. Pas de doublon, pas de décor.
"""

from __future__ import annotations

from enum import Enum

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPaintEvent
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ...i18n import t
from .. import theme


class AppState(Enum):
    """États sémantiques de l'application."""

    LOADING = "loading"
    READY = "ready"
    RECORDING = "recording"
    PROCESSING = "processing"
    ERROR = "error"


_STATE_COLORS: dict[AppState, str] = {
    AppState.LOADING: theme.GOLD,
    AppState.READY: theme.GOLD,
    AppState.RECORDING: theme.RUST,
    AppState.PROCESSING: theme.GOLD,
    AppState.ERROR: theme.RUST,
}


class _Indicator(QWidget):
    """Point lumineux circulaire avec halo et animation de pulsation."""

    DIAMETER = 10
    HALO = 20

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self.HALO, self.HALO)
        self._state = AppState.LOADING
        self._pulse_phase = 0.0
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(40)
        self._pulse_timer.timeout.connect(self._tick)
        self._pulse_timer.start()

    def set_state(self, state: AppState) -> None:
        self._state = state
        self.update()

    def _tick(self) -> None:
        # Phase 0→1 cyclique pour toute l'animation (vitesse variable selon l'état)
        step = 0.04 if self._state in (AppState.RECORDING, AppState.PROCESSING, AppState.LOADING) else 0.015
        self._pulse_phase = (self._pulse_phase + step) % 1.0
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        base_color = QColor(_STATE_COLORS[self._state])

        # Halo pulsé (fort sur states actifs, discret sur ready/error)
        if self._state in (AppState.RECORDING, AppState.PROCESSING, AppState.LOADING):
            # Pulse large qui respire
            import math

            t = (math.sin(self._pulse_phase * 2 * math.pi) + 1) / 2  # 0→1
            halo_alpha = 0.08 + t * 0.32
            halo_radius = self.HALO / 2 * (0.7 + t * 0.3)
        else:
            halo_alpha = 0.18
            halo_radius = self.HALO / 2 * 0.75

        halo_color = QColor(base_color)
        halo_color.setAlphaF(halo_alpha)
        painter.setBrush(QBrush(halo_color))
        painter.setPen(Qt.PenStyle.NoPen)
        cx = self.HALO / 2
        cy = self.HALO / 2
        painter.drawEllipse(
            int(cx - halo_radius),
            int(cy - halo_radius),
            int(halo_radius * 2),
            int(halo_radius * 2),
        )

        # Dot central plein
        painter.setBrush(QBrush(base_color))
        painter.drawEllipse(
            int(cx - self.DIAMETER / 2),
            int(cy - self.DIAMETER / 2),
            self.DIAMETER,
            self.DIAMETER,
        )


class StatusBar(QWidget):
    """
    Status bar : [● indicator] STATE_LABEL

    - Eyebrow mono ("STATUS") + label display (état)
    - Transient messages (success/error toasts via status_label)
    """

    state_changed = pyqtSignal(AppState)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBar")
        self._state = AppState.LOADING
        self._transient_timer = QTimer(self)
        self._transient_timer.setSingleShot(True)
        self._transient_timer.timeout.connect(self._restore_state_label)

        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(theme.SPACE_3)

        self._indicator = _Indicator(self)
        root.addWidget(self._indicator, 0, Qt.AlignmentFlag.AlignVCenter)

        self._label = QLabel(t("status_loading"))
        self._label.setObjectName("statusBarLabel")
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(self._label, 1)

        root.addStretch()

    # ---- API publique ----

    def set_state(self, state: AppState, hotkey_hint: str = "") -> None:
        self._state = state
        self._indicator.set_state(state)
        self._label.setText(self._default_text(state, hotkey_hint))
        self._label.setProperty("state", state.value)
        self._label.style().unpolish(self._label)
        self._label.style().polish(self._label)
        self.state_changed.emit(state)

    def show_transient(self, text: str, duration_ms: int = 2200) -> None:
        """Affiche un message temporaire (toast) qui se remplace par l'état courant."""
        self._label.setText(text)
        self._transient_timer.start(duration_ms)

    # ---- internals ----

    def _restore_state_label(self) -> None:
        self._label.setText(self._default_text(self._state, ""))

    def _default_text(self, state: AppState, hotkey_hint: str) -> str:
        if state == AppState.LOADING:
            return t("status_loading")
        if state == AppState.READY:
            return t("status_ready_hotkey", hotkey_hint=hotkey_hint) if hotkey_hint else t("status_ready")
        if state == AppState.RECORDING:
            return t("status_recording")
        if state == AppState.PROCESSING:
            return t("status_transcribing")
        if state == AppState.ERROR:
            return t("status_error")
        return ""

    @property
    def state(self) -> AppState:
        return self._state
