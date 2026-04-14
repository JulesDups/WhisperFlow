"""
MenuButton — menu discret "≡" pour les actions rares.

Contient :
- Changer le raccourci Push-to-Talk
- Basculer entre mode fenêtre flottant / normal
- Ouvrir/fermer l'historique
- Quitter

Remplace les boutons dispersés (window_mode_btn, config_key_btn) par un seul
point d'entrée. Le reste de l'UI reste propre.
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMenu, QPushButton, QWidget


class MenuButton(QPushButton):
    """
    Bouton discret `≡` ouvrant un QMenu contextualisé.

    Signaux :
      - configure_ptt_requested
      - toggle_floating_requested
      - toggle_recording_mode_requested
      - quit_requested
    """

    configure_ptt_requested = pyqtSignal()
    toggle_floating_requested = pyqtSignal()
    toggle_recording_mode_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("≡", parent)
        self.setObjectName("menuButton")
        self.setFixedSize(28, 28)
        self.setToolTip("Menu")
        self._menu = QMenu(self)
        self._menu.setObjectName("appMenu")
        self._build_menu()
        self.clicked.connect(self._show_menu)

        # State (reflected in item labels)
        self._is_floating = True
        self._is_vad = False

    def _build_menu(self) -> None:
        self._action_ptt = self._menu.addAction("Change hotkey…")
        self._action_ptt.triggered.connect(self.configure_ptt_requested.emit)

        self._action_mode = self._menu.addAction("Recording mode: Hold")
        self._action_mode.triggered.connect(self.toggle_recording_mode_requested.emit)

        self._action_floating = self._menu.addAction("Window: Floating")
        self._action_floating.triggered.connect(self.toggle_floating_requested.emit)

        self._menu.addSeparator()

        quit_action = self._menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_requested.emit)

    def _show_menu(self) -> None:
        # Positionne le menu sous le bouton, aligné à droite
        pos = self.mapToGlobal(self.rect().bottomRight())
        pos.setX(pos.x() - self._menu.sizeHint().width())
        self._menu.exec(pos)

    def set_floating(self, floating: bool) -> None:
        self._is_floating = floating
        self._action_floating.setText(f"Window: {'Floating' if floating else 'Normal'}")

    def set_recording_mode_vad(self, is_vad: bool) -> None:
        self._is_vad = is_vad
        self._action_mode.setText(f"Recording mode: {'Auto (VAD)' if is_vad else 'Hold'}")
