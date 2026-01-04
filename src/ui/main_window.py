"""
WhisperFlow Desktop - Main Window
Fenêtre principale de l'application avec interface moderne
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy, QApplication, QDialog,
    QMenu, QToolButton
)
from PyQt6.QtCore import (
    Qt, QTimer, QPoint, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QSize
)
from PyQt6.QtGui import (
    QColor, QFont, QIcon, QMouseEvent, QPainter,
    QBrush, QPen, QLinearGradient, QAction
)
import numpy as np
from typing import Optional
from enum import Enum

import sys
sys.path.append('../..')
from config import ui_config, hotkey_config, app_config, model_config
from src.ui.styles import get_main_stylesheet, get_state_colors
from src.ui.workers import (
    ModelLoaderWorker, TranscriptionWorker, AudioRecorderWorker
)
from src.transcription_service import TranscriptionService
from src.utils.clipboard import copy_to_clipboard, type_text
from src.utils.hotkey_listener import GlobalHotkeyListener
from src.utils.settings import (
    settings_manager, get_ptt_key, set_ptt_key, get_language,
    get_window_mode, set_window_mode, get_window_position, set_window_position,
    get_history_enabled, set_history_enabled
)
from src.ui.key_capture_dialog import KeyCaptureDialog
from src.utils.history import history as transcription_history


class AppState(Enum):
    """États de l'application"""
    LOADING = "loading"
    READY = "ready"
    RECORDING = "recording"
    PROCESSING = "processing"
    ERROR = "error"


class StatusIndicator(QWidget):
    """
    Indicateur d'état circulaire avec animation
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusIndicator")
        self.setFixedSize(12, 12)
        
        self._state = "loading"
        self._pulse_opacity = 1.0
        
        # Timer pour l'animation de pulsation
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._update_pulse)
        self._pulse_direction = -1
    
    def setState(self, state: str):
        """Change l'état de l'indicateur"""
        self._state = state
        self.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)
        
        # Active/désactive la pulsation
        if state == "recording":
            self._pulse_timer.start(50)
        else:
            self._pulse_timer.stop()
            self._pulse_opacity = 1.0
        
        self.update()
    
    def _update_pulse(self):
        """Met à jour l'animation de pulsation"""
        self._pulse_opacity += self._pulse_direction * 0.05
        
        if self._pulse_opacity <= 0.4:
            self._pulse_direction = 1
        elif self._pulse_opacity >= 1.0:
            self._pulse_direction = -1
        
        self.update()
    
    def paintEvent(self, event):
        """Dessine l'indicateur"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        colors = get_state_colors()
        color = QColor(colors.get(self._state, colors["loading"]))
        color.setAlphaF(self._pulse_opacity)
        
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 12, 12)


class AudioLevelBar(QProgressBar):
    """
    Barre de niveau audio stylisée
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 100)
        self.setValue(0)
        self.setTextVisible(False)
        self.setFixedHeight(8)
        
        self._state = "ready"
    
    def setState(self, state: str):
        """Change l'état visuel"""
        self._state = state
        self.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)
    
    def setLevel(self, level: float):
        """Met à jour le niveau (0-1)"""
        self.setValue(int(level * 100))


class VRAMIndicator(QWidget):
    """
    Indicateur d'utilisation VRAM GPU.
    Affiche la mémoire utilisée / totale avec barre de progression.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("vramIndicator")
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Icône GPU
        self.icon_label = QLabel("🎮")
        self.icon_label.setObjectName("vramIcon")
        layout.addWidget(self.icon_label)
        
        # Barre de progression VRAM
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("vramBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setFixedWidth(80)
        layout.addWidget(self.progress_bar)
        
        # Label texte
        self.text_label = QLabel("-- / -- GB")
        self.text_label.setObjectName("vramText")
        layout.addWidget(self.text_label)
        
        layout.addStretch()
    
    def update_vram(self, used_gb: float, total_gb: float, percentage: float):
        """Met à jour l'affichage VRAM"""
        self.progress_bar.setValue(int(percentage))
        self.text_label.setText(f"{used_gb:.1f} / {total_gb:.1f} GB")
        
        # Change la couleur selon l'utilisation
        if percentage > 90:
            self.progress_bar.setProperty("level", "critical")
        elif percentage > 75:
            self.progress_bar.setProperty("level", "warning")
        else:
            self.progress_bar.setProperty("level", "normal")
        
        self.progress_bar.style().unpolish(self.progress_bar)
        self.progress_bar.style().polish(self.progress_bar)


