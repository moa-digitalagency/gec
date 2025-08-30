@echo off
setlocal enabledelayedexpansion

echo ================================================================
echo     Installation GEC - Windows Server 2008/2012/2016+
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
    echo Clic droit sur le fichier et "Executer en tant qu'administrateur"
    pause
    exit /b 1
)

echo.
echo [ETAPE 1/9] Detection de la version Windows Server...
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
echo [INFO] Version detectee: %VERSION%

echo.
echo [ETAPE 2/9] Installation manuelle de Python 3.11...
echo [INFO] Telechargement de Python 3.11 pour Windows Server...

REM Creer dossier temporaire
if not exist "C:\temp" mkdir C:\temp
cd /d C:\temp

REM Telecharger Python 3.11 (version compatible Server)
powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe', 'python-3.11.9-amd64.exe')"

if exist "python-3.11.9-amd64.exe" (
    echo [INFO] Installation silencieuse de Python 3.11...
    python-3.11.9-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    timeout /t 30 /nobreak >nul
    echo [OK] Python 3.11 installe
) else (
    echo [ERREUR] Echec du telechargement de Python
    echo Veuillez telecharger manuellement depuis https://www.python.org
    pause
    exit /b 1
)

echo.
echo [ETAPE 3/9] Installation de Git...
powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://github.com/git-for-windows/git/releases/download/v2.42.0.windows.2/Git-2.42.0.2-64-bit.exe', 'Git-installer.exe')"

if exist "Git-installer.exe" (
    echo [INFO] Installation silencieuse de Git...
    Git-installer.exe /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
    timeout /t 30 /nobreak >nul
    echo [OK] Git installe
) else (
    echo [ERREUR] Echec du telechargement de Git
    pause
    exit /b 1
)

echo.
echo [ETAPE 4/9] Mise a jour des variables d'environnement...
REM Actualiser PATH
setx PATH "%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts;C:\Program Files\Git\bin" /M
set PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts;C:\Program Files\Git\bin

echo.
echo [ETAPE 5/9] Configuration du pare-feu Windows Server...
netsh advfirewall firewall add rule name="GEC HTTP" dir=in action=allow protocol=TCP localport=5000
netsh advfirewall firewall add rule name="GEC HTTPS" dir=in action=allow protocol=TCP localport=443

echo.
echo [ETAPE 6/9] Creation du repertoire d'installation...
if not exist "C:\GEC" mkdir C:\GEC
cd /d C:\GEC

echo [INFO] Telechargement du code source...
git clone https://github.com/moa-digitalagency/gec.git .
if %errorLevel% neq 0 (
    echo [ERREUR] Echec du telechargement du code source
    pause
    exit /b 1
)

