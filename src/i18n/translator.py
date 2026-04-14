"""
WhisperFlow - Translation engine
Simple JSON-based i18n with English/French support.
"""

from __future__ import annotations

import locale
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_TRANSLATIONS: dict[str, dict[str, str]] = {}
_CURRENT_LANG: str = "en"
_TRANSLATIONS_DIR = Path(__file__).parent / "translations"


def _load_translations() -> None:
    global _TRANSLATIONS
    for lang_file in _TRANSLATIONS_DIR.glob("*.json"):
        import json

        lang = lang_file.stem
        try:
            with lang_file.open("r", encoding="utf-8") as f:
                _TRANSLATIONS[lang] = json.load(f)
        except Exception as e:
            logger.warning("Failed to load translation %s: %s", lang_file.name, e)


def _detect_system_language() -> str:
    try:
        lang = locale.getlocale()[0] or ""
        if lang.startswith("fr"):
            return "fr"
    except Exception:
        pass
    return "en"


def _init_language() -> None:
    global _CURRENT_LANG
    try:
        from ..utils.settings import settings_manager

        lang = settings_manager.get("ui_language", None)
        if lang in ("en", "fr"):
            _CURRENT_LANG = lang
            return
    except Exception:
        pass
    _CURRENT_LANG = _detect_system_language()


def get_ui_language() -> str:
    return _CURRENT_LANG


def set_ui_language(lang: str) -> None:
    global _CURRENT_LANG
    if lang in ("en", "fr"):
        _CURRENT_LANG = lang
        try:
            from ..utils.settings import settings_manager

            settings_manager.set("ui_language", lang)
        except Exception:
            pass


def t(key: str, **kwargs: object) -> str:
    """Translate a key, with optional format parameters."""
    lang_dict = _TRANSLATIONS.get(_CURRENT_LANG, {})
    text = lang_dict.get(key)
    if text is None:
        # Fall back to English
        text = _TRANSLATIONS.get("en", {}).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


# Initialize on import
_load_translations()
_init_language()
