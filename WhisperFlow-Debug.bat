@echo off
chcp 65001 >nul
title WhisperFlow Desktop - Debug
cd /d "%~dp0"

:: Vérifie si l'environnement virtuel existe
if not exist ".venv\Scripts\python.exe" (
    echo [ERREUR] Environnement virtuel non trouve!
    echo Lancez d'abord setup.bat pour installer l'application.
    pause
    exit /b 1
)

:: Lance l'application AVEC console (pour voir les logs)
".venv\Scripts\python.exe" main.py

:: Garde la console ouverte en cas d'erreur
if errorlevel 1 (
    echo.
    echo [ERREUR] L'application s'est fermee avec une erreur.
)
pause
