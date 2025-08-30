#!/bin/bash
# =============================================================
# GEC Mines - Script d'installation automatique pour macOS
# =============================================================
# Copyright (c) 2025 MOA Digital Agency LLC
# Développé par AIsance KALONJI wa KALONJI
# Contact: moa@myoneart.com | +212 699 14 000 1
# =============================================================

set -e

echo ""
echo "========================================"
echo "   GEC Mines - Installation macOS"
echo "========================================"
echo ""

# Vérifier si Homebrew est installé
if ! command -v brew &> /dev/null; then
    echo "[AVERTISSEMENT] Homebrew n'est pas installé."
    read -p "Voulez-vous installer Homebrew maintenant? (y/n): " install_brew
    if [[ $install_brew == "y" || $install_brew == "Y" ]]; then
        echo "[INFO] Installation de Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo "[ERREUR] Homebrew est requis pour l'installation automatique."
        echo "Installez-le manuellement ou utilisez l'installation manuelle."
        exit 1
    fi
fi

# Vérifier et installer Python 3.11
if ! command -v python3.11 &> /dev/null; then
    echo "[INFO] Installation de Python 3.11..."
    brew install python@3.11
fi

# Vérifier et installer Git
if ! command -v git &> /dev/null; then
    echo "[INFO] Installation de Git..."
    brew install git
fi

echo "[INFO] Python 3.11 et Git détectés avec succès."
echo ""

# Créer l'environnement virtuel
echo "[1/5] Création de l'environnement virtuel..."
if [ -d ".venv" ]; then
    echo "L'environnement virtuel existe déjà."
else
    python3.11 -m venv .venv
fi

# Activer l'environnement virtuel
echo "[2/5] Activation de l'environnement virtuel..."
source .venv/bin/activate

# Mettre à jour pip
echo "[3/5] Mise à jour de pip..."
python -m pip install -U pip wheel

# Installer les dépendances
echo "[4/5] Installation des dépendances..."
pip install -r project-dependencies.txt

# Vérifier l'installation
echo "[5/5] Vérification de l'installation..."
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