class TitleBar(QWidget):
    """
    Barre de titre personnalisée pour fenêtre sans bordure
    Permet le drag de la fenêtre
    """
    
    close_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(40)
        
        self._drag_position: Optional[QPoint] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 8, 8)
        layout.setSpacing(8)
        
        # Indicateur d'état
        self.status_indicator = StatusIndicator()
        layout.addWidget(self.status_indicator)
        
        # Titre
        self.title_label = QLabel(app_config.APP_NAME)
        self.title_label.setObjectName("titleLabel")
        layout.addWidget(self.title_label)
        
        # Spacer
        layout.addStretch()
        
        # Version
        version_label = QLabel(f"v{app_config.APP_VERSION}")
        version_label.setObjectName("hotkeyLabel")
        layout.addWidget(version_label)
        
        # Bouton fermer
        close_btn = QPushButton("×")
        close_btn.setObjectName("closeButton")
        close_btn.clicked.connect(self.close_clicked.emit)
        close_btn.setToolTip("Fermer (ESC)")
        layout.addWidget(close_btn)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Début du drag"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Déplacement de la fenêtre"""
        if self._drag_position:
            delta = event.globalPosition().toPoint() - self._drag_position
            parent = self.window()
            parent.move(parent.pos() + delta)
            self._drag_position = event.globalPosition().toPoint()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Fin du drag"""
        self._drag_position = None


class MainWindow(QMainWindow):
    """
    Fenêtre principale de WhisperFlow
    
    Interface flottante minimaliste avec:
    - Push-to-Talk global (configurable)
    - Transcription temps réel
    - Smart Formatting
    - Mode fenêtre flottante/normale
    """
    
    def __init__(self):
        super().__init__()
        
        # État
        self._state = AppState.LOADING
        self._last_transcription = ""
        self._is_floating = get_window_mode() == "floating"
        
        # Services
        self.transcription_service = TranscriptionService()
        
        # Workers
        self.model_loader: Optional[ModelLoaderWorker] = None
        self.transcription_worker: Optional[TranscriptionWorker] = None
        self.audio_worker: Optional[AudioRecorderWorker] = None
        
        # Hotkey listener
        self.hotkey_listener = GlobalHotkeyListener()
        
        # Configuration historique
        self._history_enabled = get_history_enabled()
        
        # Setup
        self._setup_window()
        self._setup_ui()
        self._setup_workers()
        self._setup_hotkeys()
        self._apply_styles()
        
        # Restaure la position
        self._restore_window_position()
        
        # Démarre le chargement du modèle
        QTimer.singleShot(500, self._start_model_loading)
    
    def _setup_window(self):
        """Configure la fenêtre"""
        # Titre
        self.setWindowTitle(app_config.APP_NAME)
        
        # Taille
        self.setFixedSize(ui_config.WINDOW_WIDTH, ui_config.WINDOW_HEIGHT)
        
        # Applique le mode fenêtre
        self._apply_window_mode()
        
        # Opacité
        self.setWindowOpacity(ui_config.WINDOW_OPACITY)
    
    def _apply_window_mode(self):
        """Applique le mode fenêtre (flottant ou normal)"""
        if self._is_floating:
            # Fenêtre sans bordure, toujours au premier plan
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool
            )
        else:
            # Fenêtre normale avec bordure système
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.Window
            )
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    
    def _restore_window_position(self):
        """Restaure la position de la fenêtre sauvegardée"""
        x, y = get_window_position()
        if x >= 0 and y >= 0:
            # Vérifie que la position est valide (dans un écran)
            screen = QApplication.primaryScreen()
            if screen:
                geom = screen.availableGeometry()
                if 0 <= x < geom.width() and 0 <= y < geom.height():
                    self.move(x, y)
                    return
        
        # Par défaut, centre la fenêtre
        self._center_window()
    
    def _setup_ui(self):
        """Construit l'interface"""
        # Widget central avec effet d'ombre
        central = QWidget()
        central.setObjectName("centralFrame")
        self.setCentralWidget(central)
        
        # Ombre portée
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(ui_config.SHADOW_BLUR)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        central.setGraphicsEffect(shadow)
        
        # Layout principal
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Barre de titre
        self.title_bar = TitleBar()
        self.title_bar.close_clicked.connect(self.close)
        main_layout.addWidget(self.title_bar)
        
        # Zone de contenu
        content = QWidget()
        content.setObjectName("contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 8, 16, 16)
        content_layout.setSpacing(12)
        main_layout.addWidget(content)
        
        # Label de statut
        self.status_label = QLabel("Chargement du modèle...")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.status_label)
        
        # Barre de niveau audio
        self.audio_level = AudioLevelBar()
        content_layout.addWidget(self.audio_level)
        
        # Label de transcription
        self.transcription_label = QLabel("")
        self.transcription_label.setObjectName("transcriptionLabel")
        self.transcription_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.transcription_label.setWordWrap(True)
        self.transcription_label.setMinimumHeight(60)
        content_layout.addWidget(self.transcription_label)
        
        # Ligne d'info: raccourci + VRAM
        info_layout = QHBoxLayout()
        info_layout.setSpacing(12)
        
        # Hotkey info
        self.hotkey_label = QLabel()
        self.hotkey_label.setObjectName("hotkeyLabel")
        self._update_hotkey_label()
        info_layout.addWidget(self.hotkey_label)
        
        # Bouton configurer touche
        self.config_key_btn = QPushButton("⚙️")
        self.config_key_btn.setObjectName("configKeyButton")
        self.config_key_btn.setToolTip("Changer le raccourci Push-to-Talk")
        self.config_key_btn.setFixedSize(28, 28)
        self.config_key_btn.clicked.connect(self._open_key_config)
        info_layout.addWidget(self.config_key_btn)
        
        info_layout.addStretch()
        
        # Indicateur VRAM
        self.vram_indicator = VRAMIndicator()
        info_layout.addWidget(self.vram_indicator)
        
        content_layout.addLayout(info_layout)
        
        # Barre de boutons d'actions
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Bouton Mode Fenêtre (toggle flottant/normal)
        self.window_mode_btn = QPushButton("📌 Flottant" if self._is_floating else "📍 Normal")
        self.window_mode_btn.setObjectName("windowModeButton")
        self._update_window_mode_tooltip()
        self.window_mode_btn.setFixedHeight(32)
        self.window_mode_btn.clicked.connect(self._toggle_window_mode)
        button_layout.addWidget(self.window_mode_btn)
        
        button_layout.addStretch()
        
        # Bouton copier
        self.copy_btn = QPushButton("📋 Copier")
        self.copy_btn.setObjectName("copyButton")
        self.copy_btn.clicked.connect(self._copy_transcription)
        self.copy_btn.setEnabled(False)
        self.copy_btn.setFixedHeight(32)
        button_layout.addWidget(self.copy_btn)
        
        content_layout.addLayout(button_layout)
        
        # Timer pour mise à jour VRAM
        self._vram_timer = QTimer(self)
        self._vram_timer.timeout.connect(self._update_vram_display)
        self._vram_timer.start(ui_config.VRAM_UPDATE_INTERVAL_MS)
    
    def _setup_workers(self):
        """Initialise les workers de threading"""
        # Worker d'enregistrement audio
        self.audio_worker = AudioRecorderWorker()
        self.audio_worker.recording_started.connect(self._on_recording_started)
        self.audio_worker.recording_stopped.connect(self._on_recording_stopped)
        self.audio_worker.audio_level.connect(self._on_audio_level)
        self.audio_worker.audio_ready.connect(self._on_audio_ready)
        self.audio_worker.error.connect(self._on_error)
        self.audio_worker.start()
        
        # Worker de transcription
        self.transcription_worker = TranscriptionWorker(self.transcription_service)
        self.transcription_worker.started.connect(self._on_transcription_started)
        self.transcription_worker.result.connect(self._on_transcription_result)
        self.transcription_worker.error.connect(self._on_error)
        self.transcription_worker.finished.connect(self._on_transcription_finished)
        self.transcription_worker.start()
    
    def _setup_hotkeys(self):
        """Configure les raccourcis globaux"""
        # Push-to-Talk (utilise la touche sauvegardée)
        self._current_ptt_key = get_ptt_key()
        self.hotkey_listener.register(
            self._current_ptt_key,
            on_press=self._on_ptt_press,
            on_release=self._on_ptt_release,
            description="Push-to-Talk"
        )
        
        # Copier
        self.hotkey_listener.register(
            hotkey_config.COPY_TO_CLIPBOARD_KEY,
            on_press=self._copy_transcription,
            description="Copier"
        )
        
        # Quitter
        self.hotkey_listener.register(
            hotkey_config.QUIT_KEY,
            on_press=self.close,
            description="Quitter"
        )
        
        self.hotkey_listener.start()
    
    def _apply_styles(self):
        """Applique les styles CSS"""
        self.setStyleSheet(get_main_stylesheet())
    
    def _set_state(self, state: AppState):
        """Change l'état de l'application"""
        self._state = state
        
        # Met à jour l'indicateur
        self.title_bar.status_indicator.setState(state.value)
        self.audio_level.setState(state.value)
        
        # Met à jour le statut
        ptt_key = get_ptt_key().upper()
        status_messages = {
            AppState.LOADING: "Chargement du modèle...",
            AppState.READY: f"Prêt • Maintenez {ptt_key} pour parler",
            AppState.RECORDING: "🔴 Enregistrement...",
            AppState.PROCESSING: "⚙️ Transcription en cours...",
            AppState.ERROR: "❌ Erreur",
        }
        self.status_label.setText(status_messages.get(state, ""))
    
    # === Model Loading ===
    
    def _start_model_loading(self):
        """Démarre le chargement du modèle en arrière-plan"""
        self._set_state(AppState.LOADING)
        
        self.model_loader = ModelLoaderWorker(self.transcription_service)
        self.model_loader.progress.connect(self._on_model_progress)
        self.model_loader.finished.connect(self._on_model_loaded)
        self.model_loader.error.connect(self._on_error)
        self.model_loader.start()
    
    def _on_model_progress(self, message: str, progress: float):
        """Callback de progression du chargement"""
        self.status_label.setText(f"{message} ({int(progress * 100)}%)")
    
    def _on_model_loaded(self, success: bool):
        """Callback de fin de chargement"""
        if success:
            self._set_state(AppState.READY)
        else:
            self._set_state(AppState.ERROR)
            self.status_label.setText("❌ Échec du chargement du modèle")
    
    # === Recording ===
    
    def _on_ptt_press(self):
        """Appui sur la touche Push-to-Talk"""
        if self._state != AppState.READY:
            return
        
        if self.audio_worker:
            self.audio_worker.start_recording()
    
    def _on_ptt_release(self):
        """Relâchement de la touche Push-to-Talk"""
        if self._state != AppState.RECORDING:
            return
        
        if self.audio_worker:
            self.audio_worker.stop_recording()
    
    def _on_recording_started(self):
        """L'enregistrement a commencé"""
        self._set_state(AppState.RECORDING)
        self.transcription_label.setText("")
    
    def _on_recording_stopped(self):
        """L'enregistrement s'est arrêté"""
        self.audio_level.setLevel(0)
    
    def _on_audio_level(self, level: float):
        """Mise à jour du niveau audio"""
        self.audio_level.setLevel(level)
    
    def _on_audio_ready(self, audio_data: np.ndarray, sample_rate: int):
        """Audio prêt pour la transcription"""
        self._set_state(AppState.PROCESSING)
        if self.transcription_worker:
            self.transcription_worker.set_audio(audio_data, sample_rate)
    
    # === Transcription ===
    
    def _on_transcription_started(self):
        """La transcription a commencé"""
        pass
    
    def _on_transcription_result(self, text: str, processing_time: float):
        """Résultat de transcription reçu"""
        self._last_transcription = text
        self.transcription_label.setText(text)
        self.copy_btn.setEnabled(bool(text))
        
        # Affiche le temps de traitement
        if text:
            self.status_label.setText(f"✓ Transcrit en {processing_time:.2f}s")
            
            # Sauvegarde dans l'historique
            if self._history_enabled:
                transcription_history.add(text, processing_time)
            
            # Tape automatiquement si mode "type" activé
            if hotkey_config.OUTPUT_MODE == "type":
                # Délai minimal pour laisser la touche PTT être relâchée
                QTimer.singleShot(30, lambda: self._auto_type_text(text))
    
    def _auto_type_text(self, text: str):
        """Tape automatiquement le texte dans l'application active"""
        if type_text(text, use_clipboard=True):
            self.status_label.setText(f"⌨️ Texte inséré!")
        else:
            self.status_label.setText(f"⚠️ Impossible d'insérer le texte")
    
    def _on_transcription_finished(self):
        """La transcription est terminée"""
        self._set_state(AppState.READY)
    
    # === Actions ===
    
    def _copy_transcription(self):
        """Copie la transcription dans le presse-papier"""
        if self._last_transcription:
            if copy_to_clipboard(self._last_transcription):
                self.status_label.setText("📋 Copié dans le presse-papier!")
                QTimer.singleShot(2000, lambda: self._set_state(AppState.READY))
    
    def _update_hotkey_label(self):
        """Met à jour le label affichant la touche PTT"""
        ptt_key = get_ptt_key()
        # Formate joliment les combinaisons (ctrl+' -> Ctrl + ')
        display_key = ptt_key.replace('+', ' + ').upper()
        self.hotkey_label.setText(f"🎤 Maintenir {display_key} pour parler")
    
    def _open_key_config(self):
        """Ouvre le dialogue de configuration de touche"""
        if self._state == AppState.RECORDING:
            return  # Ne pas changer pendant l'enregistrement
        
        current_key = get_ptt_key()
        dialog = KeyCaptureDialog(current_key, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_key = dialog.get_key()
            if new_key and new_key != current_key:
                self._change_ptt_key(new_key)
    
    def _change_ptt_key(self, new_key: str):
        """Change la touche Push-to-Talk"""
        # Désactive l'ancienne touche
        old_key = self._current_ptt_key
        self.hotkey_listener.unregister(old_key)
        
        # Enregistre la nouvelle touche
        self._current_ptt_key = new_key
        self.hotkey_listener.register(
            new_key,
            on_press=self._on_ptt_press,
            on_release=self._on_ptt_release,
            description="Push-to-Talk"
        )
        
        # Sauvegarde dans les paramètres
        set_ptt_key(new_key)
        
        # Met à jour l'interface
        self._update_hotkey_label()
        self.status_label.setText(f"✓ Touche changée: {new_key.upper()}")
        
        print(f"🎹 Touche PTT changée: {old_key.upper()} → {new_key.upper()}")
        
        # Revient à l'état normal après 2s
        QTimer.singleShot(2000, lambda: self._set_state(AppState.READY))
    
    def _toggle_window_mode(self):
        """Bascule entre mode flottant et normal"""
        self._is_floating = not self._is_floating
        set_window_mode("floating" if self._is_floating else "normal")
        
        # Sauvegarde la position actuelle
        pos = self.pos()
        set_window_position(pos.x(), pos.y())
        
        # Réapplique le mode fenêtre
        self._apply_window_mode()
        
        # Recrée la fenêtre avec les nouveaux flags
        self.show()
        
        # Restaure la position
        self.move(pos)
        
        # Met à jour le bouton
        self.window_mode_btn.setText("📌 Flottant" if self._is_floating else "📍 Normal")
        self._update_window_mode_tooltip()
        
        mode_name = "flottant" if self._is_floating else "normal"
        self.status_label.setText(f"Mode fenêtre: {mode_name}")
        QTimer.singleShot(2000, lambda: self._set_state(AppState.READY))
    
    def _update_window_mode_tooltip(self):
        """Met à jour le tooltip du bouton mode fenêtre"""
        if self._is_floating:
            self.window_mode_btn.setToolTip("Mode: Flottant (toujours visible)\nCliquez pour basculer en mode normal")
        else:
            self.window_mode_btn.setToolTip("Mode: Normal\nCliquez pour basculer en mode flottant")
    
    def _center_window(self):
        """Centre la fenêtre sur l'écran"""
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            x = (geom.width() - self.width()) // 2
            y = (geom.height() - self.height()) // 2
            self.move(x, y)
    
    def _on_error(self, message: str):
        """Gestion des erreurs"""
        self._set_state(AppState.ERROR)
        self.status_label.setText(f"❌ {message}")
        print(f"❌ Erreur: {message}")
    
    def _update_vram_display(self):
        """Met à jour l'affichage VRAM"""
        used, total, percentage = TranscriptionService.get_vram_usage()
        self.vram_indicator.update_vram(used, total, percentage)
    
    # === Lifecycle ===
    
    def closeEvent(self, event):
        """Nettoyage à la fermeture"""
        print("🛑 Fermeture de l'application...")
        
        # Sauvegarde la position de la fenêtre
        pos = self.pos()
        set_window_position(pos.x(), pos.y())
        
        # Arrête le timer VRAM
        if hasattr(self, '_vram_timer'):
            self._vram_timer.stop()
        
        # Arrête les hotkeys
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        
        # Arrête les workers
        if self.audio_worker:
            self.audio_worker.stop()
        
        if self.transcription_worker:
            self.transcription_worker.stop()
        
        if self.model_loader:
            self.model_loader.stop()
        
        # Décharge le modèle
        if self.transcription_service and self.transcription_service.is_loaded:
            self.transcription_service.unload_model()
        
        event.accept()
        
        # Force la fermeture de l'application Qt
        QApplication.quit()
    
    def keyPressEvent(self, event):
        """Gestion des touches (backup si hotkey global échoue)"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)
