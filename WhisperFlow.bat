@echo off
cd /d "%~dp0"

:: Vérifie si l'environnement virtuel existe
if not exist ".venv\Scripts\pythonw.exe" (
    echo [ERREUR] Environnement virtuel non trouve!
    echo Lancez d'abord setup.bat pour installer l'application.
    pause
    exit /b 1
)

:: Lance l'application SANS console (pythonw)
start "" .venv\Scripts\pythonw.exe main.py
