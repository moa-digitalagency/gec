#!/bin/bash

# Installation Automatique GEC - macOS
# Développé par: MOA Digital Agency LLC
# Auteur: AIsance KALONJI wa KALONJI
# Contact: moa@myoneart.com

set -e

echo "================================================================"
echo "           Installation Automatique GEC - macOS"
echo "================================================================"
echo "Développé par: MOA Digital Agency LLC"
echo "Auteur: AIsance KALONJI wa KALONJI"
echo "Contact: moa@myoneart.com"
echo "================================================================"
echo

# Vérification de macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ [ERREUR] Ce script est conçu pour macOS uniquement"
    exit 1
fi

echo "🔍 [ETAPE 1/8] Vérification des prérequis..."

# Vérifier si Xcode Command Line Tools est installé
if ! xcode-select -p &> /dev/null; then
    echo "📦 Installation des Xcode Command Line Tools..."
    xcode-select --install
    echo "⏳ Veuillez terminer l'installation des Xcode Command Line Tools puis relancer ce script"
    exit 1
else
    echo "✅ [OK] Xcode Command Line Tools détecté"
fi

echo
echo "🍺 [ETAPE 2/8] Installation d'Homebrew..."

# Vérifier si Homebrew est installé
if ! command -v brew &> /dev/null; then
    echo "📦 Installation d'Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Ajouter Homebrew au PATH pour Apple Silicon
    if [[ $(uname -m) == "arm64" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    
    echo "✅ [OK] Homebrew installé avec succès"
else
    echo "✅ [OK] Homebrew déjà installé"
    brew update
fi

echo
echo "🐍 [ETAPE 3/8] Installation de Python 3.11 et Git..."

# Installer Python 3.11 et Git
brew install python@3.11 git

# Créer des liens symboliques si nécessaire
if [[ $(uname -m) == "arm64" ]]; then
    PYTHON_PATH="/opt/homebrew/bin/python3.11"
else
    PYTHON_PATH="/usr/local/bin/python3.11"
fi

echo "✅ [OK] Python 3.11 et Git installés"

echo
echo "📥 [ETAPE 4/8] Téléchargement du code source GEC..."

# Aller dans le répertoire home de l'utilisateur
cd "$HOME"

# Télécharger ou mettre à jour le code source
if [ -d "gec" ]; then
    echo "📂 Dossier gec existant, mise à jour..."
    cd gec
    git pull origin main
    cd ..
else
    git clone https://github.com/moa-digitalagency/gec.git
    echo "✅ [OK] Code source téléchargé avec succès"
fi

cd gec

echo
echo "⚙️  [ETAPE 5/8] Configuration de l'environnement Python..."

# Créer l'environnement virtuel
$PYTHON_PATH -m venv .venv

# Activer l'environnement virtuel
source .venv/bin/activate

# Mettre à jour pip et installer les dépendances
pip install --upgrade pip wheel
pip install -r project-dependencies.txt

echo "✅ [OK] Dépendances installées avec succès"

echo
echo "🗄️  [ETAPE 6/8] Configuration de la base de données..."

# Créer le fichier de configuration s'il n'existe pas
if [ ! -f ".env" ]; then
    cat > .env << EOF
DATABASE_URL=sqlite:///instance/gecmines.db
SESSION_SECRET=$(openssl rand -hex 32)
GEC_MASTER_KEY=$(openssl rand -hex 32)
GEC_PASSWORD_SALT=$(openssl rand -hex 16)
EOF
    echo "✅ [OK] Fichier de configuration créé"
else
    echo "ℹ️  [INFO] Fichier .env existant, conservation des paramètres"
fi

# Créer le dossier instance s'il n'existe pas
mkdir -p instance
mkdir -p logs

echo
echo "🚀 [ETAPE 7/8] Création des scripts de démarrage..."

# Créer un script de démarrage
cat > start-gec.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate

echo
echo "============================================"
echo "  GEC - Système de Gestion du Courrier"
echo "  Accès: http://localhost:5000"
echo "  Développé par MOA Digital Agency LLC"
echo "============================================"
echo

python main.py
EOF

chmod +x start-gec.sh

# Créer un fichier plist pour LaunchAgent (démarrage automatique optionnel)
mkdir -p ~/Library/LaunchAgents

cat > ~/Library/LaunchAgents/com.moa.gecmines.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.moa.gecmines</string>
    <key>ProgramArguments</key>
    <array>
        <string>$HOME/gec/start-gec.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$HOME/gec</string>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/gec/logs/gecmines.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/gec/logs/gecmines.error.log</string>
</dict>
</plist>
EOF

echo
echo "🎯 [ETAPE 8/8] Configuration finale..."

# Créer un alias pour faciliter le démarrage
if ! grep -q "alias gec-start" ~/.zshrc 2>/dev/null; then
    echo "alias gec-start='cd $HOME/gec && ./start-gec.sh'" >> ~/.zshrc
    echo "alias gec-stop='pkill -f \"python.*main.py\"'" >> ~/.zshrc
fi

if ! grep -q "alias gec-start" ~/.bash_profile 2>/dev/null; then
    echo "alias gec-start='cd $HOME/gec && ./start-gec.sh'" >> ~/.bash_profile
    echo "alias gec-stop='pkill -f \"python.*main.py\"'" >> ~/.bash_profile
fi

echo
echo "================================================================"
echo "                    INSTALLATION TERMINÉE !"
echo "================================================================"
echo
echo "✅ L'application GEC a été installée avec succès."
echo
echo "🚀 Pour démarrer l'application:"
echo "   1. Ouvrez Terminal"
echo "   2. Tapez: gec-start"
echo "   3. Ou exécutez: cd $HOME/gec && ./start-gec.sh"
echo
echo "🌐 L'application sera accessible à l'adresse:"
echo "   http://localhost:5000"
echo
echo "🛑 Pour arrêter l'application:"
echo "   Tapez: gec-stop"
echo "   Ou appuyez Ctrl+C dans le terminal"
echo
echo "⚙️  Configuration SMTP pour les emails (optionnel):"
echo "   Éditez le fichier .env pour ajouter vos paramètres SMTP"
echo
echo "🔧 Support technique:"
echo "   Email: moa@myoneart.com"
echo "   Tél: +212 699 14 000 1 / +243 86 049 33 45"
echo "   Web: myoneart.com"
echo
echo "================================================================"

echo
read -p "Voulez-vous démarrer GEC maintenant? (o/N): " start_now
if [[ $start_now =~ ^[Oo]$ ]]; then
    echo "🚀 Démarrage de GEC..."
    echo "Ouvrez votre navigateur à l'adresse: http://localhost:5000"
    echo
    ./start-gec.sh
else
    echo
    echo "ℹ️  Vous pouvez démarrer GEC plus tard en tapant 'gec-start' dans Terminal"
    echo "   ou en exécutant ./start-gec.sh dans le dossier $HOME/gec"
fi