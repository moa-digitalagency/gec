#!/bin/bash
# =====================================================
# GEC Mines - Script d'Installation Automatique Linux
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

echo -e "${GREEN}🚀 Installation de GEC Mines pour Linux${NC}"
echo -e "${GREEN}=========================================${NC}"
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

# Détecter la distribution Linux
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    elif command_exists lsb_release; then
        DISTRO=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
        VERSION=$(lsb_release -sr)
    else
        error_exit "Impossible de détecter la distribution Linux"
    fi
}

# Fonction pour installer les paquets selon la distribution
install_packages() {
    local packages="$1"
    
    case $DISTRO in
        ubuntu|debian)
            if ! command_exists sudo; then
                error_exit "sudo n'est pas installé. Veuillez l'installer ou exécuter en tant que root"
            fi
            
            info_msg "📦 Mise à jour des paquets ($DISTRO)..."
            sudo apt update >/dev/null 2>&1
            
            info_msg "📥 Installation des dépendances..."
            sudo apt install -y $packages python3.11-venv python3.11-dev build-essential >/dev/null 2>&1 || \
                error_exit "Erreur lors de l'installation des paquets"
            ;;
            
        centos|rhel|fedora|rocky|almalinux)
            if ! command_exists sudo; then
                error_exit "sudo n'est pas installé. Veuillez l'installer ou exécuter en tant que root"
            fi
            
            # Choisir le gestionnaire de paquets approprié
            if command_exists dnf; then
                PKG_MGR="dnf"
            elif command_exists yum; then
                PKG_MGR="yum"
            else
                error_exit "Aucun gestionnaire de paquets supporté trouvé (dnf/yum)"
            fi
            
            info_msg "📦 Mise à jour des paquets ($DISTRO avec $PKG_MGR)..."
            sudo $PKG_MGR update -y >/dev/null 2>&1
            
            info_msg "📥 Installation des dépendances..."
            sudo $PKG_MGR install -y $packages python3.11-devel gcc gcc-c++ make >/dev/null 2>&1 || \
                error_exit "Erreur lors de l'installation des paquets"
            ;;
            
        arch|manjaro)
            if ! command_exists sudo; then
                error_exit "sudo n'est pas installé. Veuillez l'installer ou exécuter en tant que root"
            fi
            
            info_msg "📦 Mise à jour des paquets ($DISTRO)..."
            sudo pacman -Syu --noconfirm >/dev/null 2>&1
            
            info_msg "📥 Installation des dépendances..."
            sudo pacman -S --noconfirm python git postgresql-libs base-devel >/dev/null 2>&1 || \
                error_exit "Erreur lors de l'installation des paquets"
            ;;
            
        opensuse*|sles)
            if ! command_exists sudo; then
                error_exit "sudo n'est pas installé. Veuillez l'installer ou exécuter en tant que root"
            fi
            
            info_msg "📦 Mise à jour des paquets ($DISTRO)..."
            sudo zypper refresh >/dev/null 2>&1
            
            info_msg "📥 Installation des dépendances..."
            sudo zypper install -y python311 python311-devel git postgresql-devel gcc gcc-c++ make >/dev/null 2>&1 || \
                error_exit "Erreur lors de l'installation des paquets"
            ;;
            
        *)
            warning_msg "Distribution $DISTRO non officiellement supportée"
            warning_msg "Tentative d'installation générique..."
            
            # Essayer apt en premier (Debian-like)
            if command_exists apt; then
                sudo apt update >/dev/null 2>&1
                sudo apt install -y $packages python3.11-venv python3.11-dev build-essential >/dev/null 2>&1
            # Puis dnf/yum (RedHat-like)
            elif command_exists dnf; then
                sudo dnf install -y $packages python3.11-devel gcc gcc-c++ make >/dev/null 2>&1
            elif command_exists yum; then
                sudo yum install -y $packages python3.11-devel gcc gcc-c++ make >/dev/null 2>&1
            # Puis pacman (Arch-like)
            elif command_exists pacman; then
                sudo pacman -S --noconfirm python git postgresql-libs base-devel >/dev/null 2>&1
            else
                error_exit "Gestionnaire de paquets non supporté pour cette distribution"
            fi
            ;;
    esac
}

