"""
WhisperFlow Desktop - Transcription Service
Service de transcription utilisant Faster-Whisper (CTranslate2)

Faster-Whisper offre:
- ~4x plus rapide que transformers
- ~3x moins de mémoire RAM/VRAM
- Même qualité de transcription
"""

from __future__ import annotations

import gc
import logging
import os
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from .config import app_config, model_config

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from numpy.typing import NDArray

# Import conditionnel de faster-whisper
try:
    from faster_whisper import WhisperModel

    _HAS_FASTER_WHISPER = True
except ImportError:
    _HAS_FASTER_WHISPER = False
    WhisperModel = None

# Import torch pour les infos GPU (optionnel)
try:
    import torch

    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False


@dataclass(slots=True, frozen=True)
class TranscriptionResult:
    """Résultat d'une transcription"""

    text: str
    language: str  # Langue utilisée ou détectée
    duration: float  # Durée de l'audio
    processing_time: float  # Temps de traitement
    detected_language: str | None = None  # Langue détectée si auto
    confidence: float | None = None


# Patterns d'hallucination pré-compilés pour performance
_HALLUCINATION_PATTERN = re.compile(
    r"(Merci d'avoir regardé|Sous-titres réalisés|Sous-titres par|"
    r"Merci à tous|À bientôt|Abonnez-vous|N'oubliez pas de|"
    r"Cliquez sur|\[Musique\]|\[Applaudissements\]|\(Musique\)|\.{3,})",
    re.IGNORECASE,
)
_WHITESPACE_PATTERN = re.compile(r"\s+")


