"""
WhisperFlow - Video Source
Télécharge une vidéo (YouTube, etc.) via yt-dlp et extrait son audio
au format attendu par TranscriptionService (numpy float32, 16kHz, mono).

Dépendances:
- yt-dlp : téléchargement universel (YouTube, Vimeo, Twitch, ...)
- imageio-ffmpeg : binaire ffmpeg bundlé dans le venv (zéro install globale)
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from ..config import video_source_config

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from numpy.typing import NDArray

try:
    import yt_dlp

    _HAS_YTDLP = True
except ImportError:
    _HAS_YTDLP = False
    yt_dlp = None  # type: ignore[assignment]

try:
    import imageio_ffmpeg

    _HAS_IMAGEIO_FFMPEG = True
except ImportError:
    _HAS_IMAGEIO_FFMPEG = False
    imageio_ffmpeg = None  # type: ignore[assignment]


@dataclass(slots=True, frozen=True)
class VideoMetadata:
    """Métadonnées d'une vidéo téléchargée"""

    title: str
    duration: float  # en secondes
    url: str
    uploader: str | None = None


@dataclass(slots=True, frozen=True)
class VideoDownloadResult:
    """Résultat d'un téléchargement + extraction audio"""

    audio_data: NDArray[np.float32]
    sample_rate: int
    metadata: VideoMetadata


class VideoSourceError(Exception):
    """Erreur lors du téléchargement ou de l'extraction audio"""


