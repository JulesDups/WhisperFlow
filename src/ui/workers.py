"""
WhisperFlow Desktop - Workers (Threading)
Workers QThread pour les opérations asynchrones
"""

from __future__ import annotations

import gc
import logging
import time
from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtCore import QMutex, QThread, QWaitCondition, pyqtSignal

from ..audio_engine import AudioEngine
from ..i18n import t
from ..sources import VideoSource
from ..transcription_service import TranscriptionService
from ..utils.url_notes import UrlNotesMetadata, write_url_notes

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from numpy.typing import NDArray


class ModelLoaderWorker(QThread):
    """
    Worker pour charger le modèle Whisper en arrière-plan.
    Évite de bloquer l'UI pendant le chargement (~30-60s).
    """

    # Signaux
    progress = pyqtSignal(str, float)  # message, pourcentage (0-1)
    finished = pyqtSignal(bool)  # succès
    error = pyqtSignal(str)  # message d'erreur

    def __init__(self, transcription_service: TranscriptionService) -> None:
        super().__init__()
        self.service = transcription_service
        self._should_stop = False

    def run(self) -> None:
        """Charge le modèle"""
        try:
            # Configure le callback de progression
            self.service.set_progress_callback(lambda msg, prog: self.progress.emit(msg, prog))

            # Charge le modèle
            success = self.service.load_model()

            if self._should_stop:
                return

            self.finished.emit(success)

        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(False)

    def stop(self) -> None:
        """Demande l'arrêt du worker"""
        self._should_stop = True


class TranscriptionWorker(QThread):
    """
    Worker pour la transcription audio.
    Permet de transcrire sans bloquer l'UI.
    """

    # Signaux
    started = pyqtSignal()
    progress = pyqtSignal(str)  # message de statut
    result = pyqtSignal(str, float)  # texte, temps de traitement
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, transcription_service: TranscriptionService) -> None:
        super().__init__()
        self.service = transcription_service

        # Données à transcrire
        self._audio_data: NDArray[np.float32] | None = None
        self._sample_rate: int = 16000

        # Contrôle
        self._should_stop = False
        self._mutex = QMutex()
        self._condition = QWaitCondition()
        self._has_task = False

    def set_audio(self, audio_data: NDArray[np.float32], sample_rate: int = 16000) -> None:
        """Définit l'audio à transcrire"""
        self._mutex.lock()
        try:
            self._audio_data = audio_data
            self._sample_rate = sample_rate
            self._has_task = True
            self._condition.wakeOne()
        finally:
            self._mutex.unlock()

    def run(self) -> None:
        """Boucle principale du worker"""
        while not self._should_stop:
            self._mutex.lock()
            try:
                # Attend une tâche
                while not self._has_task and not self._should_stop:
                    self._condition.wait(self._mutex)

                if self._should_stop:
                    break

                # Récupère les données
                audio = self._audio_data
                sr = self._sample_rate
                self._has_task = False
                self._audio_data = None  # Libère la référence
            finally:
                self._mutex.unlock()

            if audio is None:
                continue

            # Transcrit
            self.started.emit()
            self.progress.emit(t("worker_transcribing"))

            try:
                result = self.service.transcribe(audio, sr)

                if result:
                    self.result.emit(result.text, result.processing_time)
                else:
                    self.error.emit(t("worker_transcription_failed"))

            except Exception as e:
                self.error.emit(str(e))
            finally:
                # Libère explicitement la mémoire audio
                del audio
                # Force le garbage collector périodiquement
                if self.service.total_transcriptions % 5 == 0:
                    gc.collect()

            self.finished.emit()

    def stop(self) -> None:
        """Arrête le worker proprement"""
        self._should_stop = True
        self._mutex.lock()
        try:
            self._condition.wakeOne()
        finally:
            self._mutex.unlock()
        # Attend max 2 secondes
        if not self.wait(2000):
            logger.warning(t("worker_timeout"))
            self.terminate()
            self.wait(500)


