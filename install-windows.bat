@echo off
REM =============================================================
REM GEC Mines - Script d'installation automatique pour Windows
REM =============================================================
REM Copyright (c) 2025 MOA Digital Agency LLC
REM Développé par AIsance KALONJI wa KALONJI
REM Contact: moa@myoneart.com | +212 699 14 000 1
REM =============================================================

echo.
echo ========================================
echo   GEC Mines - Installation Windows
echo ========================================
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe. Veuillez installer Python 3.11 d'abord.
    echo Commande: winget install --id Python.Python.3.11 -e
    pause
    exit /b 1
)

REM Vérifier si Git est installé
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Git n'est pas installe. Veuillez installer Git d'abord.
    echo Commande: winget install --id Git.Git -e
    pause
    exit /b 1
)

echo [INFO] Python et Git detectes avec succes.
echo.

REM Créer l'environnement virtuel
echo [1/5] Creation de l'environnement virtuel...
if exist .venv (
    echo L'environnement virtuel existe deja.
) else (
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo Tentative avec py -3.11...
        py -3.11 -m venv .venv
    )
)

REM Activer l'environnement virtuel
echo [2/5] Activation de l'environnement virtuel...
call .venv\Scripts\activate.bat

REM Mettre à jour pip
echo [3/5] Mise a jour de pip...
python -m pip install -U pip wheel

REM Installer les dépendances
echo [4/5] Installation des dependances...
pip install -r project-dependencies.txt

REM Vérifier l'installation
echo [5/5] Verification de l'installation...
python -c "import flask; print('Flask:', flask.__version__)"
python -c "import sqlalchemy; print('SQLAlchemy:', sqlalchemy.__version__)"

echo.
echo ========================================
echo   Installation terminee avec succes!
echo ========================================
echo.
echo Pour demarrer l'application:
echo   1. Activez l'environnement: .venv\Scripts\activate.bat
echo   2. Lancez l'app: python main.py
echo   3. Ouvrez http://localhost:5000 dans votre navigateur
echo.
echo N'oubliez pas de configurer le fichier .env avec vos parametres!
echo.
pause