@echo off
REM =====================================================
REM GEC Mines - Script d'Installation Automatique Windows
REM =====================================================
REM Copyright (c) 2025 MOA Digital Agency LLC
REM Developpe par : AIsance KALONJI wa KALONJI
REM Email : moa@myoneart.com | moa.myoneart@gmail.com
REM =====================================================

echo.
echo ================================================
echo 🚀 Installation de GEC Mines pour Windows
echo ================================================
echo.

REM Verification des outils
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python n'est pas installe ou non trouve dans PATH
    echo 🔗 Veuillez installer Python 3.11: https://python.org/downloads/
    echo    Assurez-vous de cocher "Add Python to PATH"
    pause
    exit /b 1
)

where git >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Git n'est pas installe ou non trouve dans PATH
    echo 🔗 Veuillez installer Git: https://git-scm.com/downloads
    pause
    exit /b 1
)

echo ✅ Python et Git detectes

REM Definir le dossier d'installation
set INSTALL_DIR=%USERPROFILE%\gec-mines

REM Verifier si le dossier existe deja
if exist "%INSTALL_DIR%" (
    echo.
    echo ⚠️  Le dossier %INSTALL_DIR% existe deja
    set /p CHOICE="Voulez-vous le supprimer et recommencer? (o/N): "
    if /i "%CHOICE%"=="o" (
        rmdir /s /q "%INSTALL_DIR%"
        echo 🗑️  Dossier supprime
    ) else (
        echo ❌ Installation annulee
        pause
        exit /b 1
    )
)

REM Cloner le projet
echo.
echo 📂 Clonage du projet GEC Mines...
git clone https://github.com/moa-digitalagency/gec.git "%INSTALL_DIR%"
if %errorlevel% neq 0 (
    echo ❌ Erreur lors du clonage du projet
    echo    Verifiez votre connexion internet et l'acces a GitHub
    pause
    exit /b 1
)

cd /d "%INSTALL_DIR%"
echo ✅ Projet clone dans %INSTALL_DIR%

REM Creer l'environnement virtuel
echo.
echo 🐍 Creation de l'environnement Python...
python -m venv .venv
if %errorlevel% neq 0 (
    echo Tentative avec py -3.11...
    py -3.11 -m venv .venv
    if %errorlevel% neq 0 (
        echo ❌ Erreur lors de la creation de l'environnement virtuel
        pause
        exit /b 1
    )
)
echo ✅ Environnement virtuel cree

REM Activer l'environnement virtuel
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ❌ Erreur lors de l'activation de l'environnement virtuel
    pause
    exit /b 1
)
echo ✅ Environnement virtuel active

REM Installer les dependances
echo.
echo 📦 Installation des dependances Python...
python -m pip install -U pip wheel
if %errorlevel% neq 0 (
    echo ❌ Erreur lors de la mise a jour de pip
    pause
    exit /b 1
)

python -m pip install -r project-dependencies.txt
if %errorlevel% neq 0 (
    echo ❌ Erreur lors de l'installation des dependances
    pause
    exit /b 1
)
echo ✅ Dependances installees

REM Configuration initiale
echo.
echo ⚙️  Configuration initiale...

REM Creer le fichier .env s'il n'existe pas
if not exist ".env" (
    echo # Configuration GEC Mines > .env
    echo DATABASE_URL=sqlite:///instance/gecmines.db >> .env
    echo SESSION_SECRET=GEC-SECRET-KEY-CHANGE-ME-IN-PRODUCTION >> .env
    echo GEC_MASTER_KEY=CHANGE-THIS-32-CHAR-ENCRYPTION-KEY >> .env
    echo GEC_PASSWORD_SALT=CHANGE-THIS-SALT >> .env
    echo. >> .env
    echo # Configuration SMTP (optionnel) >> .env
    echo # SMTP_SERVER=smtp.gmail.com >> .env
    echo # SMTP_PORT=587 >> .env
    echo # SMTP_EMAIL=votre-email@gmail.com >> .env
    echo # SMTP_PASSWORD=votre-mot-de-passe-app >> .env
    echo # SMTP_USE_TLS=True >> .env
    echo ✅ Fichier .env cree avec configuration par defaut
) else (
    echo ✅ Fichier .env existe deja
)

REM Creer les dossiers necessaires
if not exist "instance" mkdir instance
if not exist "uploads" mkdir uploads
if not exist "backups" mkdir backups
if not exist "exports" mkdir exports
echo ✅ Dossiers necessaires crees

REM Test de l'installation
echo.
echo 🧪 Test de l'installation...
python -c "import flask, sqlalchemy, cryptography; print('✅ Modules principaux importes')"
if %errorlevel% neq 0 (
    echo ❌ Erreur lors du test d'importation
    pause
    exit /b 1
)

REM Creer un script de demarrage
echo @echo off > start-gec.bat
echo cd /d "%INSTALL_DIR%" >> start-gec.bat
echo call .venv\Scripts\activate.bat >> start-gec.bat
echo python main.py >> start-gec.bat
echo pause >> start-gec.bat
echo ✅ Script de demarrage 'start-gec.bat' cree

REM Instructions finales
echo.
echo ================================================
echo 🎉 Installation terminee avec succes!
echo ================================================
echo.
echo 📍 Dossier d'installation: %INSTALL_DIR%
echo.
echo 🚀 Pour demarrer GEC Mines:
echo    1. Double-cliquez sur 'start-gec.bat'
echo    2. Ou executez manuellement:
echo       cd "%INSTALL_DIR%"
echo       .venv\Scripts\activate
echo       python main.py
echo.
echo 🌐 L'application sera accessible sur: http://localhost:5000
echo.
echo 📧 Support: moa@myoneart.com ^| moa.myoneart@gmail.com
echo 🌐 Site web: https://myoneart.com
echo.
echo © 2025 MOA Digital Agency LLC
echo.

REM Proposer de demarrer l'application
set /p START_NOW="Voulez-vous demarrer l'application maintenant? (o/N): "
if /i "%START_NOW%"=="o" (
    echo.
    echo 🚀 Demarrage de GEC Mines...
    python main.py
)

pause