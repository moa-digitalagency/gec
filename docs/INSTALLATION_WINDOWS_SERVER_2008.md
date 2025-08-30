# Installation GEC Courrier - Windows Server 2008 R2

## Prérequis Spéciaux
- Windows Server 2008 R2 SP1 minimum
- .NET Framework 4.6.1 ou supérieur
- PowerShell 3.0 ou supérieur
- Droits administrateur

## Méthode Manuelle (Recommandée pour Server 2008)

### Étape 1: Installation de Python 3.11
Téléchargement manuel requis car winget n'est pas disponible:
1. Téléchargez Python 3.11.x depuis https://www.python.org/downloads/windows/
2. Choisissez "Windows x86-64 executable installer"
3. Lors de l'installation:
   - ✅ Cochez "Add Python to PATH"
   - ✅ Cochez "Install for all users"
   - Cliquez "Install Now"

### Étape 2: Installation de Git
1. Téléchargez Git depuis https://git-scm.com/download/win
2. Installez avec les options par défaut
3. Redémarrez l'invite de commande

### Étape 3: Téléchargement du Code Source
```cmd
git clone https://github.com/moa-digitalagency/gec.git
cd gec
```

### Étape 4: Configuration de l'Environnement
```cmd
REM Créer l'environnement virtuel
python -m venv venv

REM Activer l'environnement virtuel
venv\Scripts\activate.bat
```

### Étape 5: Installation des Dépendances
```cmd
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r project-dependencies.txt
```

### Étape 6: Configuration Windows Server
```cmd
REM Créer le fichier de configuration
echo DATABASE_URL=sqlite:///instance/geccourrier.db > .env
echo SESSION_SECRET=your-server-secret-key >> .env
echo GEC_MASTER_KEY=your-server-encryption-key >> .env
echo GEC_PASSWORD_SALT=your-server-password-salt >> .env

REM Configurer le pare-feu Windows
netsh advfirewall firewall add rule name="GEC Courrier Port 5000" dir=in action=allow protocol=TCP localport=5000
```

### Étape 7: Installation en tant que Service Windows
Créez le fichier `install-service.bat`:
```batch
@echo off
cd /d "%~dp0"

REM Installer le service GEC Courrier
sc create "GEC Courrier" binPath= "\"%CD%\venv\Scripts\python.exe\" \"%CD%\main.py\"" start= auto
sc description "GEC Courrier" "Système de gestion du courrier - Ministère des Courrier RDC"

REM Démarrer le service
sc start "GEC Courrier"

echo Service GEC Courrier installé et démarré
pause
```

### Étape 8: Configuration IIS (Optionnel)
Pour une configuration avec IIS et reverse proxy:

1. Installez IIS avec les modules Application Request Routing (ARR)
2. Créez un fichier `web.config`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <rule name="GEC Courrier" stopProcessing="true">
                    <match url="(.*)" />
                    <action type="Rewrite" url="http://localhost:5000/{R:1}" />
                </rule>
            </rules>
        </rewrite>
    </system.webServer>
</configuration>
```

## Configuration Production

### Sécurité Windows Server
```cmd
REM Créer un utilisateur dédié
net user geccourrier password123 /add /comment:"Service GEC Courrier"
net localgroup Users geccourrier /delete
net localgroup "Log on as a service" geccourrier /add

REM Permissions sur le dossier
icacls "C:\gec" /grant geccourrier:(OI)(CI)F
```

### Variables d'Environnement Système
```cmd
setx DATABASE_URL "postgresql://username:password@localhost/geccourrier" /M
setx SESSION_SECRET "your-production-secret-key" /M
setx GEC_MASTER_KEY "your-production-encryption-key" /M
setx GEC_PASSWORD_SALT "your-production-password-salt" /M
```

### Backup Automatique
Créez une tâche planifiée pour la sauvegarde:
```cmd
schtasks /create /sc daily /mo 1 /tn "GEC Courrier Backup" /tr "C:\gec\backup-daily.bat" /st 02:00
```

## Dépannage Server 2008

### Erreur SSL/TLS
```cmd
REM Mettre à jour les certificats racine
certlm.msc
```

### Erreur Python pip
```cmd
python -m pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org pip
```

### Performance Monitoring
```cmd
REM Surveiller les performances
typeperf "\Process(python)\% Processor Time" "\Process(python)\Working Set"
```

## Support Technique
- **Développé par**: MOA Digital Agency LLC
- **Auteur**: AIsance KALONJI wa KALONJI  
- **Contact**: moa@myoneart.com
- **Téléphone**: +212 699 14 000 1 / +243 86 049 33 45
- **Site Web**: myoneart.com