"""
WhisperFlow Desktop - Configuration
Configuration centralisée de l'application
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    """Configuration générale de l'application"""
    APP_NAME: str = "WhisperFlow"
    APP_VERSION: str = "1.0.0"
    
    # Répertoire de l'application
    BASE_DIR: Path = Path(__file__).parent
    CACHE_DIR: Path = BASE_DIR / ".cache"
    MODELS_DIR: Path = CACHE_DIR / "models"  # Cache des modèles Hugging Face
    

@dataclass
class AudioConfig:
    """Configuration du moteur audio"""
    SAMPLE_RATE: int = 16000  # Whisper attend du 16kHz
    CHANNELS: int = 1  # Mono
    DTYPE: str = "float32"
    BLOCKSIZE: int = 1024  # Taille du buffer audio
    

@dataclass
class ModelConfig:
    """Configuration du modèle Whisper"""
    MODEL_ID: str = "turbo"  # Modèle Faster-Whisper (turbo = large-v3-turbo)
    DEVICE: str = "cuda"  # Utilisation GPU
    TORCH_DTYPE: str = "float16"  # Half precision pour économiser la VRAM
    
    # Paramètres de génération
    LANGUAGE: str = "fr"  # Langue par défaut ("auto" pour détection automatique)
    TASK: str = "transcribe"
    MAX_NEW_TOKENS: int = 440  # Réduit pour laisser place aux tokens de démarrage (4)
    
    # Optimisations
    USE_FLASH_ATTENTION: bool = True
    CHUNK_LENGTH_S: int = 30  # Durée max d'un segment
    
    # Mode batch pour longues transcriptions
    BATCH_SIZE: int = 8  # Nombre de chunks à traiter en parallèle
    LONG_AUDIO_THRESHOLD_S: float = 30.0  # Seuil pour activer le mode batch


@dataclass
class HotkeyConfig:
    """Configuration des raccourcis clavier"""
    PUSH_TO_TALK_KEY: str = "f2"
    COPY_TO_CLIPBOARD_KEY: str = "f3"
    QUIT_KEY: str = "escape"
    
    # Mode de sortie: "type" = frappe directe, "clipboard" = copie seulement
    OUTPUT_MODE: str = "type"  # Tape automatiquement dans l'app active
    TYPE_DELAY: float = 0.01  # Délai entre caractères (secondes)


@dataclass
class UIConfig:
    """Configuration de l'interface utilisateur"""
    WINDOW_WIDTH: int = 440
    WINDOW_HEIGHT: int = 260
    WINDOW_OPACITY: float = 0.95
    
    # Intervalle de mise à jour VRAM (ms)
    VRAM_UPDATE_INTERVAL_MS: int = 2000
    
    # Couleurs
    COLOR_BACKGROUND: str = "#1E1E2E"
    COLOR_SURFACE: str = "#313244"
    COLOR_TEXT: str = "#CDD6F4"
    COLOR_TEXT_DIM: str = "#6C7086"
    COLOR_ACCENT: str = "#89B4FA"
    COLOR_RECORDING: str = "#F38BA8"
    COLOR_PROCESSING: str = "#89DCEB"
    COLOR_SUCCESS: str = "#A6E3A1"
    
    # Bordures et ombres
    BORDER_RADIUS: int = 16
    SHADOW_BLUR: int = 20


# Instances de configuration
app_config = AppConfig()
audio_config = AudioConfig()
model_config = ModelConfig()
hotkey_config = HotkeyConfig()
ui_config = UIConfig()

# Création des répertoires cache si nécessaire
app_config.CACHE_DIR.mkdir(exist_ok=True)
app_config.MODELS_DIR.mkdir(exist_ok=True)
