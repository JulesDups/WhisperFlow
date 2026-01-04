@echo off
REM ============================================
REM WhisperFlow Desktop - Script d'installation
REM ============================================
REM
REM Ce script:
REM 1. Crée un environnement virtuel Python
REM 2. Installe PyTorch avec support CUDA 12.1
REM 3. Installe les autres dépendances
REM 4. Lance l'application
REM
REM Prérequis:
REM - Python 3.10+ installé et dans le PATH
REM - GPU NVIDIA avec drivers récents
REM - FFmpeg (optionnel, pour certaines fonctionnalités)
REM
REM ============================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   WhisperFlow Desktop - Installation
echo ========================================
echo.

REM Vérifie que Python est installé (essaie py puis python)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py"
    goto :python_found
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :python_found
)

echo [ERREUR] Python n'est pas installe ou pas dans le PATH!
echo Installez Python 3.10+ depuis https://python.org
pause
exit /b 1

:python_found
echo [OK] Python detecte
%PYTHON_CMD% --version
echo.

REM Chemin du script
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Nom de l'environnement virtuel
set "VENV_DIR=.venv"

REM Vérifie si l'environnement existe
if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [INFO] Environnement virtuel existant detecte
    set "INSTALL_DEPS=0"
    
    REM Demande si on veut réinstaller
    choice /C ON /N /M "Reinstaller les dependances? [O]ui / [N]on: "
    if errorlevel 2 set "INSTALL_DEPS=0"
    if errorlevel 1 set "INSTALL_DEPS=1"
) else (
    echo [INFO] Creation de l'environnement virtuel...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    
    if errorlevel 1 (
        echo [ERREUR] Impossible de creer l'environnement virtuel!
        pause
        exit /b 1
    )
    echo [OK] Environnement virtuel cree
    set "INSTALL_DEPS=1"
)

REM Active l'environnement
echo.
echo [INFO] Activation de l'environnement virtuel...
call "%VENV_DIR%\Scripts\activate.bat"

if errorlevel 1 (
    echo [ERREUR] Impossible d'activer l'environnement virtuel!
    pause
    exit /b 1
)
echo [OK] Environnement active
echo.

REM Installation des dépendances
if "%INSTALL_DEPS%"=="1" (
    echo ========================================
    echo   Installation des dependances
    echo ========================================
    echo.
    
    REM Mise à jour de pip (utilise le python du venv)
    echo [1/4] Mise a jour de pip...
    "%VENV_DIR%\\Scripts\\python.exe" -m pip install --upgrade pip
    echo.
    
    REM Installation de PyTorch avec CUDA 12.1
    echo [2/4] Installation de PyTorch avec CUDA 12.1...
    echo      ^(Cela peut prendre plusieurs minutes^)
    "%VENV_DIR%\\Scripts\\python.exe" -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    
    if errorlevel 1 (
        echo [ERREUR] Echec de l'installation de PyTorch!
        echo Verifiez votre connexion internet.
        pause
        exit /b 1
    )
    echo [OK] PyTorch installe
    echo.
    
    REM Installation des autres dépendances (utilise le python du venv)
    echo [3/4] Installation des autres dependances...
    "%VENV_DIR%\\Scripts\\python.exe" -m pip install -r requirements.txt
    
    if errorlevel 1 (
        echo [ERREUR] Echec de l'installation des dependances!
        pause
        exit /b 1
    )
    echo [OK] Dependances installees
    echo.
    
    REM Test GPU (utilise le python du venv)
    echo [4/4] Verification du GPU...
    "%VENV_DIR%\\Scripts\\python.exe" test_gpu.py
    
    if errorlevel 1 (
        echo.
        echo [AVERTISSEMENT] Certains tests GPU ont echoue.
        echo L'application peut fonctionner mais sera plus lente.
        echo.
        pause
    ) else (
        echo.
        echo [OK] Configuration GPU validee!
        echo.
    )
)

REM Lancement de l'application
echo ========================================
echo   Lancement de WhisperFlow
echo ========================================
echo.
echo Appuyez sur F2 pour parler, ESC pour quitter.
echo.

"%VENV_DIR%\\Scripts\\python.exe" main.py

REM Si erreur
if errorlevel 1 (
    echo.
    echo [ERREUR] L'application s'est terminee avec une erreur.
    echo Consultez les messages ci-dessus pour plus de details.
    pause
)

REM Désactive l'environnement
deactivate

endlocal
