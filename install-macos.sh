#!/bin/bash
# =====================================================
# GEC Mines - Script d'Installation Automatique macOS
# =====================================================
# Copyright (c) 2025 MOA Digital Agency LLC
# Développé par : AIsance KALONJI wa KALONJI
# Email : moa@myoneart.com | moa.myoneart@gmail.com
# =====================================================

set -e  # Arrêter en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Variables
INSTALL_DIR="$HOME/gec-mines"
PYTHON_VERSION="3.11"

echo -e "${GREEN}🚀 Installation de GEC Mines pour macOS${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""

# Fonction pour vérifier si une commande existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Fonction pour afficher un message d'erreur et quitter
error_exit() {
    echo -e "${RED}❌ $1${NC}" >&2
    exit 1
}

# Fonction pour afficher un message de succès
success_msg() {
    echo -e "${GREEN}   ✅ $1${NC}"
}

# Fonction pour afficher un message d'information
info_msg() {
    echo -e "${BLUE}$1${NC}"
}

# Fonction pour afficher un message d'avertissement
warning_msg() {
    echo -e "${YELLOW}   ⚠️  $1${NC}"
}

# Étape 1: Vérifier et installer les dépendances système
info_msg "📦 Vérification des dépendances système..."

# Vérifier si Homebrew est installé
if ! command_exists brew; then
    warning_msg "Homebrew n'est pas installé"
    echo -e "${YELLOW}📥 Installation de Homebrew...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || error_exit "Erreur lors de l'installation de Homebrew"
    
    # Ajouter Homebrew au PATH pour les puces Apple Silicon
    if [[ $(uname -m) == "arm64" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    
    success_msg "Homebrew installé"
else
    success_msg "Homebrew déjà installé"
fi

# Mettre à jour Homebrew
echo -e "${BLUE}   🔄 Mise à jour de Homebrew...${NC}"
brew update >/dev/null 2>&1

# Installer Python 3.11
if ! command_exists python3.11; then
    echo -e "${BLUE}   📥 Installation de Python 3.11...${NC}"
    brew install python@3.11 || error_exit "Erreur lors de l'installation de Python 3.11"
    success_msg "Python 3.11 installé"
else
    success_msg "Python 3.11 déjà installé"
fi

# Installer Git
if ! command_exists git; then
    echo -e "${BLUE}   📥 Installation de Git...${NC}"
    brew install git || error_exit "Erreur lors de l'installation de Git"
    success_msg "Git installé"
else
    success_msg "Git déjà installé"
fi

# Étape 2: Cloner le projet
echo ""
info_msg "📂 Clonage du projet GEC Mines..."

if [ -d "$INSTALL_DIR" ]; then
    warning_msg "Le dossier $INSTALL_DIR existe déjà"
    read -p "   Voulez-vous le supprimer et recommencer? (o/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Oo]$ ]]; then
        rm -rf "$INSTALL_DIR"
        echo -e "${BLUE}   🗑️  Dossier supprimé${NC}"
    else
        error_exit "Installation annulée"
    fi
fi

git clone https://github.com/moa-digitalagency/gec.git "$INSTALL_DIR" || error_exit "Erreur lors du clonage du projet"
cd "$INSTALL_DIR"
success_msg "Projet cloné dans $INSTALL_DIR"

# Étape 3: Configurer l'environnement Python
echo ""
info_msg "🐍 Configuration de l'environnement Python..."

# Créer l'environnement virtuel
python3.11 -m venv .venv || error_exit "Erreur lors de la création de l'environnement virtuel"
success_msg "Environnement virtuel créé"

# Activer l'environnement virtuel
source .venv/bin/activate || error_exit "Erreur lors de l'activation de l'environnement virtuel"
success_msg "Environnement virtuel activé"

# Étape 4: Installer les dépendances Python
echo ""
info_msg "📦 Installation des dépendances Python..."

python -m pip install -U pip wheel || error_exit "Erreur lors de la mise à jour de pip"
success_msg "pip et wheel mis à jour"

python -m pip install -r project-dependencies.txt || error_exit "Erreur lors de l'installation des dépendances"
success_msg "Dépendances installées"

# Étape 5: Configuration initiale
echo ""
info_msg "⚙️  Configuration initiale..."

# Créer le fichier .env s'il n'existe pas
if [ ! -f ".env" ]; then
    cat > .env << EOF
# Configuration GEC Mines
DATABASE_URL=sqlite:///instance/gecmines.db
SESSION_SECRET=$(openssl rand -base64 32)
GEC_MASTER_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
GEC_PASSWORD_SALT=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)

# Configuration SMTP (optionnel)
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_EMAIL=votre-email@gmail.com
# SMTP_PASSWORD=votre-mot-de-passe-app
# SMTP_USE_TLS=True
EOF
    success_msg "Fichier .env créé avec configuration par défaut"
else
    success_msg "Fichier .env existe déjà"
fi

# Créer les dossiers nécessaires
for folder in instance uploads backups exports; do
    if [ ! -d "$folder" ]; then
        mkdir -p "$folder"
        success_msg "Dossier '$folder' créé"
    fi
done

# Étape 6: Test de l'installation
echo ""
info_msg "🧪 Test de l'installation..."

python -c "import flask, sqlalchemy, cryptography; print('   ✅ Modules principaux importés')" || error_exit "Erreur lors du test d'importation"

# Créer un script de démarrage
cat > start-gec.sh << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source .venv/bin/activate
python main.py
EOF

chmod +x start-gec.sh
success_msg "Script de démarrage 'start-gec.sh' créé"

# Créer un alias pour le terminal (optionnel)
echo ""
info_msg "🔗 Configuration des raccourcis..."

SHELL_RC=""
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [ -n "$SHELL_RC" ] && [ -f "$SHELL_RC" ]; then
    if ! grep -q "alias gec-start" "$SHELL_RC"; then
        echo "" >> "$SHELL_RC"
        echo "# GEC Mines shortcuts" >> "$SHELL_RC"
        echo "alias gec-start='cd \"$INSTALL_DIR\" && source .venv/bin/activate && python main.py'" >> "$SHELL_RC"
        echo "alias gec-cd='cd \"$INSTALL_DIR\"'" >> "$SHELL_RC"
        success_msg "Raccourcis ajoutés à $SHELL_RC"
        echo -e "${CYAN}   💡 Redémarrez votre terminal ou tapez 'source $SHELL_RC'${NC}"
        echo -e "${CYAN}   💡 Ensuite utilisez 'gec-start' pour démarrer l'application${NC}"
    fi
fi

# Étape 7: Instructions finales
echo ""
echo -e "${GREEN}🎉 Installation terminée avec succès!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "${CYAN}📍 Dossier d'installation: $INSTALL_DIR${NC}"
echo ""
echo -e "${YELLOW}🚀 Pour démarrer GEC Mines:${NC}"
echo "   1. Exécutez: ./start-gec.sh"
echo "   2. Ou manuellement:"
echo "      cd \"$INSTALL_DIR\""
echo "      source .venv/bin/activate"
echo "      python main.py"
if [ -n "$SHELL_RC" ]; then
    echo "   3. Ou utilisez le raccourci: gec-start"
fi
echo ""
echo -e "${CYAN}🌐 L'application sera accessible sur: http://localhost:5000${NC}"
echo ""
echo -e "${MAGENTA}📧 Support: moa@myoneart.com | moa.myoneart@gmail.com${NC}"
echo -e "${MAGENTA}🌐 Site web: https://myoneart.com${NC}"
echo ""
echo -e "${NC}© 2025 MOA Digital Agency LLC${NC}"

# Proposer de démarrer l'application
echo ""
read -p "Voulez-vous démarrer l'application maintenant? (o/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    echo ""
    echo -e "${GREEN}🚀 Démarrage de GEC Mines...${NC}"
    python main.py
fi