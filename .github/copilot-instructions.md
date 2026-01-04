# WhisperFlow - Instructions pour agents IA

## Architecture

Application PyQt6 de transcription vocale locale utilisant Whisper Large V3 Turbo. Architecture en 4 couches :

```
main.py                    → Point d'entrée, vérification des dépendances
config.py                  → Configuration centralisée (dataclasses)
src/
  audio_engine.py          → Capture audio (SoundDevice, 16kHz mono)
  transcription_service.py → Pipeline Whisper (transformers, GPU/CUDA)
  ui/
    main_window.py         → Fenêtre principale PyQt6 (sans bordure, draggable)
    workers.py             → QThread workers pour tâches async
    styles.py              → Thème sombre (QSS)
  utils/
    hotkey_listener.py     → Raccourcis globaux (pynput)
    settings.py            → Persistance JSON des préférences
    clipboard.py           → Copie/frappe automatique du texte
```

## Flux de données

1. **Push-to-Talk (F2)** → `GlobalHotkeyListener` déclenche `AudioRecorderWorker`
2. **AudioEngine** capture en buffer numpy (16kHz float32)
3. **TranscriptionWorker** envoie au `TranscriptionService` (GPU)
4. Résultat → copie clipboard ou frappe directe via `type_text()`

## Conventions du projet

### Configuration

- **Toujours utiliser les dataclasses de** [config.py](../config.py) : `app_config`, `audio_config`, `model_config`, `hotkey_config`, `ui_config`
- Ne pas hardcoder de valeurs de configuration dans les modules

### Threading PyQt6

- Utiliser `QThread` avec signaux/slots pour les tâches longues (voir [workers.py](../src/ui/workers.py))
- Pattern : Worker avec `QMutex`/`QWaitCondition` pour la communication
- Les callbacks audio (`_audio_callback`) s'exécutent dans un thread séparé - toujours copier les données

### État de l'application

Utiliser l'enum `AppState` dans [main_window.py](../src/ui/main_window.py) :

- `LOADING` → chargement modèle (~30s)
- `READY` → prêt à enregistrer
- `RECORDING` → capture en cours
- `PROCESSING` → transcription GPU

### Imports locaux

Les modules utilisent `sys.path.append('..')` pour les imports relatifs. Exemple :

```python
import sys
sys.path.append('..')
from config import audio_config
```

## Commandes de développement

```bash
# Installation (Windows)
setup.bat                  # Crée venv + installe PyTorch CUDA + dépendances

# Lancement
python main.py             # ou run.bat / WhisperFlow.bat

# Test GPU
python test_gpu.py         # Vérifie CUDA et la mémoire disponible
```

## Dépendances critiques

- **PyTorch CUDA** : installé séparément via `--index-url https://download.pytorch.org/whl/cu121`
- **transformers** : pipeline `automatic-speech-recognition` avec `AutoModelForSpeechSeq2Seq`
- **sounddevice** : stream audio avec callbacks
- **pynput** : capture globale des touches (fonctionne hors focus)

## Points d'attention

1. **Mémoire GPU** : Le modèle utilise ~5-6 GB VRAM. Utiliser `torch.cuda.empty_cache()` si besoin
2. **Audio 16kHz** : Whisper attend du 16kHz mono - la conversion est automatique dans `AudioEngine`
3. **Fenêtre sans bordure** : Le drag est géré manuellement dans `TitleBar` via `mousePressEvent`/`mouseMoveEvent`
4. **Flash Attention** : Optionnel, fallback sur SDPA si non installé

## Structure des paramètres utilisateur

Fichier `user_settings.json` à la racine, géré par `SettingsManager` :

```json
{
  "push_to_talk_key": "f2",
  "output_mode": "type",
  "language": "fr"
}
```
