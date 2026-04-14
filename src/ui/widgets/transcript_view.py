"""
TranscriptView — zone de résultat avec 3 states (empty / result / error).

- Empty state : message guide avec hotkey hint
- Result state : texte transcrit sélectionnable + badge langue/confidence +
  toggle `TEXT | TIMED` (visible si segments dispo, chemin URL)
- Error state : message + bouton Retry (émet retry_requested)

Le texte est toujours sélectionnable à la souris (QTextEdit read-only).
"""

from __future__ import annotations

from enum import Enum

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor, QTextOption
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...i18n import t
from ...transcription_service import TranscriptSegment
from .. import theme


class TranscriptState(Enum):
    EMPTY = "empty"
    RESULT = "result"
    ERROR = "error"


class RenderMode(Enum):
    FLAT = "flat"  # Texte brut à plat
    TIMED = "timed"  # Segments horodatés [MM:SS]


def _format_short_timecode(seconds: float) -> str:
    """[MM:SS] format compact — HH:MM:SS au-delà d'une heure."""
    if seconds < 0:
        seconds = 0.0
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class TranscriptView(QWidget):
    """
    Vue transcript avec header (badge langue + toggle render) + corps empilé.

    Signaux :
      - copy_requested : l'utilisateur veut copier le contenu actuel
      - retry_requested : l'utilisateur veut retenter l'action précédente
    """

    copy_requested = pyqtSignal()
    retry_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("transcriptView")
        self._state = TranscriptState.EMPTY
        self._last_text = ""
        self._segments: tuple[TranscriptSegment, ...] = ()
        self._render_mode = RenderMode.FLAT
        self._build_ui()
        self.set_state(TranscriptState.EMPTY)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(theme.SPACE_2)

        # Header row : eyebrow + render toggle + language badge
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(theme.SPACE_2)

        self._header_label = QLabel(t("transcript_eyebrow"))
        self._header_label.setObjectName("sectionHeader")
        header.addWidget(self._header_label)

        header.addStretch()

        # Segmented TEXT | TIMED toggle (masqué si pas de segments)
        self._btn_flat = QPushButton(t("transcript_mode_text"))
        self._btn_flat.setObjectName("renderToggleBtn")
        self._btn_flat.setProperty("segment", "left")
        self._btn_flat.setCheckable(True)
        self._btn_flat.setChecked(True)
        self._btn_flat.clicked.connect(lambda: self._set_render_mode(RenderMode.FLAT))
        header.addWidget(self._btn_flat)

        self._btn_timed = QPushButton(t("transcript_mode_timed"))
        self._btn_timed.setObjectName("renderToggleBtn")
        self._btn_timed.setProperty("segment", "right")
        self._btn_timed.setCheckable(True)
        self._btn_timed.clicked.connect(lambda: self._set_render_mode(RenderMode.TIMED))
        header.addWidget(self._btn_timed)

        self._btn_flat.hide()
        self._btn_timed.hide()

        self._lang_badge = QLabel("")
        self._lang_badge.setObjectName("langBadge")
        self._lang_badge.hide()
        header.addWidget(self._lang_badge)

        root.addLayout(header)

        # Body : stacked layout for the 3 states
        self._body = QWidget()
        self._body.setObjectName("transcriptBody")
        self._body.setMinimumHeight(200)
        self._body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._stack = QStackedLayout(self._body)
        self._stack.setContentsMargins(theme.SPACE_4, theme.SPACE_4, theme.SPACE_4, theme.SPACE_4)
        root.addWidget(self._body, 1)

        # Empty state
        self._empty_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.setSpacing(theme.SPACE_2)
        empty_layout.addStretch()
        self._empty_title = QLabel(t("transcript_empty_title"))
        self._empty_title.setObjectName("emptyTitle")
        self._empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._empty_title)
        self._empty_hint = QLabel(t("transcript_empty_hint"))
        self._empty_hint.setObjectName("emptyHint")
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hint.setWordWrap(True)
        empty_layout.addWidget(self._empty_hint)
        empty_layout.addStretch()
        self._stack.addWidget(self._empty_widget)

        # Result state — QTextEdit read-only (texte sélectionnable)
        self._text = QTextEdit()
        self._text.setObjectName("transcriptText")
        self._text.setReadOnly(True)
        self._text.setFrameStyle(0)
        self._text.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self._text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._stack.addWidget(self._text)

        # Error state
        self._error_widget = QWidget()
        err_layout = QVBoxLayout(self._error_widget)
        err_layout.setContentsMargins(0, 0, 0, 0)
        err_layout.setSpacing(theme.SPACE_3)
        err_layout.addStretch()
        self._error_title = QLabel(t("transcript_error_title"))
        self._error_title.setObjectName("errorTitle")
        self._error_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        err_layout.addWidget(self._error_title)
        self._error_detail = QLabel("")
        self._error_detail.setObjectName("errorDetail")
        self._error_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_detail.setWordWrap(True)
        err_layout.addWidget(self._error_detail)
        self._retry_btn = QPushButton(t("btn_retry"))
        self._retry_btn.setObjectName("retryBtn")
        self._retry_btn.setFixedWidth(120)
        self._retry_btn.clicked.connect(self.retry_requested.emit)
        retry_row = QHBoxLayout()
        retry_row.addStretch()
        retry_row.addWidget(self._retry_btn)
        retry_row.addStretch()
        err_layout.addLayout(retry_row)
        err_layout.addStretch()
        self._stack.addWidget(self._error_widget)

    # ---- API ----

    def set_state(self, state: TranscriptState) -> None:
        self._state = state
        index = {
            TranscriptState.EMPTY: 0,
            TranscriptState.RESULT: 1,
            TranscriptState.ERROR: 2,
        }[state]
        self._stack.setCurrentIndex(index)
        if state != TranscriptState.RESULT:
            self._lang_badge.hide()
            self._btn_flat.hide()
            self._btn_timed.hide()

    def set_result(
        self,
        text: str,
        language: str | None = None,
        confidence: float | None = None,
        segments: tuple[TranscriptSegment, ...] | None = None,
    ) -> None:
        """
        Affiche le résultat final.

        Si `segments` est fourni (et non vide), le toggle TEXT/TIMED devient
        visible et l'utilisateur peut basculer entre texte à plat et version
        horodatée. Sans segments, le toggle reste masqué.
        """
        self._last_text = text
        self._segments = tuple(segments or ())

        # Affichage du toggle selon la disponibilité des segments
        if self._segments:
            self._btn_flat.show()
            self._btn_timed.show()
        else:
            self._btn_flat.hide()
            self._btn_timed.hide()
            self._render_mode = RenderMode.FLAT

        self._render_current()

        if language:
            if confidence is not None and confidence > 0:
                self._lang_badge.setText(
                    t("transcript_language_confidence", language=language.upper(), confidence=int(confidence * 100))
                )
            else:
                self._lang_badge.setText(language.upper())
            self._lang_badge.show()
        else:
            self._lang_badge.hide()

        self.set_state(TranscriptState.RESULT)

    def set_error(self, message: str) -> None:
        self._error_detail.setText(message)
        self.set_state(TranscriptState.ERROR)

    def set_empty_hint(self, hint: str) -> None:
        self._empty_hint.setText(hint)

    def current_text(self) -> str:
        """Retourne le texte actuellement visible (flat ou timed)."""
        return self._text.toPlainText() if self._state == TranscriptState.RESULT else self._last_text

    @property
    def state(self) -> TranscriptState:
        return self._state

    # ---- internals ----

    def _set_render_mode(self, mode: RenderMode) -> None:
        if mode == self._render_mode:
            self._sync_toggle_buttons()
            return
        self._render_mode = mode
        self._sync_toggle_buttons()
        if self._state == TranscriptState.RESULT:
            self._render_current()

    def _sync_toggle_buttons(self) -> None:
        self._btn_flat.setChecked(self._render_mode == RenderMode.FLAT)
        self._btn_timed.setChecked(self._render_mode == RenderMode.TIMED)
        for btn in (self._btn_flat, self._btn_timed):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _render_current(self) -> None:
        """Re-render le contenu du QTextEdit selon le mode actif."""
        if self._render_mode == RenderMode.TIMED and self._segments:
            lines = [f"[{_format_short_timecode(seg.start)}]  {seg.text}" for seg in self._segments]
            content = "\n".join(lines)
        else:
            content = self._last_text

        self._text.setPlainText(content)
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self._text.setTextCursor(cursor)
