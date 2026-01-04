"""
WhisperFlow Desktop - Styles UI
Définition des styles CSS pour PyQt6
Style moderne inspiré macOS/Catppuccin
"""

import sys
sys.path.append('../..')
from config import ui_config


def get_main_stylesheet() -> str:
    """Retourne la feuille de style principale"""
    return f"""
    /* ============================================
       WhisperFlow - Main Stylesheet
       ============================================ */
    
    /* Widget principal */
    QWidget {{
        background-color: {ui_config.COLOR_BACKGROUND};
        color: {ui_config.COLOR_TEXT};
        font-family: "Segoe UI", "SF Pro Display", Arial, sans-serif;
        font-size: 13px;
    }}
    
    /* Fenêtre principale */
    QMainWindow {{
        background-color: transparent;
    }}
    
    /* Frame central avec coins arrondis */
    #centralFrame {{
        background-color: {ui_config.COLOR_BACKGROUND};
        border-radius: {ui_config.BORDER_RADIUS}px;
        border: 1px solid {ui_config.COLOR_SURFACE};
    }}
    
    /* Labels */
    QLabel {{
        color: {ui_config.COLOR_TEXT};
        background-color: transparent;
        padding: 2px;
    }}
    
    QLabel#titleLabel {{
        font-size: 18px;
        font-weight: bold;
        color: {ui_config.COLOR_ACCENT};
    }}
    
    QLabel#statusLabel {{
        font-size: 14px;
        color: {ui_config.COLOR_TEXT_DIM};
        padding: 8px;
    }}
    
    QLabel#transcriptionLabel {{
        font-size: 14px;
        color: {ui_config.COLOR_TEXT};
        background-color: {ui_config.COLOR_SURFACE};
        border-radius: 8px;
        padding: 12px;
        min-height: 60px;
    }}
    
    QLabel#hotkeyLabel {{
        font-size: 11px;
        color: {ui_config.COLOR_TEXT_DIM};
    }}
    
    /* Indicateur d'état */
    #statusIndicator {{
        background-color: {ui_config.COLOR_TEXT_DIM};
        border-radius: 6px;
        min-width: 12px;
        min-height: 12px;
        max-width: 12px;
        max-height: 12px;
    }}
    
    #statusIndicator[state="ready"] {{
        background-color: {ui_config.COLOR_SUCCESS};
    }}
    
    #statusIndicator[state="recording"] {{
        background-color: {ui_config.COLOR_RECORDING};
    }}
    
    #statusIndicator[state="processing"] {{
        background-color: {ui_config.COLOR_PROCESSING};
    }}
    
    #statusIndicator[state="loading"] {{
        background-color: {ui_config.COLOR_ACCENT};
    }}
    
    /* Barre de progression audio */
    QProgressBar {{
        background-color: {ui_config.COLOR_SURFACE};
        border-radius: 4px;
        height: 8px;
        text-align: center;
    }}
    
    QProgressBar::chunk {{
        background-color: {ui_config.COLOR_ACCENT};
        border-radius: 4px;
    }}
    
    QProgressBar[state="recording"]::chunk {{
        background-color: {ui_config.COLOR_RECORDING};
    }}
    
    /* Indicateur VRAM */
    #vramIndicator {{
        background-color: transparent;
    }}
    
    #vramIcon {{
        font-size: 12px;
        color: {ui_config.COLOR_TEXT_DIM};
    }}
    
    #vramText {{
        font-size: 10px;
        color: {ui_config.COLOR_TEXT_DIM};
    }}
    
    #vramBar {{
        background-color: {ui_config.COLOR_SURFACE};
        border-radius: 3px;
        height: 6px;
    }}
    
    #vramBar::chunk {{
        background-color: {ui_config.COLOR_SUCCESS};
        border-radius: 3px;
    }}
    
    #vramBar[level="warning"]::chunk {{
        background-color: #FAB387;
    }}
    
    #vramBar[level="critical"]::chunk {{
        background-color: {ui_config.COLOR_RECORDING};
    }}
    
    /* Boutons */
    QPushButton {{
        background-color: {ui_config.COLOR_SURFACE};
        color: {ui_config.COLOR_TEXT};
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
    }}
    
    QPushButton:hover {{
        background-color: {ui_config.COLOR_ACCENT};
        color: {ui_config.COLOR_BACKGROUND};
    }}
    
    QPushButton:pressed {{
        background-color: {ui_config.COLOR_PROCESSING};
    }}
    
    QPushButton#closeButton {{
        background-color: transparent;
        color: {ui_config.COLOR_TEXT_DIM};
        font-size: 16px;
        font-weight: bold;
        border-radius: 12px;
        min-width: 24px;
        max-width: 24px;
        min-height: 24px;
        max-height: 24px;
        padding: 0px;
    }}
    
    QPushButton#closeButton:hover {{
        background-color: {ui_config.COLOR_RECORDING};
        color: white;
    }}
    
    QPushButton#copyButton {{
        background-color: {ui_config.COLOR_SUCCESS};
        color: {ui_config.COLOR_BACKGROUND};
    }}
    
    QPushButton#copyButton:hover {{
        background-color: #b5eeac;
    }}
    
    QPushButton#configKeyButton {{
        background-color: transparent;
        color: {ui_config.COLOR_TEXT_DIM};
        font-size: 12px;
        border-radius: 6px;
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
        padding: 0px;
    }}
    
    QPushButton#configKeyButton:hover {{
        background-color: {ui_config.COLOR_SURFACE};
        color: {ui_config.COLOR_ACCENT};
    }}
    
    QPushButton#formatButton {{
        background-color: {ui_config.COLOR_SURFACE};
        color: {ui_config.COLOR_TEXT};
        font-size: 12px;
        border-radius: 8px;
        padding: 6px 12px;
    }}
    
    QPushButton#formatButton:hover {{
        background-color: {ui_config.COLOR_ACCENT};
        color: {ui_config.COLOR_BACKGROUND};
    }}
    
    QPushButton#formatButton:checked {{
        background-color: {ui_config.COLOR_SUCCESS};
        color: {ui_config.COLOR_BACKGROUND};
    }}
    
    QPushButton#windowModeButton {{
        background-color: {ui_config.COLOR_SURFACE};
        color: {ui_config.COLOR_TEXT};
        font-size: 12px;
        border-radius: 8px;
        padding: 6px 12px;
    }}
    
    QPushButton#windowModeButton:hover {{
        background-color: {ui_config.COLOR_ACCENT};
        color: {ui_config.COLOR_BACKGROUND};
    }}
    
    /* Barre de titre personnalisée */
    #titleBar {{
        background-color: transparent;
        border-top-left-radius: {ui_config.BORDER_RADIUS}px;
        border-top-right-radius: {ui_config.BORDER_RADIUS}px;
    }}
    
    /* Zone de contenu */
    #contentArea {{
        background-color: transparent;
        padding: 16px;
    }}
    
    /* Tooltip */
    QToolTip {{
        background-color: {ui_config.COLOR_SURFACE};
        color: {ui_config.COLOR_TEXT};
        border: 1px solid {ui_config.COLOR_TEXT_DIM};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    """


def get_recording_pulse_style() -> str:
    """Style pour l'animation de pulsation pendant l'enregistrement"""
    return f"""
    @keyframes pulse {{
        0% {{ opacity: 1; }}
        50% {{ opacity: 0.5; }}
        100% {{ opacity: 1; }}
    }}
    """


def get_state_colors() -> dict:
    """Retourne les couleurs par état"""
    return {
        "ready": ui_config.COLOR_SUCCESS,
        "recording": ui_config.COLOR_RECORDING,
        "processing": ui_config.COLOR_PROCESSING,
        "loading": ui_config.COLOR_ACCENT,
        "error": "#F38BA8",
    }
