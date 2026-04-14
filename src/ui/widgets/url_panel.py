"""
UrlPanel — input URL + options (langue, format notes) + progress overlay.

Layout :
    [Lang ▼] [TXT | JSON]                               (options row)
    [https://youtube.com/...                ] [GO/STOP] (input row)
    Title · mm:ss                                        (meta)
    ▇▇▇▇░░░░░░░░░░ Downloading 45%                      (progress)

Les options (langue, format) ne s'appliquent qu'au chemin URL ; le chemin
mic utilise ses propres réglages. L'état initial est restauré depuis les
settings utilisateur via le constructeur `UrlPanel(initial_language, initial_format)`.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...i18n import t
from .. import theme

_LANG_OPTIONS: list[tuple[str, str]] = [
    ("auto", "url_lang_auto"),
    ("fr", "url_lang_fr"),
    ("en", "url_lang_en"),
]


class UrlPanel(QWidget):
    """
    Panel d'entrée URL vidéo.

    Signaux :
      - url_submitted(str, str, str) : (url, language_code, notes_format)
      - cancel_requested() : annulation du job en cours
      - language_changed(str) : langue sélectionnée (pour persistence)
      - notes_format_changed(str) : format sélectionné (pour persistence)
    """

    url_submitted = pyqtSignal(str, str, str)
    cancel_requested = pyqtSignal()
    language_changed = pyqtSignal(str)
    notes_format_changed = pyqtSignal(str)

    def __init__(
        self,
        initial_language: str = "auto",
        initial_format: str = "json",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("urlPanel")
        self._busy = False
        self._language = initial_language if initial_language in {"auto", "fr", "en"} else "auto"
        self._format = initial_format if initial_format in {"txt", "json"} else "json"
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(theme.SPACE_2)

        # --- Options row (lang + format) ---
        options = QHBoxLayout()
        options.setContentsMargins(0, 0, 0, 0)
        options.setSpacing(theme.SPACE_2)

        self._lang_combo = QComboBox()
        self._lang_combo.setObjectName("urlLangCombo")
        for code, key in _LANG_OPTIONS:
            self._lang_combo.addItem(t(key), code)
        self._set_combo_to_language(self._language)
        self._lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        options.addWidget(self._lang_combo, 0)

        # Format toggle (segmented pair)
        self._btn_fmt_txt = QPushButton(t("url_format_txt"))
        self._btn_fmt_txt.setObjectName("formatToggleBtn")
        self._btn_fmt_txt.setProperty("segment", "left")
        self._btn_fmt_txt.setCheckable(True)
        self._btn_fmt_txt.clicked.connect(lambda: self._set_format("txt"))
        options.addWidget(self._btn_fmt_txt, 0)

        self._btn_fmt_json = QPushButton(t("url_format_json"))
        self._btn_fmt_json.setObjectName("formatToggleBtn")
        self._btn_fmt_json.setProperty("segment", "right")
        self._btn_fmt_json.setCheckable(True)
        self._btn_fmt_json.clicked.connect(lambda: self._set_format("json"))
        options.addWidget(self._btn_fmt_json, 0)

        options.addStretch()
        root.addLayout(options)

        # --- Input row ---
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(theme.SPACE_2)

        self._input = QLineEdit()
        self._input.setObjectName("urlInput")
        self._input.setPlaceholderText(t("url_placeholder"))
        self._input.setClearButtonEnabled(True)
        self._input.returnPressed.connect(self._on_submit)
        row.addWidget(self._input, 1)

        self._btn = QPushButton(t("btn_go"))
        self._btn.setObjectName("urlSubmitBtn")
        self._btn.setFixedWidth(70)
        self._btn.clicked.connect(self._on_submit)
        row.addWidget(self._btn, 0)

        root.addLayout(row)

        # --- Meta line (hidden until metadata available) ---
        self._meta = QLabel("")
        self._meta.setObjectName("urlMeta")
        self._meta.setWordWrap(True)
        self._meta.hide()
        root.addWidget(self._meta)

        # --- Progress bar + status ---
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

        # Initial state of the format buttons
        self._apply_format_state()

    # ---- API ----

    def set_visible_mode(self, visible: bool) -> None:
        self.setVisible(visible)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._input.setEnabled(not busy)
        self._lang_combo.setEnabled(not busy)
        self._btn_fmt_txt.setEnabled(not busy)
        self._btn_fmt_json.setEnabled(not busy)
        self._btn.setText(t("btn_stop") if busy else t("btn_go"))
        self._btn.setProperty("busy", busy)
        self._btn.style().unpolish(self._btn)
        self._btn.style().polish(self._btn)
        if busy:
            self._progress.show()
            self._progress_label.show()
            self._progress.setValue(0)
            self._progress_label.setText(t("url_fetching"))
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

    @property
    def language(self) -> str:
        return self._language

    @property
    def notes_format(self) -> str:
        return self._format

    # ---- internals ----

    def _set_combo_to_language(self, code: str) -> None:
        for i in range(self._lang_combo.count()):
            if self._lang_combo.itemData(i) == code:
                self._lang_combo.setCurrentIndex(i)
                return

    def _on_lang_changed(self, index: int) -> None:
        code = self._lang_combo.itemData(index)
        if code and code != self._language:
            self._language = code
            self.language_changed.emit(code)

    def _set_format(self, fmt: str) -> None:
        if fmt not in ("txt", "json"):
            return
        if fmt == self._format:
            self._apply_format_state()
            return
        self._format = fmt
        self._apply_format_state()
        self.notes_format_changed.emit(fmt)

    def _apply_format_state(self) -> None:
        self._btn_fmt_txt.setChecked(self._format == "txt")
        self._btn_fmt_json.setChecked(self._format == "json")
        for btn in (self._btn_fmt_txt, self._btn_fmt_json):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_submit(self) -> None:
        if self._busy:
            self.cancel_requested.emit()
            return
        url = self.current_url()
        if not url:
            return
        self.url_submitted.emit(url, self._language, self._format)