class VideoSource:
    """
    Télécharge une vidéo depuis une URL et en extrait l'audio
    au format Whisper (numpy float32, mono, 16kHz).

    Usage:
        source = VideoSource()
        source.set_progress_callback(lambda msg, pct: print(f"{pct*100:.0f}% {msg}"))
        result = source.download_and_extract_audio("https://youtube.com/watch?v=...")
        if result:
            service.transcribe(result.audio_data, result.sample_rate)
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        sample_rate: int = 16000,
        max_duration_s: float | None = None,
    ) -> None:
        self.cache_dir = cache_dir or video_source_config.DOWNLOADS_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sample_rate = sample_rate
        self.max_duration_s = max_duration_s if max_duration_s is not None else video_source_config.MAX_DURATION_S
        self._progress_cb: Callable[[str, float], None] | None = None

    def set_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """Définit le callback de progression (message, pourcentage 0-1)"""
        self._progress_cb = callback

    def _report(self, message: str, progress: float) -> None:
        if self._progress_cb:
            self._progress_cb(message, progress)

    @staticmethod
    def check_dependencies() -> tuple[bool, str]:
        """Vérifie que yt-dlp et imageio-ffmpeg sont disponibles"""
        if not _HAS_YTDLP:
            return False, "yt-dlp non installé (pip install yt-dlp)"
        if not _HAS_IMAGEIO_FFMPEG:
            return False, "imageio-ffmpeg non installé (pip install imageio-ffmpeg)"
        return True, ""

    def fetch_metadata(self, url: str) -> VideoMetadata | None:
        """
        Récupère les métadonnées sans télécharger (rapide).
        Utile pour afficher le titre/durée avant d'engager le DL.
        """
        ok, err = self.check_dependencies()
        if not ok:
            logger.error(err)
            return None

        try:
            opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            return VideoMetadata(
                title=info.get("title") or "Sans titre",
                duration=float(info.get("duration") or 0.0),
                url=info.get("webpage_url") or url,
                uploader=info.get("uploader"),
            )
        except Exception as e:
            logger.exception("Échec récupération métadonnées: %s", e)
            return None

    def download_and_extract_audio(self, url: str) -> VideoDownloadResult | None:
        """
        Télécharge la piste audio de la vidéo et la décode en numpy float32.

        Returns:
            VideoDownloadResult ou None en cas d'erreur.
        """
        ok, err = self.check_dependencies()
        if not ok:
            logger.error(err)
            return None

        self._report("Récupération des informations...", 0.0)

        # Utilise un sous-dossier temporaire dans le cache → auto-nettoyé
        try:
            with tempfile.TemporaryDirectory(dir=self.cache_dir, prefix="dl_") as tmp_dir:
                tmp_path = Path(tmp_dir)
                info, downloaded_file = self._download_audio(url, tmp_path)
                if info is None or downloaded_file is None:
                    return None

                duration = float(info.get("duration") or 0.0)
                if self.max_duration_s > 0 and duration > self.max_duration_s:
                    logger.error("Vidéo trop longue: %.0fs > %.0fs (max)", duration, self.max_duration_s)
                    self._report("Vidéo trop longue", 1.0)
                    return None

                metadata = VideoMetadata(
                    title=info.get("title") or "Sans titre",
                    duration=duration,
                    url=info.get("webpage_url") or url,
                    uploader=info.get("uploader"),
                )

                self._report("Extraction audio...", 0.75)
                audio = self._decode_to_numpy(downloaded_file)
                if audio is None:
                    return None

                self._report("Audio prêt", 1.0)
                logger.info(
                    "Audio extrait: %s (%.1fs, %d samples)",
                    metadata.title,
                    metadata.duration,
                    len(audio),
                )

                return VideoDownloadResult(
                    audio_data=audio,
                    sample_rate=self.sample_rate,
                    metadata=metadata,
                )
        except VideoSourceError as e:
            logger.error("VideoSource: %s", e)
            return None
        except Exception as e:
            logger.exception("Erreur inattendue: %s", e)
            return None

    def _download_audio(self, url: str, tmp_path: Path) -> tuple[dict | None, Path | None]:
        """Télécharge via yt-dlp dans tmp_path et retourne (info, fichier)."""

        def _hook(d: dict) -> None:
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done = d.get("downloaded_bytes", 0)
                pct = (done / total) if total else 0.0
                # Le DL occupe 0→70% de la progression globale
                self._report(f"Téléchargement… {pct * 100:.0f}%", pct * 0.7)
            elif status == "finished":
                self._report("Téléchargement terminé", 0.7)

        out_template = str(tmp_path / "%(id)s.%(ext)s")
        ydl_opts = {
            "format": video_source_config.YTDLP_FORMAT,
            "outtmpl": out_template,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,  # désactive la progress bar native (on a notre hook)
            "noplaylist": True,
            "progress_hooks": [_hook],
            # On ne veut pas du post-processing audio de yt-dlp (on décode nous-mêmes)
            "postprocessors": [],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = Path(ydl.prepare_filename(info))
        except Exception as e:
            logger.exception("Échec du téléchargement yt-dlp: %s", e)
            return None, None

        if not filename.exists():
            # yt-dlp peut avoir utilisé une extension différente — on cherche
            candidates = list(tmp_path.iterdir())
            if not candidates:
                logger.error("Aucun fichier téléchargé dans %s", tmp_path)
                return None, None
            filename = candidates[0]

        return info, filename

    def _decode_to_numpy(self, file_path: Path) -> NDArray[np.float32] | None:
        """
        Décode un fichier audio/vidéo en numpy float32 mono @ self.sample_rate.
        Utilise le ffmpeg bundlé par imageio-ffmpeg (chemin local au venv).
        """
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe,
            "-nostdin",
            "-i",
            str(file_path),
            "-f",
            "f32le",  # raw 32-bit float little-endian
            "-acodec",
            "pcm_f32le",
            "-ac",
            "1",  # mono
            "-ar",
            str(self.sample_rate),  # resampling
            "-loglevel",
            "error",
            "pipe:1",
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode(errors="replace") if e.stderr else ""
            logger.error("ffmpeg decode failed: %s", stderr)
            return None
        except FileNotFoundError:
            logger.error("ffmpeg introuvable: %s", ffmpeg_exe)
            return None

        if not proc.stdout:
            logger.error("ffmpeg n'a produit aucune sortie audio")
            return None

        audio = np.frombuffer(proc.stdout, dtype=np.float32)
        # np.frombuffer → read-only ; on copie pour que le consommateur puisse écrire
        return np.ascontiguousarray(audio)


# ============================================================================
# CLI standalone (test de bout en bout)
# ============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python -m src.sources.video_source <url>")
        sys.exit(1)

    test_url = sys.argv[1]
    print(f"\n=== Test VideoSource ===\nURL: {test_url}\n")

    ok, err = VideoSource.check_dependencies()
    if not ok:
        print(f"[ERREUR] {err}")
        sys.exit(1)

    source = VideoSource()
    source.set_progress_callback(lambda msg, pct: print(f"  [{pct * 100:5.1f}%] {msg}"))

    print("Étape 1/2 — Métadonnées :")
    meta = source.fetch_metadata(test_url)
    if meta:
        print(f"  Titre    : {meta.title}")
        print(f"  Durée    : {meta.duration:.1f}s")
        print(f"  Uploader : {meta.uploader}")
    else:
        print("  (échec métadonnées — on tente quand même le DL)")

    print("\nÉtape 2/2 — Téléchargement + extraction audio :")
    result = source.download_and_extract_audio(test_url)

    if result is None:
        print("\n[ÉCHEC] Impossible de récupérer l'audio")
        sys.exit(1)

    print("\n=== Succès ===")
    print(f"  Titre       : {result.metadata.title}")
    print(f"  Durée vidéo : {result.metadata.duration:.1f}s")
    print(f"  Sample rate : {result.sample_rate} Hz")
    print(f"  Samples     : {len(result.audio_data):,}")
    print(f"  Durée audio : {len(result.audio_data) / result.sample_rate:.1f}s")
    print(f"  dtype       : {result.audio_data.dtype}")
    print(f"  Shape       : {result.audio_data.shape}")
    print(f"  Min / Max   : {result.audio_data.min():.3f} / {result.audio_data.max():.3f}")
