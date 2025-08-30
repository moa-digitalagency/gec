# Installation GEC Mines - Windows 10/11

## Méthode Automatique (Recommandée)

### Téléchargement et Installation One-Click
1. Téléchargez le fichier `install-gec-windows.bat`
2. Clic droit → "Exécuter en tant qu'administrateur"
3. Suivez les instructions à l'écran
4. L'application sera automatiquement configurée et lancée

## Méthode Manuelle

### Prérequis
- Windows 10 version 1903 ou supérieure
- Connexion Internet
- Droits administrateur

### Étape 1: Installation de Python 3.11
```powershell
winget install --id Python.Python.3.11 -e
```

### Étape 2: Installation de Git
```powershell
winget install --id Git.Git -e
```

### Étape 3: Téléchargement du Code Source
```powershell
git clone https://github.com/moa-digitalagency/gec.git
cd gec
```

### Étape 4: Configuration de l'Environnement
```powershell
# Autoriser l'exécution de scripts PowerShell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force

# Créer l'environnement virtuel Python
python -m venv .venv

# Si la commande précédente échoue, essayez:
# py -3.11 -m venv .venv

# Activer l'environnement virtuel
.\.venv\Scripts\Activate.ps1
```

### Étape 5: Installation des Dépendances
```powershell
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt
```

### Étape 6: Configuration de la Base de Données
```powershell
# Créer le fichier de configuration .env
echo DATABASE_URL=sqlite:///instance/gecmines.db > .env
echo SESSION_SECRET=your-secret-key-here >> .env
echo GEC_MASTER_KEY=your-encryption-key >> .env
echo GEC_PASSWORD_SALT=your-password-salt >> .env
```

### Étape 7: Lancement de l'Application
```powershell
python .\main.py
```

L'application sera accessible à l'adresse: http://localhost:5000

## Configuration Post-Installation

### Configuration SMTP (Optionnel)
Pour activer les notifications email, ajoutez dans le fichier `.env`:
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_EMAIL=votre-email@domaine.com
SMTP_PASSWORD=votre-mot-de-passe-app
```

### Démarrage Automatique au Boot
1. Créez un raccourci vers `start-gec.bat` dans le dossier de démarrage:
   - Appuyez sur `Win + R`, tapez `shell:startup`
2. Copiez le raccourci dans ce dossier

## Dépannage

### Erreur "winget command not found"
- Installez App Installer depuis Microsoft Store
- Ou téléchargez manuellement Python 3.11 et Git depuis leurs sites officiels

### Erreur d'exécution PowerShell
```powershell
Set-ExecutionPolicy -Scope CurrentUser Unrestricted -Force
```

### Port 5000 déjà utilisé
```powershell
netstat -ano | findstr :5000
taskkill /PID <ProcessID> /F
```

## Support Technique
- **Développé par**: MOA Digital Agency LLC
- **Auteur**: AIsance KALONJI wa KALONJI
- **Contact**: moa@myoneart.com
- **Téléphone**: +212 699 14 000 1 / +243 86 049 33 45
- **Site Web**: myoneart.com