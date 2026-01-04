"""
WhisperFlow Desktop - Audio Engine
Moteur de capture audio à faible latence utilisant SoundDevice
"""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional

import numpy as np
import sounddevice as sd

sys.path.append('..')
from config import audio_config

if TYPE_CHECKING:
    from numpy.typing import NDArray


@dataclass(slots=True, frozen=True)
class AudioChunk:
    """Représente un segment audio capturé"""
    data: NDArray[np.float32]
    timestamp: float
    sample_rate: int
    duration: float


class AudioEngine:
    """
    Moteur de capture audio pour le Push-to-Talk
    
    Features:
    - Capture en temps réel à 16kHz (optimal pour Whisper)
    - Buffer circulaire pour éviter les pertes
    - Mode Push-to-Talk avec start/stop
    - Normalisation automatique du signal
    """
    
    def __init__(
        self,
        sample_rate: int = audio_config.SAMPLE_RATE,
        channels: int = audio_config.CHANNELS,
        blocksize: int = audio_config.BLOCKSIZE,
        device: Optional[int] = None
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.blocksize = blocksize
        self.device = device
        
        # État de l'enregistrement
        self._is_recording = False
        self._recording_lock = threading.Lock()
        
        # Buffer pour les données audio
        self._audio_buffer: list[np.ndarray] = []
        self._buffer_lock = threading.Lock()
        
        # Stream audio
        self._stream: Optional[sd.InputStream] = None
        
        # Callbacks
        self._on_audio_level: Optional[Callable[[float], None]] = None
        
        # Statistiques
        self._start_time: float = 0
        self._chunks_captured: int = 0
    
    def set_audio_level_callback(self, callback: Callable[[float], None]):
        """Définit le callback pour les niveaux audio (VU-mètre)"""
        self._on_audio_level = callback
    
    def _audio_callback(
        self,
        indata: NDArray[np.float32],
        frames: int,
        time_info,
        status: sd.CallbackFlags
    ) -> None:
        """
        Callback appelé par SoundDevice pour chaque bloc audio.
        ATTENTION: Ce callback s'exécute dans un thread séparé!
        """
        if status:
            print(f"⚠️ Audio status: {status}")
        
        # Vérification rapide sans lock si possible
        if not self._is_recording:
            return
        
        with self._recording_lock:
            if not self._is_recording:
                return
        
        # Copie les données (important car indata est un buffer réutilisé)
        # Utilise ravel() si déjà contiguous, sinon flatten()
        audio_data: NDArray[np.float32] = indata.ravel().copy() if indata.flags['C_CONTIGUOUS'] else indata.flatten()
        
        # Calcul du niveau audio (RMS) optimisé avec np.dot
        callback = self._on_audio_level
        if callback is not None:
            rms = np.sqrt(np.dot(audio_data, audio_data) / len(audio_data))
            # Utilise np.clip et calcul log optimisé
            level_db = 20.0 * np.log10(max(rms, 1e-10))
            normalized_level = np.clip((level_db + 60.0) / 60.0, 0.0, 1.0)
            callback(float(normalized_level))
        
        # Ajoute au buffer
        with self._buffer_lock:
            self._audio_buffer.append(audio_data)
            self._chunks_captured += 1
    
    def start_recording(self) -> bool:
        """
        Démarre l'enregistrement audio
        Returns: True si démarré avec succès
        """
        with self._recording_lock:
            if self._is_recording:
                return False
            
            # Réinitialise le buffer
            with self._buffer_lock:
                self._audio_buffer.clear()
                self._chunks_captured = 0
            
            self._start_time = time.time()
            
            try:
                # Crée et démarre le stream
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=audio_config.DTYPE,
                    blocksize=self.blocksize,
                    device=self.device,
                    callback=self._audio_callback
                )
                self._stream.start()
                self._is_recording = True
                return True
                
            except Exception as e:
                print(f"❌ Erreur démarrage audio: {e}")
                return False
    
    def stop_recording(self) -> Optional[AudioChunk]:
        """
        Arrête l'enregistrement et retourne les données capturées
        Returns: AudioChunk contenant l'audio enregistré, ou None
        """
        with self._recording_lock:
            if not self._is_recording:
                return None
            
            self._is_recording = False
        
        # Arrête le stream
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        # Récupère et concatène les données
        with self._buffer_lock:
            if not self._audio_buffer:
                return None
            
            # Pré-calcul de la taille totale pour éviter réallocations
            total_samples = sum(chunk.size for chunk in self._audio_buffer)
            audio_data = np.empty(total_samples, dtype=np.float32)
            
            # Copie efficace dans le buffer pré-alloué
            offset = 0
            for chunk in self._audio_buffer:
                audio_data[offset:offset + chunk.size] = chunk
                offset += chunk.size
            
            self._audio_buffer.clear()
        
        # Normalise l'audio (-1 à 1) - opération in-place
        max_val = np.abs(audio_data).max()
        if max_val > 0:
            audio_data *= (0.95 / max_val)
        
        duration = len(audio_data) / self.sample_rate
        
        return AudioChunk(
            data=audio_data,
            timestamp=self._start_time,
            sample_rate=self.sample_rate,
            duration=duration
        )
    
    @property
    def is_recording(self) -> bool:
        """Retourne True si l'enregistrement est en cours"""
        with self._recording_lock:
            return self._is_recording
    
    @staticmethod
    def list_devices() -> list[dict]:
        """Liste tous les périphériques audio disponibles"""
        devices = sd.query_devices()
        input_devices = []
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append({
                    'id': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate'],
                    'is_default': device == sd.query_devices(kind='input')
                })
        
        return input_devices
    
    @staticmethod
    def get_default_device() -> dict:
        """Retourne le périphérique d'entrée par défaut"""
        device = sd.query_devices(kind='input')
        return {
            'name': device['name'],
            'channels': device['max_input_channels'],
            'sample_rate': device['default_samplerate']
        }