echo.
echo [ETAPE 7/9] Configuration de l'environnement Python...
python -m venv venv
if %errorLevel% neq 0 (
    echo [ERREUR] Echec de la creation de l'environnement virtuel
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip wheel
python -m pip install -r project-dependencies.txt

if %errorLevel% neq 0 (
    echo [ERREUR] Echec de l'installation des dependances
    pause
    exit /b 1
)

echo.
echo [ETAPE 8/9] Configuration de la base de donnees et securite...

REM Configuration .env pour production
echo DATABASE_URL=sqlite:///instance/gecmines.db > .env
echo SESSION_SECRET=%RANDOM%%RANDOM%%RANDOM%%TIME:~-5% >> .env
echo GEC_MASTER_KEY=%RANDOM%%RANDOM%%RANDOM%%DATE:~-4% >> .env
echo GEC_PASSWORD_SALT=%RANDOM%%RANDOM% >> .env

REM Creer les dossiers necessaires
if not exist "instance" mkdir instance
if not exist "uploads" mkdir uploads
if not exist "backups" mkdir backups
if not exist "logs" mkdir logs

echo.
echo [ETAPE 9/9] Installation du service Windows...

REM Creer le script de service
echo @echo off > gec-service.bat
echo cd /d "C:\GEC" >> gec-service.bat
echo call venv\Scripts\activate.bat >> gec-service.bat
echo python main.py >> gec-service.bat

REM Installer le service Windows
sc create "GEC" binPath= "C:\GEC\gec-service.bat" start= auto DisplayName= "GEC - Gestion du Courrier"
sc description "GEC" "Systeme de gestion du courrier - Secrétariat Général RDC - Developpe par MOA Digital Agency LLC"

REM Configurer le service pour redemarrage automatique
sc failure "GEC" reset= 86400 actions= restart/60000/restart/60000/restart/60000

REM Creer les scripts de gestion
echo @echo off > start-gec.bat
echo echo Demarrage du service GEC... >> start-gec.bat
echo sc start "GEC" >> start-gec.bat
echo echo Service demarre. Acces: http://localhost:5000 >> start-gec.bat
echo pause >> start-gec.bat

echo @echo off > stop-gec.bat
echo echo Arret du service GEC... >> stop-gec.bat
echo sc stop "GEC" >> stop-gec.bat
echo echo Service arrete >> stop-gec.bat
echo pause >> stop-gec.bat

echo @echo off > status-gec.bat
echo echo Statut du service GEC: >> status-gec.bat
echo sc query "GEC" >> status-gec.bat
echo pause >> status-gec.bat

REM Creer script de sauvegarde automatique
echo @echo off > backup-gec.bat
echo cd /d "C:\GEC" >> backup-gec.bat
echo call venv\Scripts\activate.bat >> backup-gec.bat
echo python -c "from views import create_system_backup; create_system_backup()" >> backup-gec.bat
echo echo Sauvegarde terminee >> backup-gec.bat

REM Programmer la sauvegarde quotidienne
schtasks /create /sc daily /mo 1 /tn "GEC Backup" /tr "C:\GEC\backup-gec.bat" /st 02:00 /ru SYSTEM

echo.
echo ================================================================
echo              INSTALLATION WINDOWS SERVER TERMINEE !
echo ================================================================
echo.
echo Configuration du serveur GEC terminee avec succes.
echo.
echo COMMANDES DE GESTION:
echo   Demarrer le service: start-gec.bat
echo   Arreter le service:  stop-gec.bat
echo   Statut du service:   status-gec.bat
echo   Sauvegarde manuelle: backup-gec.bat
echo.
echo ACCES A L'APPLICATION:
echo   URL locale: http://localhost:5000
echo   URL reseau: http://[IP-SERVEUR]:5000
echo.
echo CONFIGURATION AVANCEE:
echo   - Fichier config: C:\GEC\.env
echo   - Logs systeme: Observateur d'evenements ^> Services
echo   - Sauvegarde auto: Tache planifiee "GEC Backup"
echo.
echo SECURITE:
echo   - Pare-feu: Port 5000 autorise
echo   - Service: Redemarrage automatique active
echo   - Sauvegarde: Quotidienne a 2h00
echo.
echo POUR IIS (optionnel):
echo   1. Installer IIS avec ARR (Application Request Routing)
echo   2. Configurer reverse proxy vers localhost:5000
echo   3. Configurer certificat SSL
echo.
echo Support technique:
echo   Email: moa@myoneart.com
echo   Tel: +212 699 14 000 1 / +243 86 049 33 45
echo   Web: myoneart.com
echo.
echo ================================================================

echo.
set /p startService="Voulez-vous demarrer le service GEC maintenant? (O/N): "
if /i "%startService%"=="O" (
    echo Demarrage du service...
    sc start "GEC"
    echo.
    echo Service demarre ! Acces: http://localhost:5000
    echo Verifiez le statut avec: status-gec.bat
) else (
    echo.
    echo Le service peut etre demarre plus tard avec: start-gec.bat
)

echo.
echo Nettoyage des fichiers temporaires...
cd /d C:\
if exist "C:\temp\python-3.11.9-amd64.exe" del "C:\temp\python-3.11.9-amd64.exe"
if exist "C:\temp\Git-installer.exe" del "C:\temp\Git-installer.exe"

echo.
pause