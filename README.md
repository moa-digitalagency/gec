# GEC - Système de Gestion Électronique du Courrier

**[English Version](README_EN.md)**

## Aperçu

GEC (Gestion Électronique du Courrier) est une application web Flask complète pour la gestion numérique de la correspondance. Développée spécialement pour les administrations et entreprises, elle offre une solution sécurisée et auditable pour l'enregistrement, le suivi et la gestion des courriers avec fichiers joints.

## Fonctionnalités Principales

### 🔐 Authentification et Sécurité
- **Authentification utilisateur sécurisée** avec Flask-Login
- **Chiffrement AES-256** pour toutes les données sensibles
- **Hachage bcrypt** avec sels personnalisés pour les mots de passe
- **Protection contre les attaques** : brute force, injection SQL, XSS
- **Blocage IP automatique** après tentatives de connexion échouées
- **Vérification d'intégrité des fichiers** avec checksums
- **Suppression sécurisée** des fichiers
- **Journalisation complète** de sécurité et d'audit

### 👥 Gestion des Utilisateurs et Rôles
- **Système de rôles à trois niveaux** : Super Admin, Admin, Utilisateur
- **Permissions granulaires** configurables
- **Contrôle d'accès basé sur les rôles** (RBAC)
- **Gestion des départements** et affectations
- **Profils utilisateur** avec informations de contact

### 📧 Gestion du Courrier
- **Enregistrement de courriers** entrants et sortants
- **Fichiers joints obligatoires** pour tous les types de courrier
- **Numérotation automatique** avec accusés de réception
- **Statuts configurables** : En attente, En cours, Traité, Archivé
- **Recherche avancée** avec filtres multiples
- **Types de courriers sortants** personnalisables
- **Gestion des expéditeurs/destinataires**

### 💬 Système de Commentaires et Annotations
- **Commentaires, annotations et instructions** sur les courriers
- **Notifications in-app** et par email
- **Ciblage intelligent** : créateur + dernière personne ayant reçu le courrier
- **Historique complet** des interactions

### 🔄 Transmission et Suivi
- **Transmission de courriers** entre utilisateurs
- **Notifications automatiques** de transmission
- **Historique des transmissions** avec dates et messages
- **Marquage de lecture** automatique
- **Suivi en temps réel** du statut

### 🔔 Notifications
- **Notifications in-app** en temps réel
- **Notifications email** configurables
- **Templates d'email** personnalisables
- **Intégration SendGrid** et SMTP
- **Notifications ciblées** selon les permissions

### 📊 Tableaux de Bord et Rapports
- **Tableau de bord analytique** avec statistiques temps réel
- **Graphiques interactifs** (Chart.js)
- **Export PDF et Excel** des rapports
- **Métriques de performance** et KPI
- **Statistiques par département** et utilisateur

### 📄 Génération de Documents
- **Export PDF** avec mise en page professionnelle
- **Bordereaux d'enregistrement** automatiques
- **Listes de courriers** formatées
- **En-têtes et pieds de page** personnalisables
- **Logos et signatures** dynamiques

### ⚙️ Configuration Système
- **Paramètres système** entièrement configurables
- **Logos personnalisables** (en-tête et signature)
- **Nomenclature organisationnelle** dynamique
- **Formats de numérotation** personnalisables
- **Configuration email** (SMTP/SendGrid)
- **Gestion des statuts** et types de courriers

### 🌍 Multi-langue
- **Support français et anglais**
- **Fichiers de traduction JSON**
- **Commutation de langue** en temps réel
- **Interface entièrement localisée**

### 🔒 Sauvegarde et Migration
- **Système de sauvegarde automatique**
- **Migration automatique** de base de données
- **Détection et ajout automatique** de nouvelles colonnes
- **Préservation des données** existantes
- **Système de rollback** avec checkpoints

## Technologies Utilisées

### Backend
- **Flask** (Framework web Python)
- **SQLAlchemy** avec Flask-SQLAlchemy (ORM)
- **PostgreSQL** (Base de données principale)
- **ReportLab** (Génération PDF)
- **bcrypt + cryptography** (Sécurité)
- **SendGrid** (Service email)

### Frontend
- **Jinja2** (Moteur de templates)
- **Tailwind CSS** (Framework CSS)
- **Font Awesome** (Icônes)
- **DataTables** (Tableaux interactifs)
- **Chart.js** (Graphiques)
- **jQuery** (Interactions JavaScript)

### Sécurité
- **AES-256-CBC** pour le chiffrement des données
- **bcrypt** pour le hachage des mots de passe
- **Protection CSRF** et en-têtes de sécurité
- **Validation et sanitisation** des entrées
- **Audit logging** complet

## Design et UX

