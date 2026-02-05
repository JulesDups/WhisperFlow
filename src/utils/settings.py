"""
WhisperFlow Desktop - User Settings
Gestion des paramètres utilisateur persistants
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..config import OutputMode, WindowMode, app_config, hotkey_config

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class UserSettings:
    """Paramètres utilisateur modifiables"""

    push_to_talk_key: str = "f2"
    output_mode: str = OutputMode.TYPE
    language: str = "fr"

    # Smart Formatting
    smart_formatting_enabled: bool = True
    smart_formatting_level: str = "basic"  # "none", "basic", "smart"

    # Mode fenêtre
    window_mode: str = WindowMode.FLOATING
    window_position_x: int = -1  # -1 = centré
    window_position_y: int = -1

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserSettings:
        """Crée une instance depuis un dictionnaire (ignores clés inconnues)"""
        # Valide les valeurs pour éviter injection
        ptt_key = str(data.get("push_to_talk_key", "f2"))[:50]
        output_mode = data.get("output_mode", OutputMode.TYPE)
        language = str(data.get("language", "fr"))[:10]

        # Valide output_mode
        try:
            output_mode = OutputMode(output_mode)
        except ValueError:
            output_mode = OutputMode.TYPE

        # Smart Formatting
        smart_enabled = bool(data.get("smart_formatting_enabled", True))
        smart_level = str(data.get("smart_formatting_level", "basic"))[:10]
        if smart_level not in ("none", "basic", "smart"):
            smart_level = "basic"

        # Mode fenêtre
        window_mode = str(data.get("window_mode", WindowMode.FLOATING))[:20]
        try:
            window_mode = WindowMode(window_mode)
        except ValueError:
            window_mode = WindowMode.FLOATING

        window_x = int(data.get("window_position_x", -1))
        window_y = int(data.get("window_position_y", -1))

        return cls(
            push_to_talk_key=ptt_key,
            output_mode=output_mode,
            language=language,
            smart_formatting_enabled=smart_enabled,
            smart_formatting_level=smart_level,
            window_mode=window_mode,
            window_position_x=window_x,
            window_position_y=window_y,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dictionnaire"""
        return asdict(self)


class SettingsManager:
    """
    Gestionnaire de paramètres utilisateur.

    Sauvegarde et charge les préférences depuis un fichier JSON.
    Thread-safe pour les accès concurrents.
    """

    __slots__ = ("_settings_file", "_settings", "_lock", "_callbacks", "_save_timer", "_save_delay")

    # Taille max du fichier de config (protection contre fichiers malveillants)
    MAX_CONFIG_SIZE: int = 10 * 1024  # 10 KB

    def __init__(self, settings_file: Path | None = None) -> None:
        self._settings_file = settings_file or (app_config.BASE_DIR / "user_settings.json")
        self._settings = UserSettings()
        self._lock = threading.RLock()  # RLock pour permettre réentrance
        self._callbacks: list[Callable[[str, Any], None]] = []
        self._save_timer: threading.Timer | None = None
        self._save_delay: float = 0.5  # 500ms debounce

        # Charge les paramètres existants
        self.load()

    def load(self) -> bool:
        """Charge les paramètres depuis le fichier"""
        with self._lock:
            try:
                if not self._settings_file.exists():
                    return False

                # Vérifie la taille du fichier (sécurité)
                file_size = self._settings_file.stat().st_size
                if file_size > self.MAX_CONFIG_SIZE:
                    logger.warning("Fichier de config trop volumineux (%d bytes), ignore", file_size)
                    return False

                with self._settings_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        raise ValueError("Format de configuration invalide")
                    self._settings = UserSettings.from_dict(data)

                logger.info("Parametres charges depuis %s", self._settings_file.name)
                return True

            except json.JSONDecodeError as e:
                logger.warning("Erreur JSON dans les parametres: %s", e)
            except Exception as e:
                logger.warning("Erreur chargement parametres: %s", e)
        return False

    def save(self) -> bool:
        """Sauvegarde les paramètres dans le fichier"""
        with self._lock:
            try:
                # Écrit dans un fichier temporaire puis renomme (atomique)
                temp_file = self._settings_file.with_suffix(".tmp")
                with temp_file.open("w", encoding="utf-8") as f:
                    json.dump(self._settings.to_dict(), f, indent=2, ensure_ascii=False)

                # Renommage atomique
                temp_file.replace(self._settings_file)
                logger.debug("Parametres sauvegardes")
                return True

            except Exception as e:
                logger.error("Erreur sauvegarde parametres: %s", e)
                # Nettoie le fichier temporaire si présent
                try:
                    temp_file.unlink(missing_ok=True)
                except OSError:
                    pass
                return False

    @property
    def settings(self) -> UserSettings:
        """Retourne les paramètres actuels"""
        with self._lock:
            return self._settings

    def get(self, key: str, default: Any = None) -> Any:
        """Récupère une valeur de paramètre"""
        with self._lock:
            return getattr(self._settings, key, default)

    def set(self, key: str, value: Any, *, save: bool = True) -> None:
        """Définit une valeur de paramètre"""
        with self._lock:
            if not hasattr(self._settings, key):
                return
            setattr(self._settings, key, value)

        if save:
            self._schedule_save()

        # Notifie les callbacks (hors du lock)
        for callback in self._callbacks:
            try:
                callback(key, value)
            except Exception:
                pass

    def _schedule_save(self) -> None:
        """Planifie une sauvegarde avec debounce de 500ms"""
        if self._save_timer is not None:
            self._save_timer.cancel()
        self._save_timer = threading.Timer(self._save_delay, self.save)
        self._save_timer.daemon = True
        self._save_timer.start()

    def on_change(self, callback: Callable[[str, Any], None]) -> None:
        """Enregistre un callback appelé lors des changements"""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[str, Any], None]) -> None:
        """Supprime un callback"""
        try:
            self._callbacks.remove(callback)
        except ValueError:
            pass


