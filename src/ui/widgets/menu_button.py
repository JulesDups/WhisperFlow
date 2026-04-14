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

from ...i18n import t


class MenuButton(QPushButton):
    """
    Bouton discret `≡` ouvrant un QMenu contextualisé.

    Signaux :
      - configure_ptt_requested
      - toggle_floating_requested
      - toggle_recording_mode_requested
    """

    configure_ptt_requested = pyqtSignal()
    toggle_floating_requested = pyqtSignal()
    toggle_recording_mode_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("≡", parent)
        self.setObjectName("menuButton")
        self.setFixedSize(28, 28)
        self.setToolTip(t("menu_tooltip"))
        self._menu = QMenu(self)
        self._menu.setObjectName("appMenu")
        self._build_menu()
        self.clicked.connect(self._show_menu)

        # State (reflected in item labels)
        self._is_floating = True
        self._is_vad = False

    def _build_menu(self) -> None:
        self._action_ptt = self._menu.addAction(t("menu_change_hotkey"))
        self._action_ptt.triggered.connect(self.configure_ptt_requested.emit)

        self._action_mode = self._menu.addAction(t("menu_recording_mode", mode=t("recording_mode_hold")))
        self._action_mode.triggered.connect(self.toggle_recording_mode_requested.emit)

        self._action_floating = self._menu.addAction(t("menu_window_mode", mode=t("window_mode_floating")))
        self._action_floating.triggered.connect(self.toggle_floating_requested.emit)

    def _show_menu(self) -> None:
        # Positionne le menu sous le bouton, aligné à droite
        pos = self.mapToGlobal(self.rect().bottomRight())
        pos.setX(pos.x() - self._menu.sizeHint().width())
        self._menu.exec(pos)

    def set_floating(self, floating: bool) -> None:
        self._is_floating = floating
        mode = t("window_mode_floating") if floating else t("window_mode_normal")
        self._action_floating.setText(t("menu_window_mode", mode=mode))

    def set_recording_mode_vad(self, is_vad: bool) -> None:
        self._is_vad = is_vad
        mode = t("recording_mode_auto") if is_vad else t("recording_mode_hold")
        self._action_mode.setText(t("menu_recording_mode", mode=mode))
