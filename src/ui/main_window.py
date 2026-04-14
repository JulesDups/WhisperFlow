"""
WhisperFlow Desktop — Main Window (Hegoatek DA).

Compose les widgets isolés (status bar, level meter, stats strip, source
toggle, URL panel, transcript view, menu) en une seule fenêtre cohérente.

Architecture :
- TitleBar : branding + menu ≡ + close ×
- StatusBar : état central unique (loading/ready/recording/processing/error)
- LevelMeter : feedback visuel niveau audio temps réel
- SourceToggle : MIC / URL (persistant)
- UrlPanel : input vidéo + progression (visible en mode URL)
- TranscriptView : zone résultat 3-states (empty/result/error)
- StatsStrip : GPU / MODEL / SESSION metrics en continu
"""

from __future__ import annotations

import logging

import numpy as np
from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizeGrip,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    OutputMode,
    RecordingMode,
    WindowMode,
    app_config,
    hotkey_config,
    model_config,
)
from ..transcription_service import TranscriptionService
from ..utils.clipboard import copy_to_clipboard, type_text
from ..utils.history import history as transcription_history
from ..utils.hotkey_listener import GlobalHotkeyListener
from ..utils.settings import (
    get_history_enabled,
    get_ptt_key,
    get_recording_mode,
    get_source_mode,
    get_window_mode,
    get_window_position,
    get_window_size,
    set_ptt_key,
    set_recording_mode,
    set_source_mode,
    set_window_mode,
    set_window_position,
    set_window_size,
)
from ..utils.voice_notes import voice_notes
from . import theme
from .key_capture_dialog import KeyCaptureDialog
from .styles import get_main_stylesheet
from .widgets import (
    AppState,
    LevelMeter,
    MenuButton,
    SourceMode,
    SourceToggle,
    StatsStrip,
    StatusBar,
    TranscriptState,
    TranscriptView,
    UrlPanel,
)
from .workers import (
    AudioRecorderWorker,
    ModelLoaderWorker,
    TranscriptionWorker,
    UrlTranscriptionWorker,
)

logger = logging.getLogger(__name__)


