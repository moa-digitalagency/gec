# Installation GEC Mines - macOS

## Méthode Automatique (Recommandée)

### Installation One-Click
1. Téléchargez le fichier `install-gec-macos.sh`
2. Ouvrez Terminal
3. Exécutez: `chmod +x install-gec-macos.sh && ./install-gec-macos.sh`
4. Suivez les instructions à l'écran

## Méthode Manuelle

### Prérequis
- macOS 10.15 (Catalina) ou supérieur
- Xcode Command Line Tools
- Connexion Internet

### Étape 1: Installation d'Homebrew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Étape 2: Installation de Python 3.11 et Git
```bash
brew install python@3.11 git
```

### Étape 3: Téléchargement du Code Source
```bash
git clone https://github.com/moa-digitalagency/gec.git
cd gec
```

### Étape 4: Configuration de l'Environnement
```bash
# Créer l'environnement virtuel
python3.11 -m venv .venv

# Activer l'environnement virtuel
source .venv/bin/activate
```

### Étape 5: Installation des Dépendances
```bash
pip install --upgrade pip wheel
pip install -r project-dependencies.txt
```

### Étape 6: Configuration de la Base de Données
```bash
# Créer le fichier de configuration
cat > .env << EOF
DATABASE_URL=sqlite:///instance/gecmines.db
SESSION_SECRET=your-secret-key-here
GEC_MASTER_KEY=your-encryption-key
GEC_PASSWORD_SALT=your-password-salt
EOF
```

### Étape 7: Lancement de l'Application
```bash
python main.py
```

L'application sera accessible à l'adresse: http://localhost:5000

## Configuration Production macOS

### Installation avec PostgreSQL
```bash
# Installer PostgreSQL
brew install postgresql@14
brew services start postgresql@14

# Créer la base de données
createdb gecmines

# Mettre à jour .env
echo "DATABASE_URL=postgresql://$(whoami)@localhost/gecmines" > .env
```

### Service macOS (LaunchDaemon)
Créez le fichier `~/Library/LaunchAgents/com.moa.gecmines.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.moa.gecmines</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3.11</string>
        <string>/Users/$(whoami)/gec/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/$(whoami)/gec</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/$(whoami)/gec/logs/gecmines.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/$(whoami)/gec/logs/gecmines.error.log</string>
</dict>
</plist>
```

Charger le service:
```bash
launchctl load ~/Library/LaunchAgents/com.moa.gecmines.plist
launchctl start com.moa.gecmines
```

### Configuration HTTPS avec nginx
```bash
# Installer nginx
brew install nginx

# Configuration nginx
sudo tee /opt/homebrew/etc/nginx/servers/gecmines.conf << EOF
server {
    listen 80;
    server_name localhost;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Démarrer nginx
brew services start nginx
```

## Installation Docker (Alternative)

### Dockerfile pour macOS
```bash
# Créer l'image Docker
docker build -t gecmines .

# Lancer le conteneur
docker run -d -p 5000:5000 --name gecmines \
  -v gecmines-data:/app/instance \
  -v gecmines-uploads:/app/uploads \
  gecmines
```

## Dépannage macOS

### Erreur de permissions
```bash
sudo chown -R $(whoami) /usr/local/lib/python3.11/site-packages
```

### Erreur Xcode Command Line Tools
```bash
xcode-select --install
```

### Port 5000 utilisé par AirPlay
```bash
# Désactiver AirPlay Receiver dans Préférences Système > Partage
# Ou utiliser un autre port:
export FLASK_PORT=8000
python main.py
```

### Problème SSL avec Homebrew
```bash
brew update
brew doctor
```

## Performance et Monitoring

### Surveillance des ressources
```bash
# CPU et mémoire
top -pid $(pgrep -f "python.*main.py")

# Espace disque
du -sh /Users/$(whoami)/gec/
```

### Logs système
```bash
# Voir les logs de l'application
tail -f /Users/$(whoami)/gec/logs/gecmines.log

# Logs système macOS
log show --predicate 'subsystem contains "com.moa.gecmines"' --last 1h
```

## Support Technique
- **Développé par**: MOA Digital Agency LLC
- **Auteur**: AIsance KALONJI wa KALONJI
- **Contact**: moa@myoneart.com
- **Téléphone**: +212 699 14 000 1 / +243 86 049 33 45
- **Site Web**: myoneart.com