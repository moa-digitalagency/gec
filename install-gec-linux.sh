#!/bin/bash

# Installation Automatique GEC - Linux
# Développé par: MOA Digital Agency LLC
# Auteur: AIsance KALONJI wa KALONJI
# Contact: moa@myoneart.com

set -e

echo "================================================================"
echo "           Installation Automatique GEC - Linux"
echo "================================================================"
echo "Développé par: MOA Digital Agency LLC"
echo "Auteur: AIsance KALONJI wa KALONJI"
echo "Contact: moa@myoneart.com"
echo "================================================================"
echo

# Détection de la distribution Linux
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si)
        VER=$(lsb_release -sr)
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        OS=$DISTRIB_ID
        VER=$DISTRIB_RELEASE
    elif [ -f /etc/debian_version ]; then
        OS=Debian
        VER=$(cat /etc/debian_version)
    elif [ -f /etc/SuSe-release ]; then
        OS=openSUSE
    elif [ -f /etc/redhat-release ]; then
        OS=RedHat
    else
        OS=$(uname -s)
        VER=$(uname -r)
    fi
}

# Installation des dépendances selon la distribution
install_dependencies() {
    echo "🔍 [ETAPE 1/8] Détection du système..."
    detect_os
    echo "✅ Système détecté: $OS $VER"
    
    echo
    echo "📦 [ETAPE 2/8] Installation des dépendances système..."
    
    if [[ "$OS" == *"Ubuntu"* || "$OS" == *"Debian"* ]]; then
        echo "🐧 Installation pour Ubuntu/Debian..."
        sudo apt update
        sudo apt install -y software-properties-common
        sudo add-apt-repository ppa:deadsnakes/ppa -y
        sudo apt update
        sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip git wget curl build-essential libpq-dev libssl-dev libffi-dev
        PYTHON_CMD="python3.11"
        
    elif [[ "$OS" == *"CentOS"* || "$OS" == *"Red Hat"* || "$OS" == *"RHEL"* ]]; then
        echo "🔴 Installation pour CentOS/RHEL..."
        sudo yum update -y
        sudo yum groupinstall -y "Development Tools"
        sudo yum install -y python3 python3-pip python3-devel git wget curl postgresql-devel openssl-devel libffi-devel
        PYTHON_CMD="python3"
        
    elif [[ "$OS" == *"Fedora"* ]]; then
        echo "🎩 Installation pour Fedora..."
        sudo dnf update -y
        sudo dnf groupinstall -y "Development Tools"
        sudo dnf install -y python3.11 python3-pip python3-devel git wget curl postgresql-devel openssl-devel libffi-devel
        PYTHON_CMD="python3.11"
        
    elif [[ "$OS" == *"openSUSE"* ]]; then
        echo "🦎 Installation pour openSUSE..."
        sudo zypper refresh
        sudo zypper install -y python311 python3-pip python3-devel git wget curl postgresql-devel libopenssl-devel libffi-devel
        PYTHON_CMD="python3.11"
        
    elif [[ "$OS" == *"Arch"* ]]; then
        echo "⚡ Installation pour Arch Linux..."
        sudo pacman -Syu --noconfirm
        sudo pacman -S --noconfirm python python-pip git wget curl postgresql-libs openssl libffi base-devel
        PYTHON_CMD="python"
        
    else
        echo "⚠️  Distribution non reconnue: $OS"
        echo "Installation générique avec python3..."
        PYTHON_CMD="python3"
    fi
    
    echo "✅ [OK] Dépendances système installées"
}