class AudioRecorderWorker(QThread):
    """
    Worker pour l'enregistrement audio.
    Gère le Push-to-Talk et la détection vocale automatique (VAD).
    """

    # Signaux
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    audio_level = pyqtSignal(float)  # niveau 0-1
    audio_ready = pyqtSignal(np.ndarray, int)  # data, sample_rate
    error = pyqtSignal(str)

    # Durée minimum d'enregistrement (secondes)
    MIN_RECORDING_DURATION: float = 0.3

    # Paramètres VAD
    VAD_SPEECH_THRESHOLD: float = 0.015  # RMS au-dessus = parole détectée
    VAD_SILENCE_DURATION: float = 1.5  # secondes de silence avant arrêt
    VAD_MAX_IDLE: float = 30.0  # secondes max sans parole avant reset du buffer

    def __init__(self) -> None:
        super().__init__()
        self.engine = AudioEngine()

        # État PTT
        self._is_running = False
        self._should_record = False
        self._mutex = QMutex()
        self._condition = QWaitCondition()

        # État VAD
        self._vad_active = False
        self._vad_ready = True  # Prêt à écouter (False pendant la transcription)
        self._current_level: float = 0.0

    def _on_audio_level(self, level: float) -> None:
        """Callback du niveau audio, stocke localement et émet le signal"""
        self._current_level = level
        self.audio_level.emit(level)

    def run(self) -> None:
        """Boucle principale"""
        self._is_running = True
        self.engine.set_audio_level_callback(self._on_audio_level)

        while self._is_running:
            if self._vad_active:
                self._vad_tick()
                QThread.msleep(50)
            else:
                self._ptt_tick()

    def _ptt_tick(self) -> None:
        """Une itération de la boucle Push-to-Talk"""
        self._mutex.lock()
        try:
            self._condition.wait(self._mutex, 50)
            should_record = self._should_record
        finally:
            self._mutex.unlock()

        if should_record and not self.engine.is_recording:
            if self.engine.start_recording():
                self.recording_started.emit()
            else:
                self.error.emit(t("worker_audio_error"))
        elif not should_record and self.engine.is_recording:
            chunk = self.engine.stop_recording()
            self.recording_stopped.emit()
            if chunk and chunk.duration > self.MIN_RECORDING_DURATION:
                self.audio_ready.emit(chunk.data, chunk.sample_rate)

    # === VAD (Voice Activity Detection) ===

    def _vad_tick(self) -> None:
        """Une itération de la boucle VAD"""
        if not self._vad_ready:
            return

        if not self.engine.is_recording:
            # Phase 1 : démarrer l'écoute
            if not self.engine.start_recording():
                QThread.msleep(1000)
            self._vad_silence_time = 0.0
            self._vad_speech_detected = False
            self._vad_idle_time = 0.0
            return

        if not self._vad_speech_detected:
            # Phase 2 : en attente de parole
            if self._current_level > self.VAD_SPEECH_THRESHOLD:
                self._vad_speech_detected = True
                self._vad_silence_time = 0.0
                self.recording_started.emit()
            else:
                self._vad_idle_time += 0.05
                if self._vad_idle_time > self.VAD_MAX_IDLE:
                    # Reset le buffer pour éviter l'accumulation mémoire
                    self.engine.stop_recording()
        else:
            # Phase 3 : parole détectée, surveiller le silence
            if self._current_level < self.VAD_SPEECH_THRESHOLD:
                self._vad_silence_time += 0.05
                if self._vad_silence_time >= self.VAD_SILENCE_DURATION:
                    # Assez de silence : arrêter et transcrire
                    chunk = self.engine.stop_recording()
                    self.recording_stopped.emit()
                    if chunk and chunk.duration > self.MIN_RECORDING_DURATION:
                        self._vad_ready = False
                        self.audio_ready.emit(chunk.data, chunk.sample_rate)
                    self._vad_speech_detected = False
            else:
                self._vad_silence_time = 0.0

    def notify_transcription_done(self) -> None:
        """Appelé par MainWindow quand la transcription est terminée (mode VAD)"""
        self._vad_ready = True

    def start_vad(self) -> None:
        """Active le mode détection vocale automatique"""
        self._vad_active = True
        self._vad_ready = True
        self._vad_speech_detected = False
        self._vad_silence_time = 0.0
        self._vad_idle_time = 0.0
        self._mutex.lock()
        try:
            self._condition.wakeOne()
        finally:
            self._mutex.unlock()

    def stop_vad(self) -> None:
        """Désactive le mode détection vocale"""
        self._vad_active = False
        if self.engine.is_recording:
            self.engine.stop_recording()
            self.recording_stopped.emit()

    # === PTT ===

    def start_recording(self) -> None:
        """Demande le démarrage de l'enregistrement (mode PTT)"""
        self._mutex.lock()
        try:
            self._should_record = True
            self._condition.wakeOne()
        finally:
            self._mutex.unlock()

    def stop_recording(self) -> None:
        """Demande l'arrêt de l'enregistrement (mode PTT)"""
        self._mutex.lock()
        try:
            self._should_record = False
            self._condition.wakeOne()
        finally:
            self._mutex.unlock()

    def stop(self) -> None:
        """Arrête le worker"""
        self._is_running = False
        self._vad_active = False
        self._mutex.lock()
        try:
            self._should_record = False
            self._condition.wakeOne()
        finally:
            self._mutex.unlock()
        if self.engine.is_recording:
            self.engine.stop_recording()
        if not self.wait(2000):
            logger.warning("AudioRecorderWorker: timeout, termine de force")
            self.terminate()
            self.wait(500)


