@echo off
setlocal enabledelayedexpansion

echo ================================================================
echo           Installation Automatique GEC - Windows
echo ================================================================
echo Developpe par: MOA Digital Agency LLC
echo Auteur: AIsance KALONJI wa KALONJI
echo Contact: moa@myoneart.com
echo ================================================================
echo.

REM Verifier les privileges administrateur
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Privileges administrateur detectes
) else (
    echo [ERREUR] Ce script necessite des privileges administrateur
    echo Faites un clic droit sur le fichier et selectionnez "Executer en tant qu'administrateur"
    pause
    exit /b 1
)

echo.
echo [ETAPE 1/8] Verification de winget...
where winget >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] winget est disponible
) else (
    echo [INFO] Installation d'App Installer depuis Microsoft Store...
    start ms-windows-store://pdp/?productid=9NBLGGH4NNS1
    echo Veuillez installer App Installer puis relancer ce script
    pause
    exit /b 1
)

echo.
echo [ETAPE 2/8] Installation de Python 3.11...
winget install --id Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements
if %errorLevel% == 0 (
    echo [OK] Python 3.11 installe avec succes
) else (
    echo [AVERTISSEMENT] Erreur lors de l'installation de Python, continuons...
)

echo.
echo [ETAPE 3/8] Installation de Git...
winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
if %errorLevel__ == 0 (
    echo [OK] Git installe avec succes
) else (
    echo [AVERTISSEMENT] Erreur lors de l'installation de Git, continuons...
)

echo.
echo [ETAPE 4/8] Actualisation des variables d'environnement...
REM Actualiser PATH pour inclure Python et Git
call refreshenv.cmd 2>nul || (
    echo [INFO] Ajout manuel de Python et Git au PATH...
    setx PATH "%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts;C:\Program Files\Git\bin" /M
)

echo.
echo [ETAPE 5/8] Telechargement du code source GEC...
if exist "gec" (
    echo [INFO] Dossier gec existant, mise a jour...
    cd gec
    git pull origin main
    cd ..
) else (
    git clone https://github.com/moa-digitalagency/gec.git
    if %errorLevel% == 0 (
        echo [OK] Code source telecharge avec succes
    ) else (
        echo [ERREUR] Echec du telechargement du code source
        pause
        exit /b 1
    )
)

cd gec

echo.
echo [ETAPE 6/8] Configuration de l'environnement Python...
REM Autoriser l'execution de scripts PowerShell
powershell.exe -Command "Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force"

REM Creer l'environnement virtuel
python -m venv .venv
if %errorLevel__ neq 0 (
    echo [INFO] Tentative avec py -3.11...
    py -3.11 -m venv .venv
)

REM Activer l'environnement virtuel et installer les dependances
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip wheel
python -m pip install -r project-dependencies.txt

if %errorLevel__ == 0 (
    echo [OK] Dependances installees avec succes
) else (
    echo [ERREUR] Echec de l'installation des dependances
    pause
    exit /b 1
)

echo.
echo [ETAPE 7/8] Configuration de la base de donnees...
if not exist ".env" (
    echo DATABASE_URL=sqlite:///instance/gecmines.db > .env
    echo SESSION_SECRET=%RANDOM%%RANDOM%%RANDOM% >> .env
    echo GEC_MASTER_KEY=%RANDOM%%RANDOM%%RANDOM% >> .env
    echo GEC_PASSWORD_SALT=%RANDOM%%RANDOM% >> .env
    echo [OK] Fichier de configuration cree
) else (
    echo [INFO] Fichier .env existant, conservation des parametres
)

REM Creer le dossier instance s'il n'existe pas
if not exist "instance" mkdir instance

echo.
echo [ETAPE 8/8] Creation des raccourcis...

REM Creer un fichier de demarrage
echo @echo off > start-gec.bat
echo cd /d "%%~dp0" >> start-gec.bat
echo call .venv\Scripts\activate.bat >> start-gec.bat
echo echo. >> start-gec.bat
echo echo ============================================ >> start-gec.bat
echo echo     GEC - Systeme de Gestion du Courrier >> start-gec.bat
echo echo     Acces: http://localhost:5000 >> start-gec.bat
echo echo     Developpe par MOA Digital Agency LLC >> start-gec.bat
echo echo ============================================ >> start-gec.bat
echo echo. >> start-gec.bat
echo python main.py >> start-gec.bat
echo pause >> start-gec.bat

REM Creer un raccourci sur le bureau
powershell.exe -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\GEC.lnk'); $Shortcut.TargetPath = '%CD%\start-gec.bat'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.Description = 'GEC - Systeme de Gestion du Courrier'; $Shortcut.Save()"

echo.
echo ================================================================
echo                    INSTALLATION TERMINEE !
echo ================================================================
echo.
echo L'application GEC a ete installee avec succes.
echo.
echo Pour demarrer l'application:
echo   1. Double-cliquez sur "GEC" sur votre bureau
echo   2. Ou executez "start-gec.bat" dans ce dossier
echo.
echo L'application sera accessible a l'adresse:
echo   http://localhost:5000
echo.
echo Configuration SMTP pour les emails (optionnel):
echo   Editez le fichier .env pour ajouter vos parametres SMTP
echo.
echo Support technique:
echo   Email: moa@myoneart.com
echo   Tel: +212 699 14 000 1 / +243 86 049 33 45
echo   Web: myoneart.com
echo.
echo ================================================================

echo.
set /p startNow="Voulez-vous demarrer GEC maintenant? (O/N): "
if /i "%startNow%"=="O" (
    echo Demarrage de GEC...
    start cmd /k start-gec.bat
) else (
    echo.
    echo Vous pouvez demarrer GEC plus tard en double-cliquant 
    echo sur le raccourci "GEC" sur votre bureau.
)

echo.
pause