# Fonction principale d'installation
main_installation() {
    echo
    echo "📥 [ETAPE 3/8] Téléchargement du code source GEC..."
    
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
    echo "⚙️  [ETAPE 4/8] Configuration de l'environnement Python..."
    
    # Créer l'environnement virtuel
    $PYTHON_CMD -m venv .venv
    
    # Activer l'environnement virtuel
    source .venv/bin/activate
    
    # Mettre à jour pip et installer les dépendances
    pip install --upgrade pip wheel setuptools
    pip install -r project-dependencies.txt
    
    echo "✅ [OK] Dépendances Python installées avec succès"
    
    echo
    echo "🗄️  [ETAPE 5/8] Configuration de la base de données..."
    
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
    
    # Créer les dossiers nécessaires
    mkdir -p instance logs uploads backups exports
    
    echo
    echo "🚀 [ETAPE 6/8] Création des scripts de démarrage..."
    
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
    
    # Créer un script d'arrêt
    cat > stop-gec.sh << 'EOF'
#!/bin/bash
echo "🛑 Arrêt de GEC..."
pkill -f "python.*main.py" || echo "Aucun processus GEC trouvé"
echo "✅ GEC arrêté"
EOF
    
    chmod +x stop-gec.sh
    
    echo
    echo "🔧 [ETAPE 7/8] Configuration du service systemd (optionnel)..."
    
    # Demander si l'utilisateur veut installer le service système
    read -p "Voulez-vous installer GEC comme service système? (o/N): " install_service
    
    if [[ $install_service =~ ^[Oo]$ ]]; then
        # Créer l'utilisateur système gecmines
        if ! id "gecmines" &>/dev/null; then
            sudo useradd -r -s /bin/false gecmines
        fi
        
        # Copier l'application vers /opt
        sudo mkdir -p /opt/gecmines
        sudo cp -r . /opt/gecmines/
        sudo chown -R gecmines:gecmines /opt/gecmines
        
        # Créer le fichier service systemd
        sudo tee /etc/systemd/system/gecmines.service > /dev/null << EOF
[Unit]
Description=GEC - Système de Gestion du Courrier
After=network.target

[Service]
Type=simple
User=gecmines
Group=gecmines
WorkingDirectory=/opt/gecmines
Environment=PATH=/opt/gecmines/.venv/bin
ExecStart=/opt/gecmines/.venv/bin/python main.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        # Activer et démarrer le service
        sudo systemctl daemon-reload
        sudo systemctl enable gecmines
        
        echo "✅ [OK] Service systemd configuré"
        SERVICE_INSTALLED=true
    else
        SERVICE_INSTALLED=false
    fi
    
    echo
    echo "🎯 [ETAPE 8/8] Configuration finale..."
    
    # Ajouter des alias dans le shell
    if [ "$SHELL" = "/bin/bash" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ "$SHELL" = "/bin/zsh" ]; then
        SHELL_RC="$HOME/.zshrc"
    else
        SHELL_RC="$HOME/.profile"
    fi
    
    if ! grep -q "alias gec-start" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# GEC aliases" >> "$SHELL_RC"
        echo "alias gec-start='cd $HOME/gec && ./start-gec.sh'" >> "$SHELL_RC"
        echo "alias gec-stop='cd $HOME/gec && ./stop-gec.sh'" >> "$SHELL_RC"
        echo "alias gec-logs='tail -f $HOME/gec/logs/gecmines.log'" >> "$SHELL_RC"
    fi
}

# Installation des dépendances
install_dependencies

# Installation principale
main_installation

echo
echo "================================================================"
echo "                    INSTALLATION TERMINÉE !"
echo "================================================================"
echo
echo "✅ L'application GEC a été installée avec succès."
echo

if [ "$SERVICE_INSTALLED" = true ]; then
    echo "🏗️  Installation en tant que service système:"
    echo "   Démarrer: sudo systemctl start gecmines"
    echo "   Arrêter:  sudo systemctl stop gecmines"
    echo "   Status:   sudo systemctl status gecmines"
    echo "   Logs:     sudo journalctl -u gecmines -f"
    echo
    read -p "Voulez-vous démarrer le service maintenant? (o/N): " start_service
    if [[ $start_service =~ ^[Oo]$ ]]; then
        sudo systemctl start gecmines
        echo "✅ Service démarré"
    fi
else
    echo "🚀 Pour démarrer l'application:"
    echo "   1. Tapez: gec-start"
    echo "   2. Ou exécutez: cd $HOME/gec && ./start-gec.sh"
    echo
    echo "🛑 Pour arrêter l'application:"
    echo "   Tapez: gec-stop"
    echo "   Ou appuyez Ctrl+C dans le terminal"
fi

echo
echo "🌐 L'application sera accessible à l'adresse:"
echo "   http://localhost:5000"
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

if [ "$SERVICE_INSTALLED" = false ]; then
    echo
    read -p "Voulez-vous démarrer GEC maintenant? (o/N): " start_now
    if [[ $start_now =~ ^[Oo]$ ]]; then
        echo "🚀 Démarrage de GEC..."
        echo "Ouvrez votre navigateur à l'adresse: http://localhost:5000"
        echo
        ./start-gec.sh
    else
        echo
        echo "ℹ️  Vous pouvez démarrer GEC plus tard en tapant 'gec-start'"
        echo "   ou en exécutant ./start-gec.sh dans le dossier $HOME/gec"
    fi
fi