class UrlTranscriptionWorker(QThread):
    """
    Worker qui traite un job URL de bout en bout :
    téléchargement vidéo → extraction audio → transcription Whisper →
    sauvegarde horodatée dans `notes/` (txt ou json, segments inclus).

    Émet des signaux de progression granulaires pour alimenter l'UI :
      - dl_progress(msg, ratio) : 0→0.75 (download + extraction)
      - transcribe_progress(msg) : état de la transcription
      - metadata(title, duration) : dès que fetch_metadata renvoie
      - result(text, lang, confidence, audio_duration, processing_time)
      - notes_saved(path) : chemin du fichier exporté (relatif ou absolu)
      - error(msg)
      - finished()
    """

    dl_progress = pyqtSignal(str, float)
    transcribe_progress = pyqtSignal(str)
    metadata = pyqtSignal(str, float)  # title, duration_s
    # text, lang, conf, audio_dur, proc_time, segments (tuple[TranscriptSegment, ...])
    result = pyqtSignal(str, str, float, float, float, object)
    notes_saved = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, transcription_service: TranscriptionService) -> None:
        super().__init__()
        self.service = transcription_service
        self._url: str = ""
        self._language: str = "auto"
        self._notes_format: str = "json"
        self._cancel = False
        self._mutex = QMutex()
        self._condition = QWaitCondition()
        self._has_task = False
        self._should_stop = False

    def submit_url(
        self,
        url: str,
        language: str = "auto",
        notes_format: str = "json",
    ) -> None:
        """
        Soumet une URL à traiter. Si un job est en cours, il est remplacé.

        Args:
            url: URL vidéo (YouTube, etc.)
            language: 'auto', 'fr', 'en' — passé à Whisper
            notes_format: 'txt' ou 'json' — format d'export
        """
        self._mutex.lock()
        try:
            self._url = url
            self._language = language if language in ("auto", "fr", "en") else "auto"
            self._notes_format = notes_format if notes_format in ("txt", "json") else "json"
            self._cancel = False
            self._has_task = True
            self._condition.wakeOne()
        finally:
            self._mutex.unlock()

    def cancel(self) -> None:
        """Demande l'annulation du job en cours."""
        self._cancel = True

    def run(self) -> None:
        while not self._should_stop:
            self._mutex.lock()
            try:
                while not self._has_task and not self._should_stop:
                    self._condition.wait(self._mutex)
                if self._should_stop:
                    break
                url = self._url
                language = self._language
                notes_format = self._notes_format
                self._has_task = False
                self._cancel = False
            finally:
                self._mutex.unlock()

            if not url:
                continue

            self._process_job(url, language, notes_format)
            self.finished.emit()

    def _process_job(self, url: str, language: str, notes_format: str) -> None:
        source = VideoSource()
        source.set_progress_callback(lambda msg, pct: self.dl_progress.emit(msg, pct))

        # Étape 1 — métadonnées (rapide, utile pour feedback immédiat)
        meta = source.fetch_metadata(url)
        if self._cancel:
            self.error.emit(t("error_cancelled"))
            return
        video_title = meta.title if meta is not None else "Untitled"
        if meta is not None:
            self.metadata.emit(meta.title, meta.duration)

        # Étape 2 — DL + extraction audio (0→75% de dl_progress)
        download_result = source.download_and_extract_audio(url)
        if self._cancel:
            self.error.emit(t("error_cancelled"))
            return
        if download_result is None:
            self.error.emit(t("error_download_failed"))
            return

        # Étape 3 — transcription (segments timestampés pour l'export)
        self.transcribe_progress.emit(t("worker_transcribing"))
        try:
            tr = self.service.transcribe(
                download_result.audio_data,
                download_result.sample_rate,
                language=language,
                with_segments=True,
            )
        except (RuntimeError, ValueError) as e:
            self.error.emit(t("error_transcription_detail", error=e))
            return

        if tr is None:
            self.error.emit(t("error_transcription_empty"))
            return

        audio_dur = len(download_result.audio_data) / float(download_result.sample_rate)
        lang = tr.language or ""
        conf = tr.confidence if tr.confidence is not None else 0.0

        self.result.emit(tr.text, lang, conf, audio_dur, tr.processing_time, tr.segments or ())

        # Étape 4 — export notes horodatées (txt ou json)
        try:
            notes_meta = UrlNotesMetadata(
                video_title=video_title,
                video_url=url,
                model_id=self.service.model_id,
                language_requested=language,
            )
            path = write_url_notes(tr, notes_meta, notes_format)
            self.notes_saved.emit(str(path))
        except OSError as e:
            logger.warning("Impossible d'écrire les notes : %s", e)
            # Non bloquant : le résultat est déjà remonté.

        # Libère l'audio explicitement
        del download_result

    def stop(self) -> None:
        """Arrête proprement le worker."""
        self._should_stop = True
        self._cancel = True
        self._mutex.lock()
        try:
            self._condition.wakeOne()
        finally:
            self._mutex.unlock()
        if not self.wait(3000):
            logger.warning("UrlTranscriptionWorker: timeout, terminé de force")
            self.terminate()
            self.wait(500)


class AudioLevelWorker(QThread):
    """
    Worker léger pour mettre à jour le niveau audio.
    Utilise un timer pour réduire la charge CPU.

    Note: Ce worker est conservé pour une utilisation future potentielle,
    actuellement le niveau audio est géré directement dans AudioRecorderWorker.
    """

    level_updated = pyqtSignal(float)

    def __init__(self, interval_ms: int = 50) -> None:
        super().__init__()
        self.interval = interval_ms / 1000.0
        self._current_level = 0.0
        self._running = False
        self._mutex = QMutex()

    def set_level(self, level: float) -> None:
        """Met à jour le niveau (appelé depuis un autre thread)"""
        self._mutex.lock()
        try:
            self._current_level = level
        finally:
            self._mutex.unlock()

    def run(self) -> None:
        """Émet le niveau à intervalle régulier"""
        self._running = True

        while self._running:
            self._mutex.lock()
            try:
                level = self._current_level
            finally:
                self._mutex.unlock()

            self.level_updated.emit(level)
            time.sleep(self.interval)

    def stop(self) -> None:
        """Arrête le worker"""
        self._running = False
        self.wait()
