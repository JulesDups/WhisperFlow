"""
WhisperFlow Desktop - Workers (Threading)
Workers QThread pour les opérations asynchrones
"""

from __future__ import annotations

import gc
import sys
import time
from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtCore import QMutex, QThread, QWaitCondition, pyqtSignal

sys.path.append('../..')
from src.audio_engine import AudioEngine
from src.transcription_service import TranscriptionService

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
            self.service.set_progress_callback(
                lambda msg, prog: self.progress.emit(msg, prog)
            )
            
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
        """Définit l'audio à transcrire (prend ownership du buffer)"""
        self._mutex.lock()
        try:
            # Note: On ne copie plus le buffer pour économiser la RAM
            # L'appelant (AudioRecorderWorker) crée un nouveau buffer à chaque enregistrement
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
            self.progress.emit("Transcription en cours...")
            
            try:
                result = self.service.transcribe(audio, sr)
                
                if result:
                    self.result.emit(result.text, result.processing_time)
                else:
                    self.error.emit("Échec de la transcription")
                    
            except Exception as e:
                self.error.emit(str(e))
            finally:
                # Libère explicitement la mémoire audio
                del audio
                # Force le garbage collector périodiquement
                if self.service._total_transcriptions % 5 == 0:
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
            print("⚠️ TranscriptionWorker: timeout, terminé de force")
            self.terminate()
            self.wait(500)


class AudioRecorderWorker(QThread):
    """
    Worker pour l'enregistrement audio continu.
    Gère le Push-to-Talk.
    """
    
    # Signaux
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    audio_level = pyqtSignal(float)  # niveau 0-1
    audio_ready = pyqtSignal(np.ndarray, int)  # data, sample_rate
    error = pyqtSignal(str)
    
    # Durée minimum d'enregistrement (secondes)
    MIN_RECORDING_DURATION: float = 0.3
    
    def __init__(self) -> None:
        super().__init__()
        self.engine = AudioEngine()
        
        # État
        self._is_running = False
        self._should_record = False
        self._mutex = QMutex()
        self._condition = QWaitCondition()
    
    def run(self) -> None:
        """Boucle principale"""
        self._is_running = True
        
        # Configure le callback de niveau audio
        self.engine.set_audio_level_callback(
            lambda level: self.audio_level.emit(level)
        )
        
        while self._is_running:
            self._mutex.lock()
            try:
                # Attend un signal de démarrage/arrêt
                self._condition.wait(self._mutex, 100)  # Timeout 100ms
                should_record = self._should_record
            finally:
                self._mutex.unlock()
            
            if should_record and not self.engine.is_recording:
                # Démarre l'enregistrement
                if self.engine.start_recording():
                    self.recording_started.emit()
                else:
                    self.error.emit("Impossible de démarrer l'enregistrement")
                    
            elif not should_record and self.engine.is_recording:
                # Arrête l'enregistrement
                chunk = self.engine.stop_recording()
                self.recording_stopped.emit()
                
                if chunk and chunk.duration > self.MIN_RECORDING_DURATION:
                    self.audio_ready.emit(chunk.data, chunk.sample_rate)
    
    def start_recording(self) -> None:
        """Demande le démarrage de l'enregistrement"""
        self._mutex.lock()
        try:
            self._should_record = True
            self._condition.wakeOne()
        finally:
            self._mutex.unlock()
    
    def stop_recording(self) -> None:
        """Demande l'arrêt de l'enregistrement"""
        self._mutex.lock()
        try:
            self._should_record = False
            self._condition.wakeOne()
        finally:
            self._mutex.unlock()
    
    def stop(self) -> None:
        """Arrête le worker"""
        self._is_running = False
        self._mutex.lock()
        try:
            self._should_record = False
            self._condition.wakeOne()
        finally:
            self._mutex.unlock()
        # Attend max 2 secondes
        if not self.wait(2000):
            print("⚠️ AudioRecorderWorker: timeout, terminé de force")
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
