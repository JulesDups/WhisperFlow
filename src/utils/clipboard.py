"""
WhisperFlow Desktop - Clipboard & Text Input Utility
Gestion du presse-papier système et frappe automatique
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

import pyperclip
from pynput.keyboard import Controller as KeyboardController, Key


class ClipboardManager:
    """
    Gestionnaire du presse-papier avec fonctionnalités avancées.
    
    Features:
    - Copie vers presse-papier
    - Historique des copies (optionnel)
    - Notification de copie
    """
    
    __slots__ = ('_lock',)
    
    # Taille maximum du texte à copier (sécurité)
    MAX_TEXT_SIZE: int = 100_000  # 100 KB
    
    def __init__(self, max_history: int = 0) -> None:
        # Historique désactivé pour éviter les fuites mémoire
        self._lock = threading.Lock()
    
    def copy(self, text: str) -> bool:
        """
        Copie le texte dans le presse-papier.
        
        Args:
            text: Texte à copier
            
        Returns:
            True si copié avec succès
        """
        if not text:
            return False
        
        # Limite la taille du texte (sécurité)
        if len(text) > self.MAX_TEXT_SIZE:
            text = text[:self.MAX_TEXT_SIZE]
        
        try:
            pyperclip.copy(text)
            return True
            
        except Exception as e:
            print(f"❌ Erreur clipboard: {e}")
            return False
    
    def paste(self) -> str | None:
        """
        Récupère le contenu du presse-papier.
        
        Returns:
            Contenu du presse-papier ou None
        """
        try:
            return pyperclip.paste()
        except Exception:
            return None
    
    @staticmethod
    def is_available() -> bool:
        """Vérifie si le presse-papier est disponible"""
        try:
            pyperclip.paste()
            return True
        except Exception:
            return False


class TextTyper:
    """
    Simule la frappe clavier pour insérer du texte
    dans l'application active.
    """
    
    __slots__ = ('keyboard', 'delay', '_lock')
    
    # Délais optimisés pour rapidité (réduits au minimum fiable)
    CLIPBOARD_READY_DELAY: float = 0.01  # 10ms suffit
    PASTE_COMPLETE_DELAY: float = 0.02   # 20ms suffit
    
    def __init__(self, delay: float = 0.01) -> None:
        self.keyboard = KeyboardController()
        self.delay = delay
        self._lock = threading.Lock()
    
    def type_text(self, text: str, use_clipboard: bool = True) -> bool:
        """
        Tape le texte dans l'application active.
        
        Args:
            text: Texte à taper
            use_clipboard: Si True, utilise copier/coller (plus rapide et fiable)
            
        Returns:
            True si succès
        """
        if not text:
            return False
        
        with self._lock:
            try:
                if use_clipboard:
                    return self._paste_text(text)
                else:
                    return self._type_char_by_char(text)
            except Exception as e:
                print(f"❌ Erreur frappe texte: {e}")
                return False
    
    def _paste_text(self, text: str) -> bool:
        """Colle le texte via le presse-papier (méthode rapide)"""
        # Sauvegarde le presse-papier actuel
        old_clipboard: str | None = None
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            pass
        
        try:
            # Copie le nouveau texte
            pyperclip.copy(text)
            time.sleep(self.CLIPBOARD_READY_DELAY)
            
            # Simule Ctrl+V
            self.keyboard.press(Key.ctrl)
            self.keyboard.press('v')
            self.keyboard.release('v')
            self.keyboard.release(Key.ctrl)
            
            time.sleep(self.PASTE_COMPLETE_DELAY)
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur paste: {e}")
            return False
    
    def _type_char_by_char(self, text: str) -> bool:
        """Tape caractère par caractère (méthode lente mais sans clipboard)"""
        for char in text:
            self.keyboard.type(char)
            if self.delay > 0:
                time.sleep(self.delay)
        return True
    
    def press_key(self, key) -> None:
        """Appuie sur une touche"""
        try:
            self.keyboard.press(key)
            self.keyboard.release(key)
        except Exception:
            pass


# Instances globales (singletons)
clipboard = ClipboardManager()
text_typer = TextTyper()


def copy_to_clipboard(text: str) -> bool:
    """Fonction raccourci pour copier"""
    return clipboard.copy(text)


def paste_from_clipboard() -> str | None:
    """Fonction raccourci pour coller"""
    return clipboard.paste()


def type_text(text: str, use_clipboard: bool = True) -> bool:
    """Fonction raccourci pour taper du texte"""
    return text_typer.type_text(text, use_clipboard)
