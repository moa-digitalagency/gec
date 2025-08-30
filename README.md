# 📮 GEC - Système de Gestion Électronique du Courrier

## 🌍 Language / Langue

### 📖 Documentation

#### 🇫🇷 Français
- [📚 Documentation Technique](docs/README_TECHNICAL_FR.md) - Architecture, déploiement, API
- [💼 Documentation Commerciale](docs/README_COMMERCIAL_FR.md) - Fonctionnalités, tarifs, témoignages

#### 🇬🇧 English
- [📚 Technical Documentation](docs/README_TECHNICAL_EN.md) - Architecture, deployment, API
- [💼 Commercial Documentation](docs/README_COMMERCIAL_EN.md) - Features, pricing, testimonials

---

## 🚀 Aperçu Général

**GEC** est un système complet de gestion électronique du courrier développé pour les administrations et secrétariats généraux en République Démocratique du Congo.

### ✨ Fonctionnalités Clés

- 📥 **Gestion Courrier Entrant/Sortant** avec pièces jointes obligatoires
- 🔍 **Recherche Avancée** dans tous les champs de métadonnées
- 🔐 **Sécurité Bancaire** avec chiffrement AES-256
- 👥 **Contrôle d'Accès Multi-niveaux** (Super Admin, Admin, Utilisateur)
- 📊 **Tableau de Bord Analytics** en temps réel
- 📱 **Design 100% Responsive** aux couleurs RDC
- 🌍 **Support Multi-langues** (Français/Anglais)
- 📄 **Génération PDF** pour documents officiels
- 📧 **Templates Email Configurables** avec test SMTP
- 💾 **Sauvegarde/Restauration** automatique

### 🛠️ Stack Technologique

**Backend**: Flask, PostgreSQL, SQLAlchemy, Chiffrement AES-256
**Frontend**: Tailwind CSS, DataTables, Font Awesome, Chart.js
**Sécurité**: bcrypt, cryptography, audit logging complet

---

## ⚡ Installation Multi-Plateforme

### 🪟 Windows (10/11/Server 2008+)
```powershell
# Installer Python 3.11
winget install --id Python.Python.3.11 -e

# Installer Git
winget install --id Git.Git -e

# Cloner le projet
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# Configurer l'environnement
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
python -m venv .venv
# Si erreur, essayez : py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Installer les dépendances
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

# Lancer l'application
python .\main.py
```

### 🍎 macOS (10.15+)
```bash
# Installer Homebrew si nécessaire
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Installer Python 3.11 et Git
brew install python@3.11 git

# Cloner le projet
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# Configurer l'environnement
python3.11 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

# Lancer l'application
python main.py
```

### 🐧 Linux (Ubuntu/Debian/CentOS/RHEL)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev git postgresql-client -y

# CentOS/RHEL/Fedora
sudo dnf install python3.11 python3.11-devel git postgresql -y
# ou pour les versions plus anciennes :
# sudo yum install python3.11 python3.11-devel git postgresql

# Cloner le projet
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# Configurer l'environnement
python3.11 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

# Lancer l'application
python main.py
```

### 🚀 Installation Automatique One-Click

Téléchargez et exécutez les scripts d'installation automatique selon votre système :

#### Windows 10/11
```batch
# Télécharger install-gec-windows.bat
# Clic droit → "Exécuter en tant qu'administrateur"
```

#### Windows Server 2008/2012/2016+
```batch
# Télécharger install-gec-windows-server.bat
# Clic droit → "Exécuter en tant qu'administrateur"
# Installation complète avec service Windows
```

#### macOS (10.15+)
```bash
# Télécharger install-gec-macos.sh
chmod +x install-gec-macos.sh
./install-gec-macos.sh
```

#### Linux (Toutes distributions)
```bash
# Installation directe depuis internet
curl -fsSL https://raw.githubusercontent.com/moa-digitalagency/gec/main/install-gec-linux.sh | bash

# Ou téléchargement puis exécution
chmod +x install-gec-linux.sh
./install-gec-linux.sh
```

📖 **Documentation d'installation complète** : [docs/INSTALLATION_INDEX.md](docs/INSTALLATION_INDEX.md)

### 🔧 Configuration Post-Installation

Créez un fichier `.env` pour les variables d'environnement :
```bash
DATABASE_URL=postgresql://user:password@localhost/gecmines
SESSION_SECRET=votre-clé-secrète-très-longue
GEC_MASTER_KEY=votre-clé-de-chiffrement-32-caractères
GEC_PASSWORD_SALT=votre-sel-de-mot-de-passe
```

---

## 📋 Dernières Mises à Jour (Août 2025)

✅ **Système de Templates Email**
- Templates multi-langues configurables (Français/Anglais)
- Variables dynamiques ({{numero_courrier}}, {{nom_utilisateur}}, etc.)
- Interface d'administration avec aperçu temps réel
- Test SMTP intégré dans les paramètres

✅ **Sécurité Avancée**
- Chiffrement AES-256-CBC pour toutes les données sensibles
- Hachage bcrypt renforcé avec salts personnalisés
- Protection contre les attaques par force brute
- Journalisation complète des événements de sécurité

✅ **Recherche Améliorée**
- Indexation complète des métadonnées (autres_informations, statut, fichier_nom)
- Filtre "SG en copie" pour courrier entrant uniquement
- Pièces jointes obligatoires pour tous types de courrier

✅ **Prêt pour Production**
- Nettoyage de tous les fichiers temporaires/test
- Optimisé pour déploiement externe
- Documentation complète en français et anglais

---

## 🎯 Design et Copyright

**© 2025 MOA Digital Agency LLC**

### 👨‍💻 Concepteur et Développeur
**AIsance KALONJI wa KALONJI**

### 📞 Contact MOA Digital Agency
- **📧 Email**: moa@myoneart.com
- **📧 Email alternatif**: moa.myoneart@gmail.com  
- **📱 Téléphone**: +212 699 14 000 1
- **📱 Téléphone RDC**: +243 86 049 33 45
- **🌐 Site web**: [myoneart.com](https://myoneart.com)

### 🏢 À Propos de MOA Digital Agency
MOA Digital Agency LLC est une agence de développement spécialisée dans la création de solutions digitales sur mesure pour les entreprises et institutions gouvernementales. Nous excellons dans le développement d'applications web robustes, sécurisées et évolutives.

---

## 📜 Licence

**© 2025 MOA Digital Agency LLC** | Tous droits réservés

Application conçue et développée par **AIsance KALONJI wa KALONJI** pour le Ministère des Mines de la République Démocratique du Congo.

---

<div align="center">

**Choisissez votre langue de documentation ci-dessus pour commencer !**

[🇫🇷 Documentation Française](docs/README_COMMERCIAL_FR.md) | [🇬🇧 English Documentation](docs/README_COMMERCIAL_EN.md)

---

*Développé avec 💖 et ☕ par **MOA Digital Agency LLC***

</div>