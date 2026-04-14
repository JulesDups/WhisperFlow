"""
WhisperFlow Desktop - Voice Notes
Sauvegarde persistante des transcriptions dans des fichiers Markdown quotidiens
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path

from ..config import app_config

logger = logging.getLogger(__name__)


class VoiceNotesManager:
    """
    Gestionnaire de notes vocales persistantes.

    Chaque transcription est écrite dans un fichier quotidien :
    notes/YYYY-MM-DD.md

    Format :
    # Notes vocales - YYYY-MM-DD

    [HH:MM:SS] Texte transcrit ici
    """

    __slots__ = ("_notes_dir", "_lock")

    HEADER_TEMPLATE = "# Notes vocales - {date}\n\n"

    def __init__(self, notes_dir: Path | None = None) -> None:
        self._notes_dir = notes_dir or (app_config.BASE_DIR / "notes")
        self._lock = threading.Lock()
        self._notes_dir.mkdir(exist_ok=True)

    def add_note(self, text: str) -> bool:
        """
        Ajoute une note vocale au fichier du jour.

        Args:
            text: Texte transcrit à sauvegarder

        Returns:
            True si l'écriture a réussi
        """
        if not text or not text.strip():
            return False

        text = text.strip()
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        file_path = self._notes_dir / f"{date_str}.md"

        with self._lock:
            try:
                file_exists = file_path.exists()

                with file_path.open("a", encoding="utf-8") as f:
                    if not file_exists:
                        f.write(self.HEADER_TEMPLATE.format(date=date_str))
                    f.write(f"[{time_str}] {text}\n")

                logger.debug("Note vocale sauvegardée dans %s", file_path.name)
                return True

            except OSError as e:
                logger.error("Erreur écriture note vocale: %s", e)
                return False

    def get_today_notes(self) -> str | None:
        """Retourne le contenu du fichier de notes d'aujourd'hui"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        file_path = self._notes_dir / f"{date_str}.md"

        if not file_path.exists():
            return None

        try:
            return file_path.read_text(encoding="utf-8")
        except OSError as e:
            logger.error("Erreur lecture notes: %s", e)
            return None

    def list_note_files(self) -> list[Path]:
        """Retourne la liste des fichiers de notes, triés par date"""
        if not self._notes_dir.exists():
            return []
        return sorted(self._notes_dir.glob("*.md"))

    @property
    def notes_dir(self) -> Path:
        """Retourne le répertoire des notes"""
        return self._notes_dir


# Instance globale
voice_notes = VoiceNotesManager()
