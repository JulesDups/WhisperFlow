# WhisperFlow Desktop

🎤 **Application de transcription vocale temps réel en local**

Transformez votre voix en texte instantanément, en toute confidentialité, sans connexion cloud.

![WhisperFlow](https://img.shields.io/badge/WhisperFlow-v1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![CUDA](https://img.shields.io/badge/CUDA-12.1-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Fonctionnalités

- 🚀 **Ultra-rapide** - Transcription en temps réel grâce à l'accélération GPU
- 🔒 **100% Local** - Aucune donnée ne quitte votre ordinateur
- 🎯 **Précision** - Utilise Whisper Large V3 Turbo d'OpenAI
- 🎹 **Push-to-Talk** - Appuyez sur F2, parlez, relâchez, c'est transcrit
- 📋 **Copie facile** - Résultat copié en un clic ou avec F3
- 🎨 **UI Moderne** - Interface flottante minimaliste style macOS

---

## 🖥️ Prérequis

| Composant  | Minimum               | Recommandé           |
| ---------- | --------------------- | -------------------- |
| **GPU**    | NVIDIA GTX 1060 (6GB) | RTX 3080+ / RTX 4080 |
| **VRAM**   | 6 GB                  | 12+ GB               |
| **RAM**    | 8 GB                  | 16+ GB               |
| **OS**     | Windows 10            | Windows 11           |
| **Python** | 3.10                  | 3.11                 |

### Logiciels requis

1. **Python 3.10+** - [Télécharger](https://python.org)
2. **Drivers NVIDIA récents** - [Télécharger](https://nvidia.com/drivers)
3. **FFmpeg** (optionnel) - [Télécharger](https://ffmpeg.org)

---

## 🚀 Installation

### Installation automatique (recommandée)

```bash
# 1. Clonez ou téléchargez le projet
cd WhisperFlow

# 2. Lancez l'installation
setup.bat
```

Le script `setup.bat` va automatiquement :

- Créer un environnement virtuel Python
- Installer PyTorch avec support CUDA 12.1
- Installer toutes les dépendances
- Tester la configuration GPU
- Lancer l'application

### Installation manuelle

```bash
# 1. Créer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate

# 2. Installer PyTorch avec CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Tester le GPU
python test_gpu.py

# 5. Lancer l'application
python main.py
```

---

## 🎮 Utilisation

### Raccourcis clavier

| Touche  | Action                               |
| ------- | ------------------------------------ |
| **F2**  | Push-to-Talk (maintenir pour parler) |
| **F3**  | Copier la transcription              |
| **ESC** | Quitter l'application                |

### Workflow typique

1. **Lancez** l'application avec `run.bat`
2. **Attendez** le chargement du modèle (~30s au premier lancement)
3. **Maintenez F2** et parlez dans votre micro
4. **Relâchez F2** - la transcription apparaît instantanément
5. **Appuyez F3** pour copier ou cliquez sur "Copier"

---

## ⚙️ Configuration

Modifiez `config.py` pour personnaliser :

```python
# Langue de transcription
LANGUAGE = "fr"  # fr, en, es, de, etc.

# Touche Push-to-Talk
PUSH_TO_TALK_KEY = "f2"

# Modèle Whisper
MODEL_ID = "openai/whisper-large-v3-turbo"
```

### Modèles disponibles

| Modèle                       | VRAM   | Précision  | Vitesse    |
| ---------------------------- | ------ | ---------- | ---------- |
| `whisper-tiny`               | ~1 GB  | ⭐⭐       | ⭐⭐⭐⭐⭐ |
| `whisper-base`               | ~1 GB  | ⭐⭐⭐     | ⭐⭐⭐⭐   |
| `whisper-small`              | ~2 GB  | ⭐⭐⭐⭐   | ⭐⭐⭐     |
| `whisper-medium`             | ~5 GB  | ⭐⭐⭐⭐   | ⭐⭐       |
| `whisper-large-v3`           | ~10 GB | ⭐⭐⭐⭐⭐ | ⭐         |
| **`whisper-large-v3-turbo`** | ~6 GB  | ⭐⭐⭐⭐⭐ | ⭐⭐⭐     |

---

## 🏗️ Architecture

```
WhisperFlow/
├── main.py                 # Point d'entrée
├── config.py               # Configuration centralisée
├── requirements.txt        # Dépendances Python
├── setup.bat               # Script d'installation
├── run.bat                 # Lanceur rapide
├── test_gpu.py             # Diagnostic GPU
├── LICENSE                 # Licence MIT
└── src/
    ├── audio_engine.py           # Capture audio (SoundDevice)
    ├── transcription_service.py  # Moteur IA (Faster-Whisper)
    ├── smart_formatter.py        # Formatage intelligent du texte
    ├── ui/
    │   ├── main_window.py        # Fenêtre PyQt6
    │   ├── key_capture_dialog.py # Configuration des raccourcis
    │   ├── styles.py             # Styles CSS
    │   └── workers.py            # Threading QThread
    └── utils/
        ├── clipboard.py          # Presse-papier & frappe auto
        ├── history.py            # Historique des transcriptions
        ├── hotkey_listener.py    # Raccourcis globaux
        └── settings.py           # Persistance des paramètres
```

---

## 🐛 Dépannage

### "CUDA n'est pas disponible"

1. Vérifiez que vous avez une carte NVIDIA
2. Mettez à jour vos drivers : [nvidia.com/drivers](https://nvidia.com/drivers)
3. Réinstallez PyTorch : `pip install torch --index-url https://download.pytorch.org/whl/cu121`

### "Out of Memory" (VRAM insuffisante)

1. Fermez les autres applications utilisant le GPU
2. Utilisez un modèle plus petit dans `config.py` :
   ```python
   MODEL_ID = "openai/whisper-small"
   ```

### Le micro ne fonctionne pas

1. Vérifiez que le micro est autorisé dans Windows
2. Testez avec `python -c "import sounddevice; print(sounddevice.query_devices())"`
3. Sélectionnez manuellement le périphérique dans `config.py`

### L'application ne démarre pas

1. Lancez `python test_gpu.py` pour diagnostiquer
2. Vérifiez les logs dans le terminal
3. Réinstallez avec `setup.bat`

---

## 📊 Performances

Testé sur RTX 4080 (16 GB VRAM) :

| Durée audio | Temps transcription | RTF\* |
| ----------- | ------------------- | ----- |
| 5 secondes  | ~0.5s               | 0.1x  |
| 30 secondes | ~2s                 | 0.07x |
| 1 minute    | ~3s                 | 0.05x |

\*RTF (Real-Time Factor) : < 1 = plus rapide que temps réel

---

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :

- 🐛 Signaler des bugs
- 💡 Proposer des fonctionnalités
- 🔧 Soumettre des pull requests

---

## 📄 Licence

MIT License - Libre d'utilisation personnelle et commerciale.

---

## 🙏 Crédits

- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) - Moteur de transcription optimisé
- [OpenAI Whisper](https://github.com/openai/whisper) - Modèle de transcription
- [Hugging Face Transformers](https://huggingface.co/transformers) - Pipeline ML
- [PyQt6](https://riverbankcomputing.com/software/pyqt) - Interface graphique
- [pynput](https://github.com/moses-palmer/pynput) - Raccourcis clavier
- [SoundDevice](https://python-sounddevice.readthedocs.io) - Capture audio

---

<div align="center">

**WhisperFlow Desktop** - Fait avec ❤️ pour la productivité

</div>