class TranscriptionService:
    """
    Service de transcription Faster-Whisper optimisé GPU

    Features:
    - Utilise CTranslate2 pour des performances optimales
    - Support Float16/INT8 pour réduire la mémoire
    - VAD intégré pour ignorer les silences
    - Support multi-langue avec détection auto
    """

    # Mapping des noms de modèles
    MODEL_MAPPING = {
        "openai/whisper-large-v3-turbo": "turbo",
        "openai/whisper-large-v3": "large-v3",
        "openai/whisper-large-v2": "large-v2",
        "openai/whisper-medium": "medium",
        "openai/whisper-small": "small",
        "openai/whisper-base": "base",
        "openai/whisper-tiny": "tiny",
    }

    def __init__(
        self, model_id: str = model_config.MODEL_ID, device: str = model_config.DEVICE, compute_type: str = "float16"
    ):
        # Convertit le model_id HuggingFace vers faster-whisper si nécessaire
        self.model_id = self.MODEL_MAPPING.get(model_id, model_id)
        self.device = device
        self.compute_type = compute_type

        # Composants du modèle
        self._model: WhisperModel | None = None

        # État
        self._is_loaded = False
        self._is_loading = False
        self._load_lock = threading.Lock()

        # Callbacks
        self._on_progress: Callable[[str, float], None] | None = None

        # Statistiques
        self._total_transcriptions = 0
        self._total_audio_duration = 0.0
        self._total_processing_time = 0.0

    def set_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """Définit le callback de progression (message, pourcentage)"""
        self._on_progress = callback

    def _report_progress(self, message: str, progress: float):
        """Rapporte la progression"""
        if self._on_progress:
            self._on_progress(message, progress)

    def load_model(self) -> bool:
        """
        Charge le modèle Whisper avec Faster-Whisper.

        Returns: True si chargé avec succès
        """
        if not _HAS_FASTER_WHISPER:
            logger.error("faster-whisper n'est pas installe!")
            logger.error("   Installez avec: pip install faster-whisper")
            return False

        with self._load_lock:
            if self._is_loaded:
                return True

            if self._is_loading:
                return False

            self._is_loading = True

        try:
            self._report_progress("Vérification GPU...", 0.1)

            # Vérifie CUDA si device=cuda
            if self.device == "cuda" and _HAS_TORCH and not torch.cuda.is_available():
                logger.warning("CUDA non disponible, utilisation du CPU")
                self.device = "cpu"
                self.compute_type = "int8"

            # Configure le cache local
            cache_dir = str(app_config.MODELS_DIR)
            os.environ["HF_HOME"] = cache_dir
            logger.info("Cache modeles: %s", cache_dir)

            # Libère la mémoire GPU existante
            if _HAS_TORCH and torch.cuda.is_available():
                torch.cuda.empty_cache()

            self._report_progress("Chargement du modèle Faster-Whisper...", 0.3)
            logger.info("Chargement de '%s' sur %s (%s)...", self.model_id, self.device, self.compute_type)

            # Charge le modèle avec Faster-Whisper
            self._model = WhisperModel(
                self.model_id,
                device=self.device,
                compute_type=self.compute_type,
                download_root=cache_dir,
            )

            self._report_progress("Prêt!", 1.0)

            with self._load_lock:
                self._is_loaded = True
                self._is_loading = False

            # Affiche l'utilisation mémoire
            if _HAS_TORCH and torch.cuda.is_available():
                memory_used = torch.cuda.memory_allocated() / 1024**3
                logger.info("Modele charge! VRAM utilisee: %.2f GB", memory_used)
            else:
                logger.info("Modele charge!")

            return True

        except (OSError, RuntimeError) as e:
            logger.exception("Erreur chargement modele: %s", e)
            with self._load_lock:
                self._is_loading = False
            return False

    def unload_model(self):
        """Décharge le modèle et libère la mémoire GPU"""
        with self._load_lock:
            if not self._is_loaded:
                return

            if self._model:
                del self._model
                self._model = None

            # Force le garbage collection
            gc.collect()

            if _HAS_TORCH and torch.cuda.is_available():
                torch.cuda.empty_cache()

            self._is_loaded = False
            logger.info("Modele decharge, memoire liberee")

    def transcribe(
        self, audio_data: NDArray[np.float32], sample_rate: int = 16000, language: str | None = None
    ) -> TranscriptionResult | None:
        """
        Transcrit un segment audio avec Faster-Whisper.

        Args:
            audio_data: Array numpy de l'audio (float32, -1 à 1)
            sample_rate: Fréquence d'échantillonnage
            language: Code langue (fr, en, etc.), "auto" pour détection, None utilise config

        Returns:
            TranscriptionResult ou None en cas d'erreur
        """
        if not self._is_loaded or self._model is None:
            logger.warning("Modele non charge!")
            return None

        start_time = time.time()
        audio_duration = len(audio_data) / sample_rate

        # Détermine la langue à utiliser
        use_language = language if language is not None else model_config.LANGUAGE
        auto_detect = use_language == "auto" or use_language is None or use_language == ""

        try:
            # Paramètres de transcription
            transcribe_kwargs = {
                "beam_size": 5,
                "best_of": 1,
                "vad_filter": True,  # Filtre les silences automatiquement
                "vad_parameters": {
                    "threshold": 0.5,
                    "min_speech_duration_ms": 250,
                    "min_silence_duration_ms": 500,
                },
                "without_timestamps": True,  # Plus rapide sans timestamps
            }

            # Si pas auto-détection, spécifie la langue
            if not auto_detect:
                transcribe_kwargs["language"] = use_language

            # Exécute la transcription
            segments, info = self._model.transcribe(audio_data, **transcribe_kwargs)

            # Collecte tous les segments en une seule chaîne
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            text = " ".join(text_parts).strip()

            processing_time = time.time() - start_time

            # Met à jour les statistiques
            self._total_transcriptions += 1
            self._total_audio_duration += audio_duration
            self._total_processing_time += processing_time

            # Supprime les hallucinations courantes
            text = self._clean_hallucinations(text)

            # Détermine la langue détectée/utilisée
            detected_lang = info.language if auto_detect else None
            final_language = info.language if auto_detect else use_language
            confidence = info.language_probability if auto_detect else None

            return TranscriptionResult(
                text=text,
                language=final_language,
                duration=audio_duration,
                processing_time=processing_time,
                detected_language=detected_lang,
                confidence=confidence,
            )

        except (RuntimeError, ValueError) as e:
            logger.exception("Erreur transcription: %s", e)
            return None
        finally:
            # Force garbage collection périodiquement
            if self._total_transcriptions % 10 == 0:
                gc.collect()
                if _HAS_TORCH and torch.cuda.is_available():
                    torch.cuda.empty_cache()

    def _clean_hallucinations(self, text: str) -> str:
        """
        Supprime les hallucinations courantes de Whisper.
        Utilise des regex pré-compilées pour performance.
        """
        # Supprime les hallucinations avec regex pré-compilée
        text = _HALLUCINATION_PATTERN.sub("", text)

        # Nettoie les espaces multiples avec regex pré-compilée
        text = _WHITESPACE_PATTERN.sub(" ", text)

        return text.strip()

    @property
    def is_loaded(self) -> bool:
        """Retourne True si le modèle est chargé"""
        with self._load_lock:
            return self._is_loaded

    @property
    def is_loading(self) -> bool:
        """Retourne True si le modèle est en cours de chargement"""
        with self._load_lock:
            return self._is_loading

    @property
    def total_transcriptions(self) -> int:
        """Retourne le nombre total de transcriptions effectuees"""
        return self._total_transcriptions

    @property
    def stats(self) -> dict:
        """Retourne les statistiques de transcription"""
        avg_rtf = 0  # Real-Time Factor
        if self._total_audio_duration > 0:
            avg_rtf = self._total_processing_time / self._total_audio_duration

        return {
            "total_transcriptions": self._total_transcriptions,
            "total_audio_duration": self._total_audio_duration,
            "total_processing_time": self._total_processing_time,
            "average_rtf": avg_rtf,  # < 1 = plus rapide que temps réel
        }

    @staticmethod
    def get_gpu_info() -> dict:
        """Retourne les informations sur le GPU"""
        if not _HAS_TORCH or not torch.cuda.is_available():
            return {"available": False}

        props = torch.cuda.get_device_properties(0)
        return {
            "available": True,
            "name": props.name,
            "total_memory_gb": props.total_memory / 1024**3,
            "memory_allocated_gb": torch.cuda.memory_allocated() / 1024**3,
            "memory_reserved_gb": torch.cuda.memory_reserved() / 1024**3,
        }

    @staticmethod
    def get_vram_usage() -> tuple[float, float, float]:
        """
        Retourne l'utilisation VRAM actuelle.

        Returns:
            Tuple (utilisée_gb, totale_gb, pourcentage)
        """
        if not _HAS_TORCH or not torch.cuda.is_available():
            return (0.0, 0.0, 0.0)

        allocated = torch.cuda.memory_allocated() / 1024**3
        total = torch.cuda.get_device_properties(0).total_memory / 1024**3
        percentage = (allocated / total * 100) if total > 0 else 0.0

        return (allocated, total, percentage)


