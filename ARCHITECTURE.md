# WhisperFlow - Architecture

## Vue d'ensemble

Application desktop PyQt6 de transcription vocale en temps reel, fonctionnant entierement en local. Utilise Faster-Whisper (CTranslate2) optimise pour GPU NVIDIA (CUDA 12.1).

## Structure du projet

```
WhisperFlow/
  main.py                       Point d'entree, verification des dependances
  src/
    config.py                   Configuration centralisee (dataclasses + enums)
    audio_engine.py             Capture audio (SoundDevice, 16kHz mono)
    transcription_service.py    Pipeline Faster-Whisper (GPU/CUDA)
    smart_formatter.py          Formatage du texte transcrit (regles + IA)
    ui/
      main_window.py            Fenetre principale PyQt6 (sans bordure, draggable)
      workers.py                QThread workers pour taches asynchrones
      styles.py                 Theme sombre Catppuccin (QSS)
      key_capture_dialog.py     Dialogue de capture de touche PTT
    utils/
      hotkey_listener.py        Raccourcis globaux (pynput + ThreadPoolExecutor)
      settings.py               Persistance JSON des preferences utilisateur
      clipboard.py              Copie/frappe automatique du texte
      history.py                Historique des transcriptions
      logger.py                 Configuration centralisee du logging
  tests/
    test_smart_formatter.py     Tests du formatage de texte
    test_transcription.py       Tests du nettoyage d'hallucinations
    test_settings.py            Tests de la serialisation des parametres
    test_history.py             Tests de l'historique
    test_hotkey_parser.py       Tests du parsing de raccourcis clavier
```

## Flux de donnees

```
Utilisateur (maintient F2)
        |
        v
GlobalHotkeyListener (pynput, thread daemon)
        |  on_press / on_release
        v
MainWindow._start_recording() / _stop_recording()
        |
        v
AudioRecorderWorker (QThread)
        |  AudioEngine.start_recording()
        |  Buffer numpy float32, 16kHz mono
        v
TranscriptionWorker (QThread)
        |  TranscriptionService.transcribe(audio_data)
        |  Faster-Whisper sur GPU (CTranslate2)
        v
Nettoyage hallucinations + Smart Formatting
        |
        v
Sortie: clipboard (pyperclip) ou frappe directe (pynput Ctrl+V)
```

## Couches applicatives

### 1. Capture audio (`audio_engine.py`)

- `AudioEngine` : gere le stream audio via `sounddevice`
- Capture en 16kHz mono float32 (format requis par Whisper)
- Callback audio execute dans un thread separe -- les donnees sont copiees dans un buffer numpy
- `AudioLevelMonitor` : calcule le niveau audio RMS pour l'indicateur visuel

### 2. Transcription (`transcription_service.py`)

- `TranscriptionService` : encapsule le modele Faster-Whisper
- Charge le modele `turbo` (Large V3 Turbo) sur GPU avec `float16`
- Filtre VAD integre pour ignorer les silences
- Nettoyage des hallucinations Whisper via regex pre-compilee
- Garbage collection periodique de la VRAM

### 3. Interface utilisateur (`ui/`)

- `MainWindow` : fenetre sans bordure avec coins arrondis, toujours au premier plan (mode floating)
- `TitleBar` : barre personnalisee avec drag-and-drop manuel
- `AppState` (enum) : `LOADING` -> `READY` -> `RECORDING` -> `PROCESSING`
- Workers QThread pour operations longues (chargement modele, enregistrement, transcription)
- Communication inter-threads via signaux/slots PyQt6

### 4. Utilitaires (`utils/`)

- `GlobalHotkeyListener` : ecoute des raccourcis meme hors focus, avec `ThreadPoolExecutor` pour les callbacks
- `SettingsManager` : persistance JSON avec ecriture atomique (fichier temporaire + rename)
- `ClipboardManager` / `TextTyper` : deux modes de sortie (copie ou frappe directe via Ctrl+V)

## Patterns de threading

| Thread | Role | Communication |
|--------|------|---------------|
| Main (Qt Event Loop) | UI, signaux/slots | Direct |
| pynput Listener | Ecoute touches globales | ThreadPoolExecutor -> signaux Qt |
| AudioRecorderWorker | Capture audio | QMutex/QWaitCondition -> signal `finished` |
| TranscriptionWorker | Inference GPU | Signal `transcription_done(str)` |
| sounddevice callback | Buffer audio | `numpy.copy()` dans le buffer |

## Configuration

Toute la configuration est centralisee dans `src/config.py` via des dataclasses :

- `AppConfig` : noms, versions, chemins
- `AudioConfig` : sample rate, channels, dtype
- `ModelConfig` : modele Whisper, device, langue
- `HotkeyConfig` : touches raccourcis, mode de sortie
- `UIConfig` : dimensions, couleurs, theme

Les enums `OutputMode` et `WindowMode` (StrEnum) assurent la validation des valeurs.

## Dependances principales

| Package | Role |
|---------|------|
| `faster-whisper` | Inference Whisper optimisee (CTranslate2) |
| `torch` (CUDA) | Backend GPU, gestion VRAM |
| `PyQt6` | Interface graphique |
| `sounddevice` | Capture audio |
| `pynput` | Raccourcis clavier globaux |
| `pyperclip` | Acces presse-papier |
| `numpy` | Buffers audio |

## Outils de developpement

| Outil | Fichier de config | Role |
|-------|-------------------|------|
| `ruff` | `ruff.toml` | Linting + formatage |
| `pytest` | - | Tests unitaires |
| `pre-commit` | `.pre-commit-config.yaml` | Hooks pre-commit (ruff) |
