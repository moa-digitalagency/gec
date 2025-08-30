#!/bin/bash
# =============================================================
# GEC Mines - Script d'installation automatique pour Linux
# =============================================================
# Copyright (c) 2025 MOA Digital Agency LLC
# Développé par AIsance KALONJI wa KALONJI
# Contact: moa@myoneart.com | +212 699 14 000 1
# =============================================================

set -e

echo ""
echo "========================================"
echo "   GEC Mines - Installation Linux"
echo "========================================"
echo ""

# Détecter la distribution Linux
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
elif type lsb_release >/dev/null 2>&1; then
    OS=$(lsb_release -si)
    VER=$(lsb_release -sr)
else
    OS=$(uname -s)
    VER=$(uname -r)
fi

echo "[INFO] Système détecté: $OS $VER"

# Installation des dépendances selon la distribution
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    echo "[INFO] Installation pour Ubuntu/Debian..."
    
    # Mettre à jour les packages
    echo "[1/6] Mise à jour du système..."
    sudo apt update && sudo apt upgrade -y
    
    # Installer les dépendances
    echo "[2/6] Installation de Python 3.11, pip et Git..."
    sudo apt install python3.11 python3.11-venv python3-pip git -y
    
elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Fedora"* ]]; then
    echo "[INFO] Installation pour CentOS/RHEL/Fedora..."
    
    # Mettre à jour les packages
    echo "[1/6] Mise à jour du système..."
    if command -v dnf &> /dev/null; then
        sudo dnf update -y
        sudo dnf install python3.11 python3-pip git -y
    else
        sudo yum update -y
        sudo yum install python3.11 python3-pip git -y
    fi
    
else
    echo "[AVERTISSEMENT] Distribution non reconnue. Tentative avec les commandes génériques..."
fi

# Vérifier que Python 3.11 est installé
if ! command -v python3.11 &> /dev/null; then
    echo "[ERREUR] Python 3.11 n'a pas pu être installé."
    echo "Installez Python 3.11 manuellement puis relancez ce script."
    exit 1
fi

echo "[INFO] Python 3.11 et Git installés avec succès."
echo ""

# Créer l'environnement virtuel
echo "[3/6] Création de l'environnement virtuel..."
if [ -d ".venv" ]; then
    echo "L'environnement virtuel existe déjà."
else
    python3.11 -m venv .venv
fi

# Activer l'environnement virtuel
echo "[4/6] Activation de l'environnement virtuel..."
source .venv/bin/activate

# Mettre à jour pip
echo "[5/6] Mise à jour de pip..."
python -m pip install -U pip wheel

# Installer les dépendances
echo "[6/6] Installation des dépendances Python..."
pip install -r project-dependencies.txt

# Vérifier l'installation
echo "Vérification de l'installation..."
python -c "import flask; print('Flask:', flask.__version__)"
python -c "import sqlalchemy; print('SQLAlchemy:', sqlalchemy.__version__)"

echo ""
echo "========================================"
echo "   Installation terminée avec succès!"
echo "========================================"
echo ""
echo "Pour démarrer l'application:"
echo "  1. Activez l'environnement: source .venv/bin/activate"
echo "  2. Lancez l'app: python main.py"
echo "  3. Ouvrez http://localhost:5000 dans votre navigateur"
echo ""
echo "N'oubliez pas de configurer le fichier .env avec vos paramètres!"
echo ""

# Rendre le script exécutable
chmod +x install-linux.sh 2>/dev/null || true