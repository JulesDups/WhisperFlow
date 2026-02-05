"""
WhisperFlow Desktop - Key Capture Dialog
Dialogue pour capturer une nouvelle touche ou combinaison de touches
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ..config import ui_config


class KeyCaptureDialog(QDialog):
    """
    Dialogue modal pour capturer une nouvelle touche ou combinaison.

    Supporte:
    - Touches simples (F2, F3, etc.)
    - Combinaisons avec modificateurs (Ctrl+', Alt+Space, etc.)
    """

    key_captured = pyqtSignal(str)  # Émet le nom de la touche/combinaison capturée

    def __init__(self, current_key: str = "F2", parent=None):
        super().__init__(parent)
        self.current_key = current_key
        self.captured_key: str = ""
        self._current_modifiers: set[str] = set()

        self._setup_window()
        self._setup_ui()
        self._apply_styles()

    def _setup_window(self):
        """Configure la fenêtre"""
        self.setWindowTitle("Configurer le raccourci")
        self.setFixedSize(400, 220)
        self.setModal(True)

        # Style de fenêtre
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)

    def _setup_ui(self):
        """Construit l'interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Titre
        title = QLabel("🎹 Configurer le raccourci Push-to-Talk")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Instructions
        self.instruction_label = QLabel(
            f"Raccourci actuel: <b>{self.current_key.upper()}</b><br><br>"
            "Appuyez sur une touche ou combinaison...<br>"
            "<span style='color: #6C7086; font-size: 11px;'>Ex: F2, Ctrl+', Alt+Space</span>"
        )
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction_label.setWordWrap(True)
        layout.addWidget(self.instruction_label)

        # Label pour la touche capturée
        self.key_label = QLabel("")
        self.key_label.setObjectName("capturedKeyLabel")
        self.key_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_label.setMinimumHeight(50)
        layout.addWidget(self.key_label)

        # Boutons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        self.confirm_btn = QPushButton("Confirmer")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self._confirm)
        self.confirm_btn.setObjectName("confirmButton")
        button_layout.addWidget(self.confirm_btn)

        layout.addLayout(button_layout)

    def _apply_styles(self):
        """Applique les styles"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {ui_config.COLOR_BACKGROUND};
                border: 1px solid {ui_config.COLOR_SURFACE};
                border-radius: 12px;
            }}
            QLabel {{
                color: {ui_config.COLOR_TEXT};
            }}
            #capturedKeyLabel {{
                color: {ui_config.COLOR_ACCENT};
                background-color: {ui_config.COLOR_SURFACE};
                border-radius: 8px;
                padding: 8px;
            }}
            QPushButton {{
                background-color: {ui_config.COLOR_SURFACE};
                color: {ui_config.COLOR_TEXT};
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ui_config.COLOR_ACCENT};
                color: {ui_config.COLOR_BACKGROUND};
            }}
            #confirmButton {{
                background-color: {ui_config.COLOR_SUCCESS};
                color: {ui_config.COLOR_BACKGROUND};
            }}
            #confirmButton:disabled {{
                background-color: {ui_config.COLOR_TEXT_DIM};
            }}
        """)

    def keyPressEvent(self, event: QKeyEvent):
        """Capture la touche appuyée avec modificateurs"""
        key = event.key()
        modifiers = event.modifiers()

        # Ignore certaines touches
        if key in (Qt.Key.Key_unknown,):
            return

        # Collecte les modificateurs
        mod_parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            mod_parts.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            mod_parts.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            mod_parts.append("Shift")

        # Si c'est juste un modificateur seul, affiche-le mais ne confirme pas
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift, Qt.Key.Key_Meta, Qt.Key.Key_AltGr):
            if mod_parts:
                self.key_label.setText(" + ".join(mod_parts) + " + ...")
            return

        # Convertit en nom de touche
        key_name = self._key_to_name(key)

        if key_name:
            # Construit la combinaison complète
            if mod_parts:
                full_hotkey = "+".join(mod_parts) + "+" + key_name
                display_name = " + ".join(mod_parts) + " + " + key_name.upper()
            else:
                full_hotkey = key_name
                display_name = key_name.upper()

            self.captured_key = full_hotkey.lower()
            self.key_label.setText(display_name)
            self.confirm_btn.setEnabled(True)
            self.instruction_label.setText(
                f"Nouveau raccourci: <b>{display_name}</b><br><br>Cliquez sur Confirmer pour valider"
            )

    def _key_to_name(self, key: int) -> str:
        """Convertit un code Qt.Key en nom de touche"""
        # Touches de fonction
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            return f"f{key - Qt.Key.Key_F1 + 1}"

        # F13-F24
        if Qt.Key.Key_F13 <= key <= Qt.Key.Key_F24:
            return f"f{key - Qt.Key.Key_F13 + 13}"

        # Touches spéciales
        special_keys = {
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_CapsLock: "caps_lock",
            Qt.Key.Key_Shift: "shift",
            Qt.Key.Key_Control: "ctrl",
            Qt.Key.Key_Alt: "alt",
            Qt.Key.Key_Insert: "insert",
            Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Home: "home",
            Qt.Key.Key_End: "end",
            Qt.Key.Key_PageUp: "page_up",
            Qt.Key.Key_PageDown: "page_down",
            Qt.Key.Key_Pause: "pause",
            Qt.Key.Key_Print: "print_screen",
            Qt.Key.Key_ScrollLock: "scroll_lock",
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Enter: "enter",
            # Caractères spéciaux courants
            Qt.Key.Key_Apostrophe: "'",
            Qt.Key.Key_QuoteDbl: '"',
            Qt.Key.Key_Semicolon: ";",
            Qt.Key.Key_Colon: ":",
            Qt.Key.Key_Comma: ",",
            Qt.Key.Key_Period: ".",
            Qt.Key.Key_Slash: "/",
            Qt.Key.Key_Backslash: "\\",
            Qt.Key.Key_BracketLeft: "[",
            Qt.Key.Key_BracketRight: "]",
            Qt.Key.Key_Minus: "-",
            Qt.Key.Key_Equal: "=",
            Qt.Key.Key_Plus: "+",
            Qt.Key.Key_Asterisk: "*",
            Qt.Key.Key_At: "@",
            Qt.Key.Key_NumberSign: "#",
            Qt.Key.Key_Dollar: "$",
            Qt.Key.Key_Percent: "%",
            Qt.Key.Key_AsciiCircum: "^",
            Qt.Key.Key_Ampersand: "&",
            Qt.Key.Key_ParenLeft: "(",
            Qt.Key.Key_ParenRight: ")",
            Qt.Key.Key_Underscore: "_",
            Qt.Key.Key_QuoteLeft: "`",
            Qt.Key.Key_AsciiTilde: "~",
            # Touches spécifiques clavier français AZERTY
            Qt.Key.Key_twosuperior: "²",
            Qt.Key.Key_threesuperior: "³",
            Qt.Key.Key_degree: "°",
            Qt.Key.Key_sterling: "£",
            Qt.Key.Key_currency: "¤",
            Qt.Key.Key_mu: "µ",
            Qt.Key.Key_section: "§",
            Qt.Key.Key_Ugrave: "ù",
            Qt.Key.Key_Agrave: "à",
            Qt.Key.Key_Eacute: "é",
            Qt.Key.Key_Egrave: "è",
            Qt.Key.Key_Ccedilla: "ç",
            Qt.Key.Key_exclamdown: "¡",
            Qt.Key.Key_questiondown: "¿",
            Qt.Key.Key_Less: "<",
            Qt.Key.Key_Greater: ">",
        }

        if key in special_keys:
            return special_keys[key]

        # Touches alphanumériques
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            return chr(key).lower()

        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            return chr(key)

        # Pavé numérique
        if Qt.Key.Key_0 <= key - 0x01000000 <= Qt.Key.Key_9:
            return f"num_{key - Qt.Key.Key_0 - 0x01000000}"

        # Fallback: essaie de récupérer le caractère directement
        # Utile pour les touches non mappées explicitement
        try:
            from PyQt6.QtGui import QKeySequence

            seq = QKeySequence(key)
            char = seq.toString()
            if char and len(char) == 1 and char.isprintable():
                return char.lower()
        except (ImportError, ValueError):
            pass

        return ""

    def _confirm(self):
        """Confirme la sélection"""
        if self.captured_key:
            self.key_captured.emit(self.captured_key)
            self.accept()

    def get_key(self) -> str:
        """Retourne la touche capturée après fermeture"""
        return self.captured_key
