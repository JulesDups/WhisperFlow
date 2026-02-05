"""
WhisperFlow Desktop - Global Hotkey Listener
Écoute les raccourcis clavier globaux avec pynput
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from pynput import keyboard

from ..config import hotkey_config

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class HotkeyBinding:
    """Liaison d'un raccourci"""

    key: str
    modifiers: frozenset[str] = field(default_factory=frozenset)  # ctrl, alt, shift
    on_press: Callable[[], None] | None = None
    on_release: Callable[[], None] | None = None
    description: str = ""


def parse_hotkey(hotkey_str: str) -> tuple[str, frozenset[str]]:
    """
    Parse une chaîne de raccourci en touche + modificateurs.

    Exemples:
        "ctrl+'" -> ("'", frozenset({"ctrl"}))
        "ctrl+shift+f2" -> ("f2", frozenset({"ctrl", "shift"}))
        "f2" -> ("f2", frozenset())
    """
    parts = hotkey_str.lower().split("+")
    modifiers = set()
    key = parts[-1]  # La dernière partie est la touche principale

    for part in parts[:-1]:
        part = part.strip()
        if part in ("ctrl", "control", "ctrl_l", "ctrl_r"):
            modifiers.add("ctrl")
        elif part in ("alt", "alt_l", "alt_r"):
            modifiers.add("alt")
        elif part in ("shift", "shift_l", "shift_r"):
            modifiers.add("shift")
        elif part in ("cmd", "win", "super", "meta"):
            modifiers.add("cmd")

    return key.strip(), frozenset(modifiers)


