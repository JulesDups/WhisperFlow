"""
StatsStrip — 3 colonnes de métriques temps réel.

  GPU              MODEL            SESSION
  4.2 / 16.0 GB    turbo · fr       12 clips
  [▇▇░░░░] 26%     RTF 0.031        1,847 words
  IDLE             LIVE             ~18 min saved

Compose un GpuGauge + 2 sous-widgets (ModelCard, SessionCard) alignés.
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .. import theme
from .gpu_gauge import GpuGauge


@dataclass(slots=True)
class SessionStats:
    """Statistiques agrégées de la session."""

    clips: int = 0
    total_words: int = 0
    total_audio_duration_s: float = 0.0  # somme des durées transcrites
    total_processing_time_s: float = 0.0  # somme des temps de traitement

    @property
    def rtf(self) -> float:
        """Real-Time Factor moyen (processing_time / audio_duration)."""
        if self.total_audio_duration_s <= 0:
            return 0.0
        return self.total_processing_time_s / self.total_audio_duration_s

    @property
    def time_saved_min(self) -> float:
        """
        Estimation du temps gagné vs frappe clavier.
        Hypothèse : un humain tape à ~200 mots/min, parle à ~150 mots/min.
        Le gain réel vient du différentiel tape vs parle + correction.
        On utilise une approximation conservative : temps gagné ≈ mots / 40 (min).
        """
        return self.total_words / 40.0


class _MetricCard(QFrame):
    """Une carte métrique : eyebrow + valeur principale + 2 lignes de hints."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("metricCard")

        root = QVBoxLayout(self)
        root.setContentsMargins(theme.SPACE_3, theme.SPACE_3, theme.SPACE_3, theme.SPACE_3)
        root.setSpacing(theme.SPACE_1)

        self._eyebrow = QLabel(title)
        self._eyebrow.setObjectName("eyebrow")
        root.addWidget(self._eyebrow)

        self._value = QLabel("—")
        self._value.setObjectName("metricValue")
        root.addWidget(self._value)

        self._hint1 = QLabel("")
        self._hint1.setObjectName("metricHint")
        root.addWidget(self._hint1)

        self._hint2 = QLabel("")
        self._hint2.setObjectName("metricHint")
        root.addWidget(self._hint2)

        root.addStretch()

    def set_value(self, value: str) -> None:
        self._value.setText(value)

    def set_hints(self, hint1: str = "", hint2: str = "") -> None:
        self._hint1.setText(hint1)
        self._hint2.setText(hint2)


class StatsStrip(QWidget):
    """
    Strip horizontale : GPU | MODEL | SESSION.

    Chaque colonne est une carte bordée subtile. L'ensemble est un bloc unique
    avec eyebrow "METRICS" au-dessus.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statsStrip")
        self._session = SessionStats()
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(theme.SPACE_2)

        # Eyebrow section header
        header = QLabel("METRICS")
        header.setObjectName("sectionHeader")
        root.addWidget(header)

        # Row of 3 cards
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.SPACE_2)

        # 1. GPU card (has its own internal layout via GpuGauge)
        self._gpu_card = _GpuCardWrapper()
        row.addWidget(self._gpu_card, 1)

        # 2. Model card
        self._model_card = _MetricCard("MODEL")
        self._model_card.set_value("turbo")
        self._model_card.set_hints("RTF —", "—")
        row.addWidget(self._model_card, 1)

        # 3. Session card
        self._session_card = _MetricCard("SESSION")
        self._session_card.set_value("0 clips")
        self._session_card.set_hints("0 words", "~0 min saved")
        row.addWidget(self._session_card, 1)

        root.addLayout(row)

    # ---- API ----

    @property
    def gpu_gauge(self) -> GpuGauge:
        return self._gpu_card.gauge

    def set_model_info(self, model_id: str, language: str | None = None) -> None:
        label = model_id if language is None else f"{model_id} · {language}"
        self._model_card.set_value(label)

    def set_model_status(self, rtf: float | None, is_live: bool) -> None:
        rtf_text = f"RTF {rtf:.3f}" if rtf is not None and rtf > 0 else "RTF —"
        state = " LIVE" if is_live else " IDLE"
        self._model_card.set_hints(rtf_text, state)

    def record_transcription(self, text: str, audio_duration_s: float, processing_time_s: float) -> None:
        """Incrémente les stats de session depuis un résultat de transcription."""
        self._session.clips += 1
        self._session.total_words += len(text.split())
        self._session.total_audio_duration_s += audio_duration_s
        self._session.total_processing_time_s += processing_time_s
        self._refresh_session()
        self.set_model_status(self._session.rtf, False)

    def _refresh_session(self) -> None:
        s = self._session
        self._session_card.set_value(f"{s.clips} clip{'s' if s.clips != 1 else ''}")
        words_fmt = f"{s.total_words:,}".replace(",", " ")
        self._session_card.set_hints(
            f"{words_fmt} words",
            f"~{s.time_saved_min:.0f} min saved",
        )


class _GpuCardWrapper(QFrame):
    """Wrap GpuGauge dans un QFrame pour avoir la même apparence de carte."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.SPACE_3, theme.SPACE_3, theme.SPACE_3, theme.SPACE_3)
        layout.setSpacing(0)

        self.gauge = GpuGauge(self)
        layout.addWidget(self.gauge, 0, Qt.AlignmentFlag.AlignTop)
        layout.addStretch()
