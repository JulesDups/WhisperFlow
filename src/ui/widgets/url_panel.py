"""
UrlPanel — input URL + bouton submit + progress overlay.

Affiche aussi les métadonnées de la vidéo en cours (titre, durée) une fois
récupérées, et la progression DL → extraction → transcription.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import theme


class UrlPanel(QWidget):
    """
    Panel d'entrée URL vidéo.

    Signaux :
      - url_submitted(str) : l'utilisateur a cliqué GO ou tapé Enter
      - cancel_requested() : l'utilisateur veut annuler le job en cours
    """

    url_submitted = pyqtSignal(str)
    cancel_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("urlPanel")
        self._busy = False
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(theme.SPACE_2)

        # Input row
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.SPACE_2)

        self._input = QLineEdit()
        self._input.setObjectName("urlInput")
        self._input.setPlaceholderText("https://youtube.com/watch?v=…")
        self._input.setClearButtonEnabled(True)
        self._input.returnPressed.connect(self._on_submit)
        row.addWidget(self._input, 1)

        self._btn = QPushButton("GO")
        self._btn.setObjectName("urlSubmitBtn")
        self._btn.setFixedWidth(60)
        self._btn.clicked.connect(self._on_submit)
        row.addWidget(self._btn, 0)

        root.addLayout(row)

        # Meta line (hidden until metadata available)
        self._meta = QLabel("")
        self._meta.setObjectName("urlMeta")
        self._meta.setWordWrap(True)
        self._meta.hide()
        root.addWidget(self._meta)

        # Progress bar + status
        self._progress = QProgressBar()
        self._progress.setObjectName("urlProgress")
        self._progress.setRange(0, 100)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        self._progress.hide()
        root.addWidget(self._progress)

        self._progress_label = QLabel("")
        self._progress_label.setObjectName("urlProgressLabel")
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._progress_label.hide()
        root.addWidget(self._progress_label)

    # ---- API ----

    def set_visible_mode(self, visible: bool) -> None:
        """Affiche/masque le panel selon le mode source actif."""
        self.setVisible(visible)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._input.setEnabled(not busy)
        self._btn.setText("STOP" if busy else "GO")
        self._btn.setProperty("busy", busy)
        self._btn.style().unpolish(self._btn)
        self._btn.style().polish(self._btn)
        if busy:
            self._progress.show()
            self._progress_label.show()
            self._progress.setValue(0)
            self._progress_label.setText("Fetching…")
        else:
            self._progress.hide()
            self._progress_label.hide()

    def set_progress(self, message: str, ratio: float) -> None:
        self._progress.setValue(int(max(0.0, min(1.0, ratio)) * 100))
        self._progress_label.setText(message)

    def set_metadata(self, title: str, duration_s: float) -> None:
        mm = int(duration_s // 60)
        ss = int(duration_s % 60)
        self._meta.setText(f"{title}  ·  {mm}:{ss:02d}")
        self._meta.show()

    def clear_metadata(self) -> None:
        self._meta.clear()
        self._meta.hide()

    def current_url(self) -> str:
        return self._input.text().strip()

    def clear_input(self) -> None:
        self._input.clear()

    # ---- events ----

    def _on_submit(self) -> None:
        if self._busy:
            self.cancel_requested.emit()
            return
        url = self.current_url()
        if not url:
            return
        self.url_submitted.emit(url)