# Instance globale
settings_manager = SettingsManager()


def get_ptt_key() -> str:
    """Retourne la touche Push-to-Talk configurée"""
    return settings_manager.get("push_to_talk_key", hotkey_config.PUSH_TO_TALK_KEY)


def set_ptt_key(key: str) -> None:
    """Définit la touche Push-to-Talk"""
    settings_manager.set("push_to_talk_key", key)


def get_language() -> str:
    """Retourne la langue configurée pour la transcription"""
    return settings_manager.get("language", "fr")


def set_language(language: str) -> None:
    """Définit la langue de transcription"""
    settings_manager.set("language", language)


def get_smart_formatting() -> tuple[bool, str]:
    """Retourne (enabled, level) pour le smart formatting"""
    enabled = settings_manager.get("smart_formatting_enabled", True)
    level = settings_manager.get("smart_formatting_level", "basic")
    return enabled, level


def set_smart_formatting(enabled: bool, level: str = "basic") -> None:
    """Configure le smart formatting"""
    settings_manager.set("smart_formatting_enabled", enabled, save=False)
    settings_manager.set("smart_formatting_level", level)


def get_window_mode() -> str:
    """Retourne le mode de fenêtre ('floating' ou 'normal')"""
    return settings_manager.get("window_mode", "floating")


def set_window_mode(mode: str) -> None:
    """Définit le mode de fenêtre"""
    try:
        WindowMode(mode)
        settings_manager.set("window_mode", mode)
    except ValueError:
        pass


def get_window_position() -> tuple[int, int]:
    """Retourne la position de la fenêtre sauvegardée (-1, -1 si non définie)"""
    x = settings_manager.get("window_position_x", -1)
    y = settings_manager.get("window_position_y", -1)
    return x, y


def set_window_position(x: int, y: int) -> None:
    """Sauvegarde la position de la fenêtre"""
    settings_manager.set("window_position_x", x, save=False)
    settings_manager.set("window_position_y", y)


def get_sound_enabled() -> bool:
    """Retourne si les sons sont activés"""
    return settings_manager.get("sound_enabled", True)


def set_sound_enabled(enabled: bool) -> None:
    """Active/désactive les sons"""
    settings_manager.set("sound_enabled", enabled)


def get_history_enabled() -> bool:
    """Retourne si l'historique est activé"""
    return settings_manager.get("history_enabled", True)


def set_history_enabled(enabled: bool) -> None:
    """Active/désactive l'historique"""
    settings_manager.set("history_enabled", enabled)