# Étape 1: Détecter la distribution et installer les dépendances
info_msg "🔍 Détection de la distribution Linux..."
detect_distro
success_msg "Distribution détectée: $DISTRO $VERSION"

info_msg "📦 Installation des dépendances système..."

# Paquets de base pour la plupart des distributions
BASE_PACKAGES="python3.11 git postgresql-client"

# Installer les paquets selon la distribution
install_packages "$BASE_PACKAGES"
success_msg "Dépendances système installées"

# Étape 2: Vérifier les installations
info_msg "🧪 Vérification des installations..."

if ! command_exists python3.11; then
    error_exit "Python 3.11 n'a pas été installé correctement"
fi
success_msg "Python 3.11 vérifié"

if ! command_exists git; then
    error_exit "Git n'a pas été installé correctement"
fi
success_msg "Git vérifié"

# Étape 3: Cloner le projet
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

# Étape 4: Configurer l'environnement Python
echo ""
info_msg "🐍 Configuration de l'environnement Python..."

# Créer l'environnement virtuel
python3.11 -m venv .venv || error_exit "Erreur lors de la création de l'environnement virtuel"
success_msg "Environnement virtuel créé"

# Activer l'environnement virtuel
source .venv/bin/activate || error_exit "Erreur lors de l'activation de l'environnement virtuel"
success_msg "Environnement virtuel activé"

# Étape 5: Installer les dépendances Python
echo ""
info_msg "📦 Installation des dépendances Python..."

python -m pip install -U pip wheel || error_exit "Erreur lors de la mise à jour de pip"
success_msg "pip et wheel mis à jour"

python -m pip install -r project-dependencies.txt || error_exit "Erreur lors de l'installation des dépendances"
success_msg "Dépendances installées"

# Étape 6: Configuration initiale
echo ""
info_msg "⚙️  Configuration initiale..."

# Créer le fichier .env s'il n'existe pas
if [ ! -f ".env" ]; then
    cat > .env << EOF
# Configuration GEC Mines
DATABASE_URL=sqlite:///instance/gecmines.db
SESSION_SECRET=$(openssl rand -base64 32 2>/dev/null || dd if=/dev/urandom bs=32 count=1 2>/dev/null | base64)
GEC_MASTER_KEY=$(openssl rand -base64 32 2>/dev/null | tr -d "=+/" | cut -c1-32 || dd if=/dev/urandom bs=32 count=1 2>/dev/null | base64 | tr -d "=+/" | cut -c1-32)
GEC_PASSWORD_SALT=$(openssl rand -base64 16 2>/dev/null | tr -d "=+/" | cut -c1-16 || dd if=/dev/urandom bs=16 count=1 2>/dev/null | base64 | tr -d "=+/" | cut -c1-16)

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

# Étape 7: Test de l'installation
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

# Créer un service systemd pour l'utilisateur (optionnel)
if command_exists systemctl; then
    info_msg "🔧 Configuration du service systemd utilisateur..."
    
    mkdir -p ~/.config/systemd/user
    
    cat > ~/.config/systemd/user/gec-mines.service << EOF
[Unit]
Description=GEC Mines Application
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/.venv/bin
ExecStart=$INSTALL_DIR/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF
    
    systemctl --user daemon-reload
    success_msg "Service systemd configuré"
    echo -e "${CYAN}   💡 Utilisez 'systemctl --user start gec-mines' pour démarrer en service${NC}"
    echo -e "${CYAN}   💡 Utilisez 'systemctl --user enable gec-mines' pour démarrage automatique${NC}"
fi

# Créer des alias pour le terminal
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

# Étape 8: Instructions finales
echo ""
echo -e "${GREEN}🎉 Installation terminée avec succès!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "${CYAN}📍 Dossier d'installation: $INSTALL_DIR${NC}"
echo -e "${CYAN}🖥️  Distribution: $DISTRO $VERSION${NC}"
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
if command_exists systemctl; then
    echo "   4. Ou comme service: systemctl --user start gec-mines"
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