class _TitleBar(QWidget):
    """Barre supérieure : brand eyebrow + nom + version + menu + close. Draggable."""

    close_clicked = pyqtSignal()
    menu_clicked = pyqtSignal()

    def __init__(self, menu_button: MenuButton, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(48)
        self._drag_position: QPoint | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(theme.SPACE_5, theme.SPACE_3, theme.SPACE_3, theme.SPACE_3)
        root.setSpacing(theme.SPACE_3)

        brand = QVBoxLayout()
        brand.setContentsMargins(0, 0, 0, 0)
        brand.setSpacing(0)

        self._eyebrow = QLabel("DESKTOP · VOICE")
        self._eyebrow.setObjectName("brandEyebrow")
        brand.addWidget(self._eyebrow)

        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(theme.SPACE_2)
        self._name = QLabel(app_config.APP_NAME)
        self._name.setObjectName("brandName")
        name_row.addWidget(self._name)
        self._version = QLabel(f"v{app_config.APP_VERSION}")
        self._version.setObjectName("brandVersion")
        name_row.addWidget(self._version, 0, Qt.AlignmentFlag.AlignBottom)
        brand.addLayout(name_row)

        root.addLayout(brand)
        root.addStretch()

        root.addWidget(menu_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self._close_btn = QPushButton("×")
        self._close_btn.setObjectName("closeButton")
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setToolTip("Close (Esc)")
        self._close_btn.clicked.connect(self.close_clicked.emit)
        root.addWidget(self._close_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_position is None:
            return
        delta = event.globalPosition().toPoint() - self._drag_position
        parent = self.window()
        parent.move(parent.pos() + delta)
        self._drag_position = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._drag_position = None


class MainWindow(QMainWindow):
    """
    Fenêtre principale WhisperFlow — design Hegoatek.

    Deux modes source :
      - MIC : push-to-talk / VAD (pipeline existant)
      - URL : téléchargement vidéo yt-dlp + transcription
    """

    def __init__(self) -> None:
        super().__init__()

        # State
        self._last_transcription = ""
        self._is_floating = get_window_mode() == WindowMode.FLOATING
        self._recording_mode = get_recording_mode()
        self._source_mode = SourceMode(get_source_mode())
        self._history_enabled = get_history_enabled()
        self._last_audio_duration_s: float = 0.0

        # Services
        self.transcription_service = TranscriptionService()

        # Workers
        self.model_loader: ModelLoaderWorker | None = None
        self.transcription_worker: TranscriptionWorker | None = None
        self.audio_worker: AudioRecorderWorker | None = None
        self.url_worker: UrlTranscriptionWorker | None = None

        # Hotkeys
        self.hotkey_listener = GlobalHotkeyListener()
        self._current_ptt_key = get_ptt_key()

        # Setup
        self._setup_window()
        self._setup_ui()
        self._setup_workers()
        self._setup_hotkeys()
        self._apply_styles()
        self._restore_window_position()

        # Load model
        QTimer.singleShot(500, self._start_model_loading)

    # ============================================================
    # Window chrome
    # ============================================================

    def _setup_window(self) -> None:
        self.setWindowTitle(app_config.APP_NAME)

        width, height = get_window_size()
        self.resize(width, height)
        self.setMinimumSize(theme.WINDOW_MIN_WIDTH, theme.WINDOW_MIN_HEIGHT)

        self._apply_window_mode()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _apply_window_mode(self) -> None:
        flags = Qt.WindowType.FramelessWindowHint
        if self._is_floating:
            flags |= Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        else:
            flags |= Qt.WindowType.Window
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _restore_window_position(self) -> None:
        x, y = get_window_position()
        if x >= 0 and y >= 0:
            screen = QApplication.primaryScreen()
            if screen:
                geom = screen.availableGeometry()
                if 0 <= x < geom.width() and 0 <= y < geom.height():
                    self.move(x, y)
                    return
        self._center_window()

    def _center_window(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            x = (geom.width() - self.width()) // 2
            y = (geom.height() - self.height()) // 2
            self.move(x, y)

    # ============================================================
    # UI composition
    # ============================================================

    def _setup_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralFrame")
        self.setCentralWidget(central)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        central.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Menu button (injected into title bar)
        self.menu_btn = MenuButton()
        self.menu_btn.configure_ptt_requested.connect(self._open_key_config)
        self.menu_btn.toggle_floating_requested.connect(self._toggle_window_mode)
        self.menu_btn.toggle_recording_mode_requested.connect(self._toggle_recording_mode)
        self.menu_btn.quit_requested.connect(self.close)
        self.menu_btn.set_floating(self._is_floating)
        self.menu_btn.set_recording_mode_vad(self._recording_mode == RecordingMode.VOICE_DETECTION)

        # Title bar
        self.title_bar = _TitleBar(self.menu_btn)
        self.title_bar.close_clicked.connect(self.close)
        main_layout.addWidget(self.title_bar)

        # Content area
        content = QWidget()
        content.setObjectName("contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(theme.SPACE_5, theme.SPACE_2, theme.SPACE_5, theme.SPACE_3)
        content_layout.setSpacing(theme.SPACE_4)
        main_layout.addWidget(content, 1)

        # --- Status bar ---
        self.status_bar = StatusBar()
        content_layout.addWidget(self.status_bar)

        # --- Level meter ---
        self.level_meter = LevelMeter()
        content_layout.addWidget(self.level_meter)

        # --- Source toggle ---
        self.source_toggle = SourceToggle(initial=self._source_mode)
        self.source_toggle.source_changed.connect(self._on_source_changed)
        content_layout.addWidget(self.source_toggle)

        # --- URL panel (visible seulement en mode URL) ---
        self.url_panel = UrlPanel()
        self.url_panel.url_submitted.connect(self._on_url_submitted)
        self.url_panel.cancel_requested.connect(self._on_url_cancelled)
        self.url_panel.set_visible_mode(self._source_mode == SourceMode.URL)
        content_layout.addWidget(self.url_panel)

        # --- Transcript view ---
        self.transcript_view = TranscriptView()
        self.transcript_view.retry_requested.connect(self._on_retry_requested)
        content_layout.addWidget(self.transcript_view, 1)

        # --- Bottom row : copy button + stats strip ---
        self.stats_strip = StatsStrip()
        self.stats_strip.set_model_info(model_config.MODEL_ID, "auto")
        content_layout.addWidget(self.stats_strip)

        # Copy row (fallback si type_text échoue + permet select-and-copy)
        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(theme.SPACE_2)
        actions_row.addStretch()
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setObjectName("urlSubmitBtn")
        self.copy_btn.setFixedWidth(100)
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._copy_transcription)
        actions_row.addWidget(self.copy_btn)
        content_layout.addLayout(actions_row)

        # Size grip in bottom-right corner for resizing
        self._size_grip = QSizeGrip(central)
        self._size_grip.setFixedSize(16, 16)

        # Start GPU polling
        self.stats_strip.gpu_gauge.start_polling()

        # Initial transcript hint
        self._update_empty_hint()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        # Position the size grip at the bottom-right
        if hasattr(self, "_size_grip"):
            central = self.centralWidget()
            if central is not None:
                self._size_grip.move(
                    central.width() - self._size_grip.width() - 4,
                    central.height() - self._size_grip.height() - 4,
                )

    # ============================================================
    # Workers
    # ============================================================

    def _setup_workers(self) -> None:
        # Audio recording worker
        self.audio_worker = AudioRecorderWorker()
        self.audio_worker.recording_started.connect(self._on_recording_started)
        self.audio_worker.recording_stopped.connect(self._on_recording_stopped)
        self.audio_worker.audio_level.connect(self._on_audio_level)
        self.audio_worker.audio_ready.connect(self._on_audio_ready)
        self.audio_worker.error.connect(self._on_error)
        self.audio_worker.start()

        # Transcription worker (mic path)
        self.transcription_worker = TranscriptionWorker(self.transcription_service)
        self.transcription_worker.started.connect(self._on_transcription_started)
        self.transcription_worker.result.connect(self._on_transcription_result)
        self.transcription_worker.error.connect(self._on_error)
        self.transcription_worker.finished.connect(self._on_transcription_finished)
        self.transcription_worker.start()

        # URL worker (video path)
        self.url_worker = UrlTranscriptionWorker(self.transcription_service)
        self.url_worker.dl_progress.connect(self._on_url_progress)
        self.url_worker.transcribe_progress.connect(self._on_url_transcribe_progress)
        self.url_worker.metadata.connect(self._on_url_metadata)
        self.url_worker.result.connect(self._on_url_result)
        self.url_worker.error.connect(self._on_url_error)
        self.url_worker.finished.connect(self._on_url_finished)
        self.url_worker.start()

    def _setup_hotkeys(self) -> None:
        self.hotkey_listener.register(
            self._current_ptt_key,
            on_press=self._on_ptt_press,
            on_release=self._on_ptt_release,
            description="Push-to-Talk",
        )
        self.hotkey_listener.register("f1", on_press=self._toggle_recording_mode, description="Mode")
        self.hotkey_listener.register(
            hotkey_config.COPY_TO_CLIPBOARD_KEY,
            on_press=self._copy_transcription,
            description="Copy",
        )
        self.hotkey_listener.register(hotkey_config.QUIT_KEY, on_press=self.close, description="Quit")
        self.hotkey_listener.start()

    def _apply_styles(self) -> None:
        self.setStyleSheet(get_main_stylesheet())

    # ============================================================
    # State helpers
    # ============================================================

    def _hotkey_hint(self) -> str:
        if self._recording_mode == RecordingMode.VOICE_DETECTION:
            return "VAD listening"
        return f"hold {self._current_ptt_key.upper()}"

    def _set_state(self, state: AppState) -> None:
        self.status_bar.set_state(state, self._hotkey_hint())

    def _update_empty_hint(self) -> None:
        if self._source_mode == SourceMode.URL:
            hint = "Paste a video URL and press GO."
        elif self._recording_mode == RecordingMode.VOICE_DETECTION:
            hint = "Auto-listening. Just start speaking."
        else:
            hint = f"Hold {self._current_ptt_key.upper()} to speak."
        self.transcript_view.set_empty_hint(hint)

    # ============================================================
    # Model loading
    # ============================================================

    def _start_model_loading(self) -> None:
        self._set_state(AppState.LOADING)
        self.model_loader = ModelLoaderWorker(self.transcription_service)
        self.model_loader.progress.connect(self._on_model_progress)
        self.model_loader.finished.connect(self._on_model_loaded)
        self.model_loader.error.connect(self._on_error)
        self.model_loader.start()

    def _on_model_progress(self, message: str, progress: float) -> None:
        self.status_bar.show_transient(f"{message} ({int(progress * 100)}%)", 10_000)

    def _on_model_loaded(self, success: bool) -> None:
        if not success:
            self._set_state(AppState.ERROR)
            self.status_bar.show_transient("Model load failed", 5_000)
            return
        self._set_state(AppState.READY)
        self.stats_strip.set_model_status(None, True)
        if (
            self._recording_mode == RecordingMode.VOICE_DETECTION
            and self.audio_worker is not None
            and self._source_mode == SourceMode.MIC
        ):
            self.audio_worker.start_vad()

    # ============================================================
    # PTT + VAD (mic path)
    # ============================================================

    def _on_ptt_press(self) -> None:
        if self._source_mode != SourceMode.MIC:
            return
        if self._recording_mode == RecordingMode.VOICE_DETECTION:
            return
        if self.status_bar.state != AppState.READY:
            return
        if self.audio_worker is not None:
            self.audio_worker.start_recording()

    def _on_ptt_release(self) -> None:
        if self._source_mode != SourceMode.MIC:
            return
        if self._recording_mode == RecordingMode.VOICE_DETECTION:
            return
        if self.status_bar.state != AppState.RECORDING:
            return
        if self.audio_worker is not None:
            self.audio_worker.stop_recording()

    def _on_recording_started(self) -> None:
        self._set_state(AppState.RECORDING)
        self.level_meter.set_recording(True)
        self.transcript_view.set_state(TranscriptState.EMPTY)

    def _on_recording_stopped(self) -> None:
        self.level_meter.set_recording(False)
        self.level_meter.set_level(0.0)

    def _on_audio_level(self, level: float) -> None:
        self.level_meter.set_level(level)

    def _on_audio_ready(self, audio_data: np.ndarray, sample_rate: int) -> None:
        self._set_state(AppState.PROCESSING)
        self._last_audio_duration_s = float(len(audio_data)) / float(sample_rate)
        if self.transcription_worker is not None:
            self.transcription_worker.set_audio(audio_data, sample_rate)

    # ============================================================
    # Transcription result (mic)
    # ============================================================

    def _on_transcription_started(self) -> None:
        pass

    def _on_transcription_result(self, text: str, processing_time: float) -> None:
        self._last_transcription = text
        if not text:
            self.transcript_view.set_error("Empty transcription")
            return

        self.transcript_view.set_result(text)
        self.copy_btn.setEnabled(True)

        # Stats
        self.stats_strip.record_transcription(text, self._last_audio_duration_s, processing_time)

        # Toast & history
        self.status_bar.show_transient(f"Done in {processing_time:.2f}s", 2200)
        if self._history_enabled:
            transcription_history.add(text, processing_time)
        voice_notes.add_note(text)

        # Auto-type
        if hotkey_config.OUTPUT_MODE == OutputMode.TYPE:
            QTimer.singleShot(10, lambda: self._auto_type_text(text))

    def _auto_type_text(self, text: str) -> None:
        if type_text(text, use_clipboard=True):
            self.status_bar.show_transient("Text inserted", 1800)
        else:
            self.status_bar.show_transient("Auto-type failed — use Copy", 3000)

    def _on_transcription_finished(self) -> None:
        self._set_state(AppState.READY)
        if (
            self._recording_mode == RecordingMode.VOICE_DETECTION
            and self.audio_worker is not None
            and self._source_mode == SourceMode.MIC
        ):
            self.audio_worker.notify_transcription_done()

    # ============================================================
    # URL flow
    # ============================================================

    def _on_source_changed(self, mode: SourceMode) -> None:
        self._source_mode = mode
        set_source_mode(mode.value)
        self.url_panel.set_visible_mode(mode == SourceMode.URL)
        self._update_empty_hint()

        if mode == SourceMode.URL:
            # Switching to URL : stop VAD/listening on mic
            if self.audio_worker is not None and self._recording_mode == RecordingMode.VOICE_DETECTION:
                self.audio_worker.stop_vad()
            self.transcript_view.set_state(TranscriptState.EMPTY)
        else:
            # Switching back to mic : restart VAD if needed
            if (
                self.audio_worker is not None
                and self._recording_mode == RecordingMode.VOICE_DETECTION
                and self.status_bar.state == AppState.READY
            ):
                self.audio_worker.start_vad()

    def _on_url_submitted(self, url: str) -> None:
        if self.url_worker is None:
            return
        self.url_panel.clear_metadata()
        self.url_panel.set_busy(True)
        self._set_state(AppState.PROCESSING)
        self.transcript_view.set_state(TranscriptState.EMPTY)
        self.url_worker.submit_url(url)

    def _on_url_cancelled(self) -> None:
        if self.url_worker is not None:
            self.url_worker.cancel()
        self.url_panel.set_busy(False)
        self._set_state(AppState.READY)

    def _on_url_progress(self, message: str, ratio: float) -> None:
        self.url_panel.set_progress(message, ratio)

    def _on_url_transcribe_progress(self, message: str) -> None:
        self.url_panel.set_progress(message, 0.85)

    def _on_url_metadata(self, title: str, duration_s: float) -> None:
        self.url_panel.set_metadata(title, duration_s)

    def _on_url_result(
        self,
        text: str,
        lang: str,
        confidence: float,
        audio_duration_s: float,
        processing_time: float,
    ) -> None:
        self._last_transcription = text
        self.transcript_view.set_result(text, lang or None, confidence or None)
        self.copy_btn.setEnabled(bool(text))

        self.stats_strip.record_transcription(text, audio_duration_s, processing_time)
        self.status_bar.show_transient(
            f"Transcribed in {processing_time:.1f}s · {audio_duration_s:.0f}s audio",
            3000,
        )
        if self._history_enabled and text:
            transcription_history.add(text, processing_time)
        if text:
            voice_notes.add_note(text)

    def _on_url_error(self, message: str) -> None:
        self.transcript_view.set_error(message)
        self.url_panel.set_busy(False)
        self._set_state(AppState.ERROR)

    def _on_url_finished(self) -> None:
        self.url_panel.set_busy(False)
        if self.status_bar.state != AppState.ERROR:
            self._set_state(AppState.READY)

    # ============================================================
    # Menu actions
    # ============================================================

    def _copy_transcription(self) -> None:
        text = self.transcript_view.current_text() or self._last_transcription
        if text and copy_to_clipboard(text):
            self.status_bar.show_transient("Copied to clipboard", 1800)

    def _on_retry_requested(self) -> None:
        # Si mode URL : resoumettre l'URL courante. Sinon : passer à l'empty state.
        if self._source_mode == SourceMode.URL:
            url = self.url_panel.current_url()
            if url:
                self._on_url_submitted(url)
                return
        self.transcript_view.set_state(TranscriptState.EMPTY)
        self._set_state(AppState.READY)

    def _toggle_recording_mode(self) -> None:
        if self.status_bar.state == AppState.RECORDING:
            return
        if self._recording_mode == RecordingMode.PUSH_TO_TALK:
            self._recording_mode = RecordingMode.VOICE_DETECTION
        else:
            self._recording_mode = RecordingMode.PUSH_TO_TALK
        set_recording_mode(self._recording_mode)
        self.menu_btn.set_recording_mode_vad(self._recording_mode == RecordingMode.VOICE_DETECTION)
        self._update_empty_hint()

        if self.audio_worker is not None and self._source_mode == SourceMode.MIC:
            if self._recording_mode == RecordingMode.VOICE_DETECTION:
                self.audio_worker.start_vad()
            else:
                self.audio_worker.stop_vad()

        self._set_state(AppState.READY)
        mode_name = "Auto (VAD)" if self._recording_mode == RecordingMode.VOICE_DETECTION else "Hold"
        self.status_bar.show_transient(f"Recording mode: {mode_name}", 1800)

    def _open_key_config(self) -> None:
        if self.status_bar.state == AppState.RECORDING:
            return
        current_key = get_ptt_key()
        dialog = KeyCaptureDialog(current_key, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_key = dialog.get_key()
            if new_key and new_key != current_key:
                self._change_ptt_key(new_key)

    def _change_ptt_key(self, new_key: str) -> None:
        old_key = self._current_ptt_key
        self.hotkey_listener.unregister(old_key)
        self._current_ptt_key = new_key
        self.hotkey_listener.register(
            new_key,
            on_press=self._on_ptt_press,
            on_release=self._on_ptt_release,
            description="Push-to-Talk",
        )
        set_ptt_key(new_key)
        self._update_empty_hint()
        self.status_bar.show_transient(f"Hotkey: {new_key.upper()}", 2000)
        logger.info("PTT key changed: %s -> %s", old_key, new_key)
        QTimer.singleShot(2000, lambda: self._set_state(AppState.READY))

    def _toggle_window_mode(self) -> None:
        self._is_floating = not self._is_floating
        set_window_mode(WindowMode.FLOATING if self._is_floating else WindowMode.NORMAL)

        pos = self.pos()
        set_window_position(pos.x(), pos.y())

        self._apply_window_mode()
        self.show()
        self.move(pos)

        self.menu_btn.set_floating(self._is_floating)
        mode_name = "Floating" if self._is_floating else "Normal"
        self.status_bar.show_transient(f"Window: {mode_name}", 1800)

    # ============================================================
    # Errors
    # ============================================================

    def _on_error(self, message: str) -> None:
        self._set_state(AppState.ERROR)
        self.transcript_view.set_error(message)
        logger.error("Error: %s", message)

    # ============================================================
    # Lifecycle
    # ============================================================

    def closeEvent(self, event) -> None:  # noqa: N802
        logger.info("Closing WhisperFlow...")

        # Persist window geometry
        pos = self.pos()
        set_window_position(pos.x(), pos.y())
        set_window_size(self.width(), self.height())

        # Stop hotkeys
        self.hotkey_listener.stop()

        # Stop workers
        if hasattr(self, "stats_strip"):
            self.stats_strip.gpu_gauge.stop_polling()
        if self.audio_worker is not None:
            self.audio_worker.stop()
        if self.transcription_worker is not None:
            self.transcription_worker.stop()
        if self.url_worker is not None:
            self.url_worker.stop()
        if self.model_loader is not None:
            self.model_loader.stop()

        # Unload model
        if self.transcription_service and self.transcription_service.is_loaded:
            self.transcription_service.unload_model()

        event.accept()
        QApplication.quit()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)