class GlobalHotkeyListener:
    """
    Écouteur de raccourcis clavier globaux.

    Permet de capturer des touches même quand l'application n'est pas au focus.
    Utilise pynput pour la compatibilité Windows/macOS/Linux.

    Features:
    - Push-to-Talk (appui maintenu)
    - Toggle (appui simple)
    - Combinaisons de touches
    """

    __slots__ = (
        "_listener",
        "_bindings",
        "_pressed_keys",
        "_active_modifiers",
        "_lock",
        "_is_running",
        "_active_bindings",
        "_executor",
    )

    # Touches modificatrices
    MODIFIER_KEYS = {
        "ctrl_l": "ctrl",
        "ctrl_r": "ctrl",
        "ctrl": "ctrl",
        "alt_l": "alt",
        "alt_r": "alt",
        "alt": "alt",
        "alt_gr": "alt",
        "shift_l": "shift",
        "shift_r": "shift",
        "shift": "shift",
        "cmd": "cmd",
        "cmd_l": "cmd",
        "cmd_r": "cmd",
    }

    # Virtual key code mapping (Windows)
    VK_MAP = {
        0xDE: "'",  # VK_OEM_7 (apostrophe sur QWERTY)
        0xC0: "`",  # VK_OEM_3 (backtick)
        0xDC: "\\",  # VK_OEM_5 (backslash)
        0xDD: "²",  # VK_OEM_6 (² sur AZERTY français)
    }

    def __init__(self) -> None:
        # Listener pynput
        self._listener: keyboard.Listener | None = None

        # Bindings enregistrés: clé = "modifiers:key" pour unicité
        self._bindings: dict[str, HotkeyBinding] = {}

        # État des touches
        self._pressed_keys: set[str] = set()
        self._active_modifiers: set[str] = set()  # ctrl, alt, shift actifs
        self._lock = threading.Lock()
        # Bindings actuellement actifs (clé de binding)
        self._active_bindings: set[str] = set()

        # État du listener
        self._is_running = False
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="hotkey")

    def register(
        self,
        hotkey: str,
        on_press: Callable[[], None] | None = None,
        on_release: Callable[[], None] | None = None,
        description: str = "",
    ) -> None:
        """
        Enregistre un nouveau raccourci

        Args:
            hotkey: Raccourci (ex: "f2", "ctrl+'", "ctrl+shift+space")
            on_press: Callback appelé lors de l'appui
            on_release: Callback appelé lors du relâchement
            description: Description du raccourci
        """
        key, modifiers = parse_hotkey(hotkey)
        binding_key = self._make_binding_key(key, modifiers)

        binding = HotkeyBinding(
            key=key, modifiers=modifiers, on_press=on_press, on_release=on_release, description=description
        )
        self._bindings[binding_key] = binding
        logger.info("Raccourci enregistre: %s (%s)", hotkey, description)

    def unregister(self, hotkey: str) -> None:
        """Supprime un raccourci"""
        key, modifiers = parse_hotkey(hotkey)
        binding_key = self._make_binding_key(key, modifiers)
        self._bindings.pop(binding_key, None)

    def _make_binding_key(self, key: str, modifiers: frozenset[str]) -> str:
        """Crée une clé unique pour un binding"""
        mod_str = "+".join(sorted(modifiers)) if modifiers else ""
        return f"{mod_str}:{key}" if mod_str else f":{key}"

    def _normalize_key(self, key) -> str | None:
        """
        Normalise une touche pynput vers un nom string
        """
        try:
            # Touches spéciales (F1, F2, Ctrl, etc.)
            if hasattr(key, "name") and key.name:
                return key.name.lower()

            # Touches caractères (inclut les caractères spéciaux comme ², é, etc.)
            if hasattr(key, "char") and key.char:
                char = key.char
                # Normalise certains caractères pour la comparaison
                return char.lower() if char.isalpha() else char

            # Virtual key code (Windows) - pour les touches non mappées
            if hasattr(key, "vk") and key.vk:
                if key.vk in self.VK_MAP:
                    return self.VK_MAP[key.vk]
                # Retourne le code comme chaîne pour debug
                logger.debug("VK code non mappe: 0x%02X", key.vk)

            # Fallback
            key_str = str(key).lower().replace("key.", "").replace("'", "")
            if key_str and len(key_str) == 1:
                return key_str
            return key_str if key_str else None

        except Exception:
            return None

    def _on_press(self, key) -> None:
        """Callback interne pour les appuis"""
        key_name = self._normalize_key(key)
        if not key_name:
            return
        with self._lock:
            # Met à jour les modificateurs actifs
            if key_name in self.MODIFIER_KEYS:
                self._active_modifiers.add(self.MODIFIER_KEYS[key_name])

            # Évite les répétitions (key repeat)
            if key_name in self._pressed_keys:
                return
            self._pressed_keys.add(key_name)

            # Détecte tous les bindings satisfaits par l'état courant des touches
            current_active = set()
            for bkey, binding in self._bindings.items():
                try:
                    # binding.key doit être présent dans pressed_keys (single-key bindings)
                    # et ses modifiers doivent être un sous-ensemble des modifiers actifs
                    if binding.key in self._pressed_keys and binding.modifiers.issubset(self._active_modifiers):
                        current_active.add(bkey)
                except Exception:
                    pass

            # Déclenche on_press pour les bindings nouvellement actifs
            new_actives = current_active - self._active_bindings
            for bkey in new_actives:
                binding = self._bindings.get(bkey)
                if binding and binding.on_press:
                    try:
                        self._executor.submit(binding.on_press)
                    except Exception:
                        pass

            # Met à jour l'ensemble des bindings actifs
            self._active_bindings = current_active

    def _on_release(self, key) -> None:
        """Callback interne pour les relâchements"""
        key_name = self._normalize_key(key)
        if not key_name:
            return
        with self._lock:
            # Retire la touche pressée
            self._pressed_keys.discard(key_name)

            # Met à jour les modificateurs actifs
            if key_name in self.MODIFIER_KEYS:
                self._active_modifiers.discard(self.MODIFIER_KEYS[key_name])

            # Recalcule les bindings satisfaits après ce relâchement
            current_active = set()
            for bkey, binding in self._bindings.items():
                try:
                    if binding.key in self._pressed_keys and binding.modifiers.issubset(self._active_modifiers):
                        current_active.add(bkey)
                except Exception:
                    pass

            # Les bindings qui étaient actifs mais ne le sont plus -> on_release
            to_release = set(self._active_bindings) - current_active
            for bkey in to_release:
                binding = self._bindings.get(bkey)
                if binding and binding.on_release:
                    try:
                        self._executor.submit(binding.on_release)
                    except Exception:
                        pass

            # Met à jour l'ensemble des bindings actifs
            self._active_bindings = current_active

    def start(self):
        """Démarre l'écoute des raccourcis"""
        if self._is_running:
            return

        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        # Marque le thread comme daemon pour qu'il se termine avec le programme principal
        self._listener.daemon = True
        self._listener.start()
        self._is_running = True
        logger.info("Ecoute des raccourcis globaux activee")

    def stop(self):
        """Arrête l'écoute"""
        if not self._is_running:
            return

        self._is_running = False

        if self._listener:
            try:
                self._listener.stop()
                # Attend un peu que le thread se termine
                self._listener.join(timeout=1.0)
            except Exception as e:
                logger.warning("Erreur arret listener: %s", e)
            finally:
                self._listener = None
        self._executor.shutdown(wait=False)

        with self._lock:
            self._pressed_keys.clear()
            self._active_modifiers.clear()

        logger.info("Ecoute des raccourcis globaux desactivee")

    def is_key_pressed(self, key: str) -> bool:
        """Vérifie si une touche est actuellement pressée"""
        with self._lock:
            return key.lower() in self._pressed_keys

    @property
    def is_running(self) -> bool:
        """Retourne True si le listener est actif"""
        return self._is_running

    @property
    def bindings(self) -> list[HotkeyBinding]:
        """Retourne la liste des bindings enregistrés"""
        return list(self._bindings.values())