class AudioLevelMonitor:
    """
    Moniteur de niveau audio pour le feedback visuel
    Fournit une valeur lissée du niveau audio
    """
    
    def __init__(self, smoothing: float = 0.3):
        self.smoothing = smoothing
        self._current_level = 0.0
        self._peak_level = 0.0
        self._peak_decay = 0.95
        self._lock = threading.Lock()
    
    def update(self, level: float):
        """Met à jour le niveau avec lissage"""
        with self._lock:
            # Lissage exponentiel
            self._current_level = (
                self.smoothing * level + 
                (1 - self.smoothing) * self._current_level
            )
            
            # Peak hold avec decay
            if level > self._peak_level:
                self._peak_level = level
            else:
                self._peak_level *= self._peak_decay
    
    @property
    def level(self) -> float:
        """Niveau actuel (0-1)"""
        with self._lock:
            return self._current_level
    
    @property
    def peak(self) -> float:
        """Niveau peak (0-1)"""
        with self._lock:
            return self._peak_level


# Test standalone
if __name__ == "__main__":
    print("🎤 Test du moteur audio")
    print("-" * 40)
    
    # Liste les périphériques
    print("\n📋 Périphériques d'entrée disponibles:")
    for device in AudioEngine.list_devices():
        marker = "→ " if device['is_default'] else "  "
        print(f"{marker}[{device['id']}] {device['name']}")
    
    # Test d'enregistrement
    print("\n🔴 Enregistrement de 3 secondes...")
    
    engine = AudioEngine()
    monitor = AudioLevelMonitor()
    
    engine.set_audio_level_callback(monitor.update)
    
    engine.start_recording()
    
    for i in range(30):
        time.sleep(0.1)
        bar = "█" * int(monitor.level * 20)
        print(f"\r  Niveau: [{bar:<20}] {monitor.level:.2f}", end="")
    
    print()
    
    chunk = engine.stop_recording()
    
    if chunk:
        print(f"\n✅ Enregistrement terminé!")
        print(f"   Durée: {chunk.duration:.2f}s")
        print(f"   Samples: {len(chunk.data)}")
        print(f"   Sample Rate: {chunk.sample_rate} Hz")
    else:
        print("\n❌ Aucune donnée capturée")
