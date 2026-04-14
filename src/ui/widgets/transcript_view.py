"""
TranscriptView — zone de résultat avec 3 states (empty / result / error).

- Empty state : message guide avec hotkey hint
- Result state : texte transcrit sélectionnable + badge langue/confidence
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
    QStackedLayout,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import theme


class TranscriptState(Enum):
    EMPTY = "empty"
    RESULT = "result"
    ERROR = "error"


class TranscriptView(QWidget):
    """
    Vue transcript avec header (badge langue) + corps empilé (3 states).

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
        self._build_ui()
        self.set_state(TranscriptState.EMPTY)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(theme.SPACE_2)

        # Header row : eyebrow + language badge
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(theme.SPACE_2)

        self._header_label = QLabel("TRANSCRIPT")
        self._header_label.setObjectName("sectionHeader")
        header.addWidget(self._header_label)

        header.addStretch()

        self._lang_badge = QLabel("")
        self._lang_badge.setObjectName("langBadge")
        self._lang_badge.hide()
        header.addWidget(self._lang_badge)

        root.addLayout(header)

        # Body : stacked layout for the 3 states
        self._body = QWidget()
        self._body.setObjectName("transcriptBody")
        self._stack = QStackedLayout(self._body)
        self._stack.setContentsMargins(theme.SPACE_4, theme.SPACE_4, theme.SPACE_4, theme.SPACE_4)
        root.addWidget(self._body, 1)

        # Empty state
        self._empty_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.setSpacing(theme.SPACE_2)
        empty_layout.addStretch()
        self._empty_title = QLabel("Ready to capture")
        self._empty_title.setObjectName("emptyTitle")
        self._empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._empty_title)
        self._empty_hint = QLabel("Hold F2 to speak, or paste a video URL below.")
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
        self._error_title = QLabel("Something went wrong")
        self._error_title.setObjectName("errorTitle")
        self._error_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        err_layout.addWidget(self._error_title)
        self._error_detail = QLabel("")
        self._error_detail.setObjectName("errorDetail")
        self._error_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_detail.setWordWrap(True)
        err_layout.addWidget(self._error_detail)
        self._retry_btn = QPushButton("Retry")
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

    def set_result(self, text: str, language: str | None = None, confidence: float | None = None) -> None:
        self._last_text = text
        self._text.setPlainText(text)
        # Auto-scroll to top pour voir le début
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self._text.setTextCursor(cursor)

        if language:
            if confidence is not None and confidence > 0:
                self._lang_badge.setText(f"{language.upper()} · {confidence * 100:.0f}%")
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
        return self._last_text

    @property
    def state(self) -> TranscriptState:
        return self._state