- **Couleurs RDC** : Bleu (#003087), Jaune (#FFD700), Rouge (#CE1126), Vert (#009639)
- **Design responsive** adaptatif
- **Interface intuitive** et ergonomique
- **Menu hamburger universel**
- **Préservation du ratio d'aspect** pour les logos
- **Thème corporatif** cohérent

## Installation et Déploiement

### Prérequis
- Python 3.11+ (recommandé)
- Git
- PostgreSQL (optionnel, SQLite par défaut)

### 🪟 Installation Windows (10/11)

```powershell
# Installer Python 3.11
winget install --id Python.Python.3.11 -e

# Installer Git
winget install --id Git.Git -e

# Cloner le projet
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# Configurer PowerShell pour les scripts
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force

# Créer l'environnement virtuel
python -m venv .venv
# Si erreur, essayez : py -3.11 -m venv .venv

# Activer l'environnement
.\.venv\Scripts\Activate.ps1

# Installer les dépendances
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

# Lancer l'application
python .\main.py
```

### 🖥️ Installation Windows Server (2008/2012/2016/2019/2022)

```cmd
REM Télécharger Python depuis python.org si winget non disponible
REM Ou utiliser chocolatey : choco install python git

REM Cloner le projet
git clone https://github.com/moa-digitalagency/gec.git
cd gec

REM Créer l'environnement virtuel
python -m venv .venv

REM Activer l'environnement
.venv\Scripts\activate.bat

REM Installer les dépendances
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

REM Lancer l'application
python main.py
```

### 🍎 Installation macOS (10.15+)

```bash
# Installer Homebrew si nécessaire
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Installer Python 3.11 et Git
brew install python@3.11 git

# Cloner le projet
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# Créer l'environnement virtuel
python3.11 -m venv .venv

# Activer l'environnement
source .venv/bin/activate

# Installer les dépendances
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

# Lancer l'application
python main.py
```

### 🐧 Installation Linux

#### Ubuntu/Debian
```bash
# Mettre à jour le système
sudo apt update

# Installer Python 3.11 et dépendances
sudo apt install python3.11 python3.11-venv python3.11-dev git postgresql-client -y

# Cloner le projet
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# Créer l'environnement virtuel
python3.11 -m venv .venv

# Activer l'environnement
source .venv/bin/activate

# Installer les dépendances
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

# Lancer l'application
python main.py
```

#### CentOS/RHEL/Fedora
```bash
# Pour Fedora/CentOS Stream
sudo dnf install python3.11 python3.11-devel git postgresql -y

# Pour RHEL/CentOS 7-8 (versions plus anciennes)
sudo yum install python3.11 python3.11-devel git postgresql -y

# Cloner le projet
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# Créer l'environnement virtuel
python3.11 -m venv .venv

# Activer l'environnement
source .venv/bin/activate

# Installer les dépendances
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

# Lancer l'application
python main.py
```

#### Arch Linux
```bash
# Installer les dépendances
sudo pacman -S python git postgresql

# Cloner le projet
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# Créer l'environnement virtuel
python -m venv .venv

# Activer l'environnement
source .venv/bin/activate

# Installer les dépendances
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

# Lancer l'application
python main.py
```

### Variables d'Environnement

Créez un fichier `.env` dans le dossier du projet :

```bash
DATABASE_URL=postgresql://user:password@host:port/database
SESSION_SECRET=your_secret_key_here
SENDGRID_API_KEY=your_sendgrid_key (optionnel)
GEC_MASTER_KEY=your_encryption_key_32_chars
GEC_PASSWORD_SALT=your_password_salt
```

### Déploiement Production

#### Avec Gunicorn (Linux/macOS)
```bash
# Installer Gunicorn
pip install gunicorn

# Lancer en production
gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
```

#### Avec Waitress (Windows)
```powershell
# Installer Waitress
pip install waitress

# Lancer en production
waitress-serve --host=0.0.0.0 --port=5000 main:app
```

### 🔧 Dépannage

**Erreur Python non trouvé (Windows)** :
- Redémarrez votre terminal après installation
- Utilisez `py` au lieu de `python`
- Vérifiez PATH dans variables d'environnement

**Erreur permissions PowerShell** :
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
```

**Erreur pip outdated** :
```bash
python -m pip install --upgrade pip
```

**Port 5000 occupé** :
```bash
# Changer le port dans main.py ou utiliser
python main.py --port 8080
```

## Support et Contribution

Ce système est développé pour répondre aux besoins spécifiques des administrations et peut être adapté selon les exigences organisationnelles.

### 👨‍💻 Développeur et Concepteur
**AIsance KALONJI wa KALONJI**

### 🏢 Copyright et Licence
**© 2025 MOA Digital Agency LLC** - Tous droits réservés

### 📞 Informations de Contact

**MOA Digital Agency**
- **📧 Email** : moa@myoneart.com
- **📧 Email alternatif** : moa.myoneart@gmail.com
- **📱 Téléphone Maroc** : +212 699 14 000 1
- **📱 Téléphone RDC** : +243 86 049 33 45
- **🌐 Site web** : [myoneart.com](https://myoneart.com)

### 🤝 Support Technique

Pour obtenir de l'aide technique, des modifications personnalisées ou des questions sur le déploiement :

1. **Support par email** : Contactez-nous à moa@myoneart.com
2. **Documentation** : Consultez ce README pour les instructions d'installation
3. **Personnalisation** : MOA Digital Agency propose des services d'adaptation sur mesure

### 💼 À Propos de MOA Digital Agency

MOA Digital Agency LLC est une agence de développement spécialisée dans la création de solutions digitales sur mesure pour les entreprises et institutions gouvernementales. Nous excellons dans le développement d'applications web robustes, sécurisées et évolutives.

**Domaines d'expertise** :
- Applications web d'entreprise
- Systèmes de gestion administratifs
- Solutions de sécurité avancées
- Intégration et migration de données

---

**GEC - Système de Gestion du Courrier**  
*Solution digitale pour l'administration moderne*