class PushToTalkController:
    """
    Contrôleur spécialisé pour le Push-to-Talk

    Simplifie la gestion du mode Push-to-Talk avec:
    - Activation sur appui
    - Désactivation sur relâchement
    - Callbacks pour les transitions d'état
    """

    def __init__(
        self,
        key: str = hotkey_config.PUSH_TO_TALK_KEY,
        on_start: Callable[[], None] | None = None,
        on_stop: Callable[[], None] | None = None,
    ):
        self.key = key
        self.on_start = on_start
        self.on_stop = on_stop

        self._listener = GlobalHotkeyListener()
        self._is_active = False
        self._lock = threading.Lock()

    def _handle_press(self):
        """Gère l'appui de la touche PTT"""
        with self._lock:
            if self._is_active:
                return
            self._is_active = True

        if self.on_start:
            self.on_start()

    def _handle_release(self):
        """Gère le relâchement de la touche PTT"""
        with self._lock:
            if not self._is_active:
                return
            self._is_active = False

        if self.on_stop:
            self.on_stop()

    def start(self):
        """Démarre le contrôleur PTT"""
        self._listener.register(
            key=self.key,
            on_press=self._handle_press,
            on_release=self._handle_release,
            description=f"Push-to-Talk ({self.key.upper()})",
        )
        self._listener.start()

    def stop(self):
        """Arrête le contrôleur PTT"""
        self._listener.stop()

        with self._lock:
            self._is_active = False

    @property
    def is_active(self) -> bool:
        """Retourne True si le PTT est actuellement actif"""
        with self._lock:
            return self._is_active


# Test standalone
if __name__ == "__main__":
    print("🎹 Test du listener de raccourcis globaux")
    print("-" * 40)
    print("Appuyez sur F2 pour tester le Push-to-Talk")
    print("Appuyez sur ESC pour quitter")
    print()

    should_exit = False

    def on_ptt_start():
        print("🔴 ENREGISTREMENT...")

    def on_ptt_stop():
        print("⬜ Arrêt enregistrement")

    def on_escape():
        global should_exit
        should_exit = True
        print("\n👋 Au revoir!")

    # Crée le listener
    listener = GlobalHotkeyListener()

    listener.register("f2", on_press=on_ptt_start, on_release=on_ptt_stop)
    listener.register("esc", on_press=on_escape)

    listener.start()

    # Boucle principale
    import time

    while not should_exit:
        time.sleep(0.1)

    listener.stop()
