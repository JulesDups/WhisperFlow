"""
WhisperFlow Desktop
===================

Application de transcription vocale temps réel en local.
Utilise Whisper Large V3 Turbo optimisé pour GPU (RTX 4080).

Usage:
    python main.py

Raccourcis:
    F2      - Push-to-Talk (maintenir pour enregistrer)
    F3      - Copier la transcription
    ESC     - Quitter

Auteur: WhisperFlow Team
Licence: MIT
"""

import logging
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from src.config import app_config
from src.utils.logger import setup_logging


def check_requirements():
    """Vérifie que toutes les dépendances sont installées"""
    missing = []

    try:
        import PyQt6  # noqa: F401
    except ImportError:
        missing.append("PyQt6")

    try:
        import torch

        if not torch.cuda.is_available():
            print("⚠️  AVERTISSEMENT: CUDA n'est pas disponible!")
            print("   La transcription sera très lente sans GPU.")
            print()
    except ImportError:
        missing.append("torch")

    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        missing.append("faster-whisper")

    try:
        import sounddevice  # noqa: F401
    except ImportError:
        missing.append("sounddevice")

    try:
        import pynput  # noqa: F401
    except ImportError:
        missing.append("pynput")

    try:
        import pyperclip  # noqa: F401
    except ImportError:
        missing.append("pyperclip")

    if missing:
        print("❌ Dépendances manquantes:")
        for dep in missing:
            print(f"   - {dep}")
        print()
        print("Installez-les avec:")
        print("   pip install -r requirements.txt")
        print()
        print("Pour PyTorch avec CUDA:")
        print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
        sys.exit(1)


def main():
    """Point d'entrée principal"""

    setup_logging()
    logger = logging.getLogger(__name__)  # noqa: F841

    # Bannière
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                                                            ║")
    print("║   🎤 WhisperFlow Desktop                                   ║")
    print("║   Transcription vocale temps réel en local                 ║")
    print("║                                                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    # Vérifie les dépendances
    check_requirements()

    # Configuration High DPI
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    # Crée l'application
    app = QApplication(sys.argv)
    app.setApplicationName(app_config.APP_NAME)
    app.setApplicationVersion(app_config.APP_VERSION)

    # Charge les fonts Hegoatek bundlées (Syne, DM Mono) — doit être après QApplication
    from src.ui import theme as _theme

    display_family, _ = _theme.load_fonts()

    # Police par défaut
    font = QFont(display_family, 10)
    app.setFont(font)

    # Affiche les infos GPU
    try:
        import torch

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"🖥️  GPU détecté: {gpu_name} ({gpu_mem:.1f} GB)")
        else:
            print("⚠️  Mode CPU (lent)")
    except ImportError:
        print("⚠️  PyTorch non installé")
    except Exception as e:
        print(f"⚠️  Erreur détection GPU: {e}")

    print()
    print("📌 Raccourcis clavier:")
    print("   F2  - Push-to-Talk (maintenir pour parler)")
    print("   F3  - Copier la transcription")
    print("   ESC - Quitter")
    print()
    print("🚀 Démarrage de l'application...")
    print()

    # Importe et crée la fenêtre principale
    from src.ui.main_window import MainWindow

    window = MainWindow()
    window.show()

    # Boucle d'événements
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
