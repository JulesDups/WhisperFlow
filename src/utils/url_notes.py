"""
URL notes writer — sauvegarde structurée des transcriptions vidéo.

Usage (depuis UrlTranscriptionWorker) :
    path = write_url_notes(
        result=tr,
        video_title="Me at the zoo",
        video_url="https://...",
        fmt="json",
    )

Layout disque :
    notes/
      2026-04-14/
        12-34-56_me-at-the-zoo.json
        12-34-56_another-video.txt

Chaque fichier est autonome : on peut ouvrir un .json/.txt et retrouver
titre, URL, langue, segments horodatés, infos modèle, temps de traitement.
Les transcripts du chemin micro (PTT/VAD) passent par voice_notes, pas par
cet helper — ce writer est **réservé au chemin URL**.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from ..config import app_config
from ..transcription_service import TranscriptionResult

logger = logging.getLogger(__name__)


NotesFormat = Literal["txt", "json"]


NOTES_DIR: Path = app_config.BASE_DIR / "notes"


@dataclass(slots=True, frozen=True)
class UrlNotesMetadata:
    """Métadonnées injectées dans le fichier exporté."""

    video_title: str
    video_url: str
    model_id: str
    language_requested: str  # "fr", "en", "auto"


def _slugify(text: str, max_len: int = 60) -> str:
    """Slug sûr pour nom de fichier : ascii lowercase + tirets."""
    # Normalise accents et décompose
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    # Remplace tout non-alphanum par '-'
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_text).strip("-").lower()
    if not slug:
        slug = "untitled"
    return slug[:max_len].rstrip("-")


def _format_timecode(seconds: float) -> str:
    """HH:MM:SS.mmm format pour les segments dans .txt (3 décimales comme Whisper)."""
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000))
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def write_url_notes(
    result: TranscriptionResult,
    meta: UrlNotesMetadata,
    fmt: NotesFormat,
    *,
    now: datetime | None = None,
) -> Path:
    """
    Écrit un fichier de transcription pour une vidéo URL.

    Args:
        result: TranscriptionResult avec `segments` rempli (with_segments=True).
        meta: métadonnées (titre, URL, modèle, langue demandée).
        fmt: 'txt' ou 'json'.
        now: datetime à utiliser pour l'horodatage (default: maintenant).

    Returns:
        Path absolu du fichier écrit.

    Raises:
        OSError: si la création du dossier ou l'écriture échoue.
    """
    now = now or datetime.now()

    date_dir = NOTES_DIR / now.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(meta.video_title or "untitled")
    filename = f"{now.strftime('%H-%M-%S')}_{slug}.{fmt}"
    path = date_dir / filename

    if fmt == "json":
        _write_json(path, result, meta, now)
    else:
        _write_txt(path, result, meta, now)

    logger.info("URL notes written: %s", path.name)
    return path


def _write_json(
    path: Path,
    result: TranscriptionResult,
    meta: UrlNotesMetadata,
    now: datetime,
) -> None:
    payload: dict = {
        "metadata": {
            "timestamp": now.isoformat(timespec="seconds"),
            "video_title": meta.video_title,
            "video_url": meta.video_url,
            "model": meta.model_id,
            "language_requested": meta.language_requested,
            "language_detected": result.language,
            "language_probability": result.confidence,
            "audio_duration_s": result.duration,
            "processing_time_s": result.processing_time,
        },
        "text": result.text,
        "segments": [{"start": seg.start, "end": seg.end, "text": seg.text} for seg in (result.segments or ())],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_txt(
    path: Path,
    result: TranscriptionResult,
    meta: UrlNotesMetadata,
    now: datetime,
) -> None:
    lines: list[str] = []
    lines.append(f"# {meta.video_title}")
    lines.append(f"# {meta.video_url}")
    lang_line = f"# {now.strftime('%Y-%m-%d %H:%M:%S')} · {result.language}"
    if result.confidence is not None:
        lang_line += f" ({result.confidence * 100:.0f}%)"
    lang_line += f" · {meta.model_id} · {result.duration:.1f}s audio · {result.processing_time:.1f}s proc"
    lines.append(lang_line)
    lines.append("")

    if result.segments:
        for seg in result.segments:
            lines.append(f"[{_format_timecode(seg.start)} -> {_format_timecode(seg.end)}]  {seg.text}")
    else:
        lines.append(result.text)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
