"""
WhisperFlow Desktop - Transcription History
Historique des transcriptions avec persistance optionnelle
"""

from __future__ import annotations

import json
import threading
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

import sys
sys.path.append('..')
from config import app_config


@dataclass(slots=True)
class TranscriptionEntry:
    """Entrée dans l'historique des transcriptions"""
    text: str
    timestamp: str
    duration: float
    language: str
    processing_time: float
    
    @classmethod
    def create(
        cls,
        text: str,
        duration: float,
        language: str,
        processing_time: float
    ) -> TranscriptionEntry:
        """Crée une nouvelle entrée avec timestamp automatique"""
        return cls(
            text=text,
            timestamp=datetime.now().isoformat(),
            duration=duration,
            language=language,
            processing_time=processing_time
        )
    
    @property
    def formatted_time(self) -> str:
        """Retourne l'heure formatée"""
        try:
            dt = datetime.fromisoformat(self.timestamp)
            return dt.strftime("%H:%M:%S")
        except:
            return self.timestamp[:8]
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> TranscriptionEntry:
        """Crée depuis un dictionnaire"""
        return cls(
            text=str(data.get("text", "")),
            timestamp=str(data.get("timestamp", "")),
            duration=float(data.get("duration", 0)),
            language=str(data.get("language", "fr")),
            processing_time=float(data.get("processing_time", 0))
        )


class TranscriptionHistory:
    """
    Historique des transcriptions en mémoire.
    
    Features:
    - Limite de taille configurable
    - Sauvegarde optionnelle sur disque
    - Thread-safe
    """
    
    __slots__ = ('_history', '_max_size', '_lock', '_file_path', '_auto_save')
    
    DEFAULT_MAX_SIZE = 50
    HISTORY_FILENAME = "transcription_history.json"
    
    def __init__(
        self,
        max_size: int = DEFAULT_MAX_SIZE,
        persist: bool = False
    ) -> None:
        self._history: deque[TranscriptionEntry] = deque(maxlen=max_size)
        self._max_size = max_size
        self._lock = threading.Lock()
        self._auto_save = persist
        
        if persist:
            self._file_path = app_config.CACHE_DIR / self.HISTORY_FILENAME
            self._load()
        else:
            self._file_path = None
    
    def add(self, text: str, processing_time: float = 0.0, duration: float = 0.0, language: str = "fr") -> None:
        """Ajoute une entrée à l'historique (version simplifiée)"""
        if not text or not text.strip():
            return
        
        entry = TranscriptionEntry.create(
            text=text.strip(),
            duration=duration,
            language=language,
            processing_time=processing_time
        )
        with self._lock:
            self._history.append(entry)
            if self._auto_save:
                self._save_unsafe()
    
    def add_entry(self, entry: TranscriptionEntry) -> None:
        """Ajoute une entrée pré-créée à l'historique"""
        with self._lock:
            self._history.append(entry)
            if self._auto_save:
                self._save_unsafe()
    
    def add_from_result(
        self,
        text: str,
        duration: float,
        language: str,
        processing_time: float
    ) -> None:
        """Ajoute une entrée depuis un résultat de transcription"""
        if not text or not text.strip():
            return
        
        entry = TranscriptionEntry.create(
            text=text.strip(),
            duration=duration,
            language=language,
            processing_time=processing_time
        )
        self.add_entry(entry)
    
    def get_recent(self, count: int = 10) -> list[TranscriptionEntry]:
        """Retourne les N entrées les plus récentes"""
        with self._lock:
            items = list(self._history)
            return items[-count:] if len(items) > count else items
    
    def get_all(self) -> list[TranscriptionEntry]:
        """Retourne tout l'historique"""
        with self._lock:
            return list(self._history)
    
    def clear(self) -> None:
        """Vide l'historique"""
        with self._lock:
            self._history.clear()
            if self._auto_save and self._file_path:
                try:
                    self._file_path.unlink(missing_ok=True)
                except:
                    pass
    
    def __len__(self) -> int:
        with self._lock:
            return len(self._history)
    
    def __iter__(self) -> Iterator[TranscriptionEntry]:
        with self._lock:
            return iter(list(self._history))
    
    @property
    def last(self) -> TranscriptionEntry | None:
        """Retourne la dernière entrée"""
        with self._lock:
            return self._history[-1] if self._history else None
    
    @property
    def total_duration(self) -> float:
        """Durée totale de l'audio transcrit"""
        with self._lock:
            return sum(e.duration for e in self._history)
    
    @property
    def total_processing_time(self) -> float:
        """Temps de traitement total"""
        with self._lock:
            return sum(e.processing_time for e in self._history)
    
    def _save_unsafe(self) -> None:
        """Sauvegarde sans lock (appelé depuis contexte verrouillé)"""
        if not self._file_path:
            return
        
        try:
            data = [e.to_dict() for e in self._history]
            with self._file_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde historique: {e}")
    
    def _load(self) -> None:
        """Charge l'historique depuis le fichier"""
        if not self._file_path or not self._file_path.exists():
            return
        
        try:
            with self._file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for item in data[-self._max_size:]:
                    if isinstance(item, dict):
                        entry = TranscriptionEntry.from_dict(item)
                        self._history.append(entry)
                
                print(f"📜 Historique chargé: {len(self._history)} entrées")
        except Exception as e:
            print(f"⚠️ Erreur chargement historique: {e}")
    
    def export_text(self) -> str:
        """Exporte l'historique en texte"""
        lines = []
        for entry in self:
            lines.append(f"[{entry.formatted_time}] {entry.text}")
        return "\n".join(lines)


# Instance globale (sans persistance par défaut)
history = TranscriptionHistory(persist=False)


def add_to_history(
    text: str,
    duration: float,
    language: str,
    processing_time: float
) -> None:
    """Ajoute une transcription à l'historique"""
    history.add_from_result(text, duration, language, processing_time)


def get_history() -> list[TranscriptionEntry]:
    """Retourne l'historique complet"""
    return history.get_all()


def get_recent_history(count: int = 10) -> list[TranscriptionEntry]:
    """Retourne les entrées récentes"""
    return history.get_recent(count)


def clear_history() -> None:
    """Vide l'historique"""
    history.clear()