# Test standalone
if __name__ == "__main__":
    print("🤖 Test du service de transcription (Faster-Whisper)")
    print("-" * 50)

    if not _HAS_FASTER_WHISPER:
        print("❌ faster-whisper n'est pas installé!")
        print("   pip install faster-whisper")
        exit(1)

    # Affiche les infos GPU
    gpu_info = TranscriptionService.get_gpu_info()
    if gpu_info["available"]:
        print(f"✅ GPU: {gpu_info['name']}")
        print(f"   Mémoire totale: {gpu_info['total_memory_gb']:.1f} GB")
    else:
        print("ℹ️ Pas de GPU, utilisation du CPU")

    # Crée le service
    service = TranscriptionService()

    def on_progress(msg, progress):
        bar = "█" * int(progress * 20)
        print(f"\r  [{bar:<20}] {progress * 100:.0f}% - {msg}", end="")

    service.set_progress_callback(on_progress)

    print("\n\n📦 Chargement du modèle...")
    if not service.load_model():
        print("\n❌ Échec du chargement!")
        exit(1)

    print("\n")

    # Test avec un audio synthétique (silence)
    print("🎤 Test transcription (silence de 1s)...")
    test_audio = np.zeros(16000, dtype=np.float32)
    result = service.transcribe(test_audio)

    if result:
        print("✅ Transcription réussie!")
        print(f"   Texte: '{result.text}'")
        print(f"   Langue: {result.language}")
        print(f"   Temps: {result.processing_time:.2f}s")

    # Statistiques
    print("\n📊 Après transcription:")
    gpu_info = TranscriptionService.get_gpu_info()
    if gpu_info["available"]:
        print(f"   VRAM utilisée: {gpu_info['memory_allocated_gb']:.2f} GB")

    stats = service.stats
    print(f"   RTF moyen: {stats['average_rtf']:.3f}")

    # Décharge
    service.unload_model()
