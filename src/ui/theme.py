"""
WhisperFlow UI — Hegoatek Design System adaptation for PyQt6

Tokens centralisés : palette ink/cream/gold/rust, typographie Syne/DM Mono,
motion (durées, easings). Pas de hex codé en dur côté consommateurs :
tout passe par ces tokens.

Source : `da-hegoatek` skill → adaptation PyQt6 (QFontDatabase pour les fonts,
QEasingCurve pour les easings, QSS rgba() pour les alphas).
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QEasingCurve
from PyQt6.QtGui import QFont, QFontDatabase

from ..config import app_config

logger = logging.getLogger(__name__)


# ============================================================================
# Palette Hegoatek (tokens bruts)
# ============================================================================

INK = "#1C343A"  # deep teal — bg en dark mode
CREAM = "#FBFAF8"  # warm cream — text en dark mode
GOLD = "#D4A374"  # accent wayfinding — ready, active, live (both modes)
RUST = "#BF2C23"  # danger — errors, recording hot state


def rgba(hex_color: str, alpha: float) -> str:
    """
    Convertit '#RRGGBB' + alpha (0-1) en chaîne `rgba(r, g, b, a)` pour QSS.

    Usage côté QSS / styles :
        rgba(CREAM, 0.10)  →  'rgba(251, 250, 248, 0.100)'
    """
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


# ============================================================================
# Couleurs dérivées — pré-calculées pour le QSS
# ============================================================================
# LIGHT MODE Hegoatek : bg = cream, text = ink, accent = gold, danger = rust
# Cette inversion (vs dark mode) donne un résultat plus éditorial et plus
# lisible pour une fenêtre utilitaire toujours visible.

# Surfaces
BG = CREAM  # fond principal : cream warm
BG_ELEVATED = "#FFFFFF"  # cards : blanc pur, ressort sur cream
BG_SOFT = rgba(INK, 0.04)  # surface soft (wash ink transparent)
BG_HOVER = rgba(INK, 0.08)  # hover state

# Borders
BORDER = rgba(INK, 0.12)  # bordure subtile
BORDER_STRONG = rgba(INK, 0.20)  # bordure plus visible
BORDER_GOLD = rgba(GOLD, 0.65)  # focus, active (plus marqué en light)
BORDER_RUST = rgba(RUST, 0.50)  # error state

# Text
TEXT = INK
TEXT_DIM = rgba(INK, 0.65)  # texte secondaire, hints
TEXT_MUTED = rgba(INK, 0.45)  # placeholders, disabled
TEXT_FAINT = rgba(INK, 0.28)  # très discret (grid lines)

# Accent (gold) — wayfinding
ACCENT = GOLD
ACCENT_SOFT = rgba(GOLD, 0.18)  # backgrounds gold légers
ACCENT_STRONG = rgba(GOLD, 0.32)  # hover sur gold bg
ACCENT_GLOW = rgba(GOLD, 0.40)  # ombres/glow

# Danger (rust)
DANGER = RUST
DANGER_BG = rgba(RUST, 0.10)  # alert bg
DANGER_BORDER = rgba(RUST, 0.40)

# Recording state — rust vif
RECORDING = RUST
RECORDING_GLOW = rgba(RUST, 0.40)

# Hex "contrast" pour les custom-paint widgets (level_meter, gpu_gauge) qui
# construisent des QColor avec alpha : en light mode = INK, en dark = CREAM.
# Les widgets font `QColor(theme.CONTRAST_HEX).setAlphaF(...)`.
CONTRAST_HEX = INK


# ============================================================================
# Typographie — chargement des fonts bundlées
# ============================================================================

_FONT_DIR: Path = app_config.BASE_DIR / "assets" / "fonts"

_fonts_loaded: bool = False
_display_family: str = "Segoe UI"  # fallback
_mono_family: str = "Consolas"  # fallback


def load_fonts() -> tuple[str, str]:
    """
    Charge Syne (display) et DM Mono (metadata) dans QFontDatabase.
    Idempotent — les appels suivants retournent directement les familles.

    IMPORTANT : doit être appelé APRÈS création de QApplication.

    Returns:
        (display_family, mono_family) — noms de famille Qt à utiliser dans QSS.
    """
    global _fonts_loaded, _display_family, _mono_family

    if _fonts_loaded:
        return _display_family, _mono_family

    font_files = {
        "display": ["DMSans.ttf"],  # DM Sans variable — rondeur + pair avec DM Mono
        "mono": ["DMMono-Light.ttf", "DMMono-Regular.ttf", "DMMono-Medium.ttf"],
    }

    display_family: str | None = None
    mono_family: str | None = None

    for role, filenames in font_files.items():
        for filename in filenames:
            path = _FONT_DIR / filename
            if not path.exists():
                logger.warning("Font file missing: %s", path)
                continue

            font_id = QFontDatabase.addApplicationFont(str(path))
            if font_id < 0:
                logger.warning("Failed to load font: %s", path)
                continue

            families = QFontDatabase.applicationFontFamilies(font_id)
            if not families:
                continue

            family_name = families[0]
            if role == "display" and display_family is None:
                display_family = family_name
            elif role == "mono" and mono_family is None:
                mono_family = family_name

    if display_family:
        _display_family = display_family
        logger.info("Display font loaded: %s", display_family)
    else:
        logger.warning("DM Sans not loaded — falling back to %s", _display_family)

    if mono_family:
        _mono_family = mono_family
        logger.info("Mono font loaded: %s", mono_family)
    else:
        logger.warning("DM Mono not loaded — falling back to %s", _mono_family)

    _fonts_loaded = True
    return _display_family, _mono_family


def display_family() -> str:
    """Nom de famille à utiliser dans QSS pour le font-display (DM Sans)."""
    return _display_family if _fonts_loaded else "Segoe UI"


def mono_family() -> str:
    """Nom de famille à utiliser dans QSS pour le font-mono (DM Mono)."""
    return _mono_family if _fonts_loaded else "Consolas"


def display_font(size: int = 14, weight: QFont.Weight = QFont.Weight.Medium) -> QFont:
    """Crée un QFont display (Syne)."""
    f = QFont(display_family(), size)
    f.setWeight(weight)
    return f


def mono_font(size: int = 10, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """Crée un QFont mono (DM Mono)."""
    f = QFont(mono_family(), size)
    f.setWeight(weight)
    f.setStyleHint(QFont.StyleHint.Monospace)
    return f


# ============================================================================
# Motion — durées et easings
# ============================================================================

# Durations (millisecondes) — alignées avec --hg-dur-fast/base/slow
DUR_FAST = 150
DUR_BASE = 250
DUR_SLOW = 500

# Easings — approximations QEasingCurve des bezier Hegoatek
# --hg-ease        = cubic-bezier(0.16, 1, 0.3, 1)   ≈ OutExpo
# --hg-ease-bounce = cubic-bezier(0.34, 1.56, 0.64, 1) ≈ OutBack
EASE_HG: QEasingCurve.Type = QEasingCurve.Type.OutExpo
EASE_HG_BOUNCE: QEasingCurve.Type = QEasingCurve.Type.OutBack


def ease(curve_type: QEasingCurve.Type = EASE_HG) -> QEasingCurve:
    """Crée une QEasingCurve pour QPropertyAnimation."""
    return QEasingCurve(curve_type)


# ============================================================================
# Dimensions — spacing scale Hegoatek (multiples de 4)
# ============================================================================

SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 20
SPACE_6 = 24
SPACE_8 = 32
SPACE_10 = 40

# Border radius scale
RADIUS_SM = 6
RADIUS_MD = 8
RADIUS_LG = 12
RADIUS_XL = 16

# Window
WINDOW_DEFAULT_WIDTH = 480
WINDOW_DEFAULT_HEIGHT = 780
WINDOW_MIN_WIDTH = 420
WINDOW_MIN_HEIGHT = 720
