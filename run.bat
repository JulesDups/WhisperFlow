@echo off
REM ============================================
REM WhisperFlow Desktop - Lanceur rapide
REM ============================================
REM Utilise ce script pour lancer l'application
REM après l'installation initiale avec setup.bat
REM ============================================

setlocal

REM Chemin du script
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Active l'environnement
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo [ERREUR] Environnement virtuel non trouve!
    echo Lancez d'abord setup.bat pour installer.
    pause
    exit /b 1
)

REM Lance l'application
python main.py

deactivate
endlocal
