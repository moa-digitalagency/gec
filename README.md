# GEC - Système de Gestion Électronique du Courrier

## Aperçu

GEC (Gestion Électronique du Courrier) est une application web Flask complète pour la gestion numérique de la correspondance. Développée spécialement pour les administrations gouvernementales et entreprises de la République Démocratique du Congo, elle offre une solution sécurisée, évolutive et auditable pour l'enregistrement, le suivi et la gestion des courriers avec fichiers joints.

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
- **Rate limiting** et monitoring des tentatives malveillantes

### 👥 Gestion des Utilisateurs et Rôles
- **Système de rôles à trois niveaux** : Super Admin, Admin, Utilisateur
- **Permissions granulaires** configurables par fonctionnalité
- **Contrôle d'accès basé sur les rôles** (RBAC)
- **Gestion des départements** et affectations hiérarchiques
- **Profils utilisateur complets** avec informations de contact
- **Affichage de la fonction** dans le tableau de bord utilisateur
- **Gestion des photos de profil** avec prévisualisation sécurisée
- **Encryption des données sensibles** (téléphone, adresse, fonction)

### 📧 Gestion du Courrier
- **Enregistrement de courriers** entrants et sortants
- **Fichiers joints obligatoires** pour tous les types de courrier
- **Support multi-format** : PDF, images, documents Office
- **Numérotation automatique** avec accusés de réception
- **Statuts configurables** : En attente, En cours, Traité, Archivé
- **Recherche avancée** avec filtres multiples et performants
- **Types de courriers sortants** personnalisables
- **Gestion des expéditeurs/destinataires** avec historique
- **Import/Export** de données en masse
- **Archivage automatique** avec rétention configurable

### 🔄 Transmission et Suivi
- **Transmission de courriers** entre utilisateurs et départements
- **Pièces jointes lors de la transmission** avec validation
- **Notifications automatiques** de transmission multicanal
- **Historique complet des transmissions** avec traçabilité
- **Messages personnalisés** lors des transmissions
- **Marquage de lecture** automatique et manuel
- **Suivi en temps réel** du statut et des interactions
- **Workflow de validation** configurable par type de courrier

### 💬 Système de Commentaires et Annotations
- **Commentaires riches** avec support formatting
- **Annotations et instructions** détaillées sur les courriers
- **Mentions utilisateurs** avec notifications automatiques
- **Threading des discussions** par courrier
- **Historique complet** des interactions avec timestamps
- **Modération des commentaires** selon les rôles
- **Export des discussions** en PDF pour archivage

### 🔔 Notifications
- **Notifications in-app** en temps réel avec badges
- **Notifications email** configurables (SendGrid + SMTP)
- **Templates d'email** personnalisables par type d'événement
- **Ciblage intelligent** : créateur + dernière personne ayant reçu le courrier
- **Notifications push** pour événements critiques
- **Centre de notifications** avec historique complet
- **Préférences utilisateur** pour personnaliser les notifications

### 📊 Tableaux de Bord et Rapports
- **Tableau de bord analytique** avec métriques temps réel
- **Affichage de la fonction utilisateur** sous le nom complet
- **Graphiques interactifs** dynamiques (Chart.js)
- **KPI personnalisés** par rôle et département
- **Export PDF et Excel** des rapports avec mise en forme
- **Statistiques avancées** par période, utilisateur, département
- **Tableaux de performance** avec tendances
- **Dashboard administrateur** avec vue globale système

### 📄 Génération de Documents
- **Export PDF professionnel** avec en-têtes personnalisés
- **Bordereaux d'enregistrement** automatiques avec QR codes
- **Listes de courriers** formatées avec filtres appliqués
- **Rapports périodiques** automatisés
- **Templates personnalisables** par organisation
- **Logos et signatures** dynamiques selon le contexte
- **Génération batch** pour traitement en masse
- **Intégration ReportLab** pour layouts complexes

### 💾 Système de Sauvegarde et Restauration
- **Sauvegarde complète automatique** incluant :
  - Base de données PostgreSQL complète
  - Tous les fichiers téléchargés et pièces jointes
  - Fichiers de transmission (`forward_attachments`)
  - Templates et configurations système
  - Fichiers de traduction et langues
  - Variables d'environnement documentées
- **Validation d'intégrité** des sauvegardes avec checksums
- **Restauration cross-platform** compatible tous environnements
- **Mises à jour sécurisées** avec sauvegarde automatique pré-update
- **Protection des paramètres** lors des mises à jour
- **Interface de gestion** avec validation en un clic
- **Manifestes de sauvegarde** avec instructions intégrées
- **Rollback système** avec checkpoints automatiques

### ⚙️ Configuration Système
- **Paramètres système** entièrement configurables via interface
- **Logos personnalisables** (en-tête et signature) avec prévisualisation
- **Nomenclature organisationnelle** dynamique et adaptable
- **Formats de numérotation** personnalisables par type
- **Configuration email** flexible (SMTP/SendGrid)
- **Gestion des statuts** et types de courriers personnalisés
- **Paramètres de sécurité** configurables (timeouts, tentatives)
- **Maintenance système** avec outils intégrés
- **Variables d'environnement** documentées automatiquement

### 🌍 Système Multi-langue Avancé
- **Support natif de 10+ langues** : Français, Anglais, Espagnol, Allemand, Italien, Portugais, Arabe, Chinois, Japonais, Russe
- **Détection automatique** des langues disponibles avec fallback intelligent
- **Interface d'administration complète** pour la gestion des langues
- **Activation/désactivation** granulaire des langues individuelles
- **Upload et téléchargement** sécurisé des fichiers de traduction
- **Validation automatique** des fichiers JSON de traduction
- **Persistance multi-niveau** (session + cookie + base de données)
- **Plus de 600 clés de traduction** par langue avec contexte
- **API de traduction** pour extensions futures

#### 🎛️ Gestion des Langues (Super Admin)
- **Interface dédiée** accessible via `/manage_languages`
- **Toggle switches** pour activation/désactivation instantanée
- **Upload sécurisé** de nouveaux fichiers JSON de traduction
- **Téléchargement** des fichiers existants pour modification
- **Protection automatique** du français (langue de référence)
- **Validation syntaxique** et sémantique des traductions
- **Logs d'audit complets** pour toutes les actions linguistiques
- **Prévisualisation** des changements avant application

### 🔧 Gestion des Mises à Jour
- **Mises à jour en ligne** via Git avec sauvegarde automatique
- **Mises à jour hors ligne** via fichiers ZIP sécurisés
- **Validation pré-déploiement** avec tests automatiques
- **Préservation totale** des données et configurations utilisateur
- **Rollback automatique** en cas d'échec de mise à jour
- **Migration automatique** de base de données
- **Détection et ajout** automatique de nouvelles colonnes
- **Interface de gestion** avec contrôles de sécurité

### 📈 Performance et Monitoring
- **Caching intelligent** multi-niveau pour optimisation
- **Monitoring des performances** en temps réel
- **Optimisation des requêtes** SQL avec indexation automatique
- **Monitoring système** avec alertes configurables
- **Logs structurés** avec rotation automatique
- **Métriques de santé** système et application
- **Profiling des requêtes** lentes avec recommandations
- **Optimisation automatique** des images et documents

## Technologies Utilisées

### Backend
- **Flask** (Framework web Python) avec extensions complètes
- **SQLAlchemy** avec Flask-SQLAlchemy (ORM avancé)
- **PostgreSQL** (Base de données principale) avec fallback SQLite
- **ReportLab** (Génération PDF professionnelle)
- **bcrypt + cryptography** (Sécurité de niveau entreprise)
- **SendGrid** (Service email professionnel)
- **Gunicorn** (Serveur WSGI de production)

### Frontend
- **Jinja2** (Moteur de templates avec extensions)
- **Tailwind CSS** (Framework CSS moderne et responsive)
- **Font Awesome** (Icônes professionnelles)
- **DataTables** (Tableaux interactifs avancés)
- **Chart.js** (Graphiques dynamiques)
- **jQuery** (Interactions JavaScript optimisées)
- **Select2** (Sélecteurs améliorés)

### Sécurité
- **AES-256-CBC** pour le chiffrement symétrique
- **RSA** pour l'échange de clés sécurisé
- **bcrypt** pour le hachage des mots de passe
- **Protection CSRF** et en-têtes de sécurité
- **Validation et sanitisation** complète des entrées
- **Audit logging** avec traçabilité complète
- **Rate limiting** configurable par endpoint

### Stockage et Données
- **PostgreSQL** pour données relationnelles complexes
- **Système de fichiers local** avec organisation hiérarchique
- **Support multi-format** : PDF, images, documents
- **Compression automatique** des archives
- **Indexation full-text** pour recherche performante

## Design et UX

### Thème Visuel
- **Couleurs officielles RDC** : Bleu (#003087), Jaune (#FFD700), Rouge (#CE1126), Vert (#009639)
- **Design responsive** adaptatif pour tous écrans
- **Interface intuitive** avec UX optimisée
- **Menu hamburger universel** pour navigation mobile
- **Thème sombre/clair** selon préférences utilisateur

### Ergonomie
- **Navigation intuitive** avec breadcrumbs
- **Recherche globale** accessible partout
- **Raccourcis clavier** pour actions fréquentes
- **Préservation du contexte** entre sessions
- **Interface accessible** (WCAG 2.1 compatible)
- **Feedback visuel** immédiat pour toutes actions

## Installation et Déploiement

### Prérequis
- Python 3.11+ (recommandé)
- Git pour versioning et mises à jour
- PostgreSQL (optionnel, SQLite par défaut)
- 4GB RAM minimum (8GB recommandé)
- 10GB espace disque pour données

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

**📄 Documentation complète disponible dans [README-ENV.md](README-ENV.md)**

Le système nécessite plusieurs variables d'environnement pour fonctionner correctement. Pour une configuration détaillée en français et anglais, consultez le fichier [README-ENV.md](README-ENV.md).

#### Configuration Rapide

1. **Copiez le fichier template** : `.env.example` → `.env`
2. **Générez les clés de chiffrement** : `python generate_keys.py`
3. **Remplissez vos valeurs** dans le fichier `.env`

#### Variables Critiques (Production)

```bash
# Base de données (Fourni automatiquement sur Replit)
DATABASE_URL=postgresql://user:password@host:port/database

# Sécurité (Fourni automatiquement sur Replit)
SESSION_SECRET=your-secret-key-here

# Clés de chiffrement (CRITIQUE - À générer avec generate_keys.py)
GEC_MASTER_KEY=votre-cle-master-base64
GEC_PASSWORD_SALT=votre-sel-base64

# Email (Optionnel)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=notifications@votredomaine.com
SMTP_PASSWORD=votre-mot-de-passe-smtp
SMTP_USE_TLS=True
```

**⚠️ Important** : Les variables `GEC_MASTER_KEY` et `GEC_PASSWORD_SALT` sont **critiques**. Sans elles, les données chiffrées seront perdues à chaque redémarrage. Utilisez `python generate_keys.py` pour les générer en toute sécurité.

### Déploiement Production

#### Avec Gunicorn (Linux/macOS)
```bash
# Installer Gunicorn
pip install gunicorn

# Lancer en production
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 main:app
```

#### Avec Waitress (Windows)
```powershell
# Installer Waitress
pip install waitress

# Lancer en production
waitress-serve --host=0.0.0.0 --port=5000 main:app
```

#### Configuration Docker (Optionnelle)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
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

**Erreur base de données** :
```bash
# Vérifier la connectivité PostgreSQL
psql $DATABASE_URL -c "SELECT 1"

# Réinitialiser la base si nécessaire
python -c "from app import db; db.create_all()"
```

## 🔧 Outils de Maintenance

### Script de Nettoyage de Base de Données

Le système inclut un utilitaire de nettoyage complet (`cleanup_database.py`) pour la maintenance et les déploiements initiaux.

#### 📋 Fonctionnalités
- **Suppression sélective** : Retire toutes les données opérationnelles tout en préservant la configuration système
- **Préservation du super admin** : Garde intact l'utilisateur super admin (sa.gec001)
- **Sécurité transactionnelle** : Toutes les opérations sont protégées avec rollback automatique en cas d'erreur
- **Confirmation obligatoire** : Demande une confirmation explicite ("OUI") avant l'exécution
- **Rapports statistiques** : Affiche les statistiques avant/après nettoyage

#### 🗑️ Données Supprimées
- ✅ Tous les courriers (entrants et sortants)
- ✅ Tous les commentaires et transferts
- ✅ Toutes les notifications
- ✅ Tous les logs d'activité
- ✅ Toutes les IP bloquées
- ✅ Tous les comptes utilisateurs (sauf super admin)
- ✅ Les affectations de chefs de département

#### 💾 Données Conservées
- ✓ Compte super administrateur
- ✓ Définitions des départements
- ✓ Rôles et permissions
- ✓ Statuts de courrier
- ✓ Types de courrier sortant
- ✓ Paramètres système
- ✓ Modèles d'email
- ✓ Fichiers de traduction

#### 🚀 Utilisation du Script

```bash
# Se positionner dans le répertoire du projet
cd /chemin/vers/votre/projet-gec

# Exécuter le script de nettoyage
python cleanup_database.py

# Le script va :
# 1. Afficher les statistiques actuelles
# 2. Demander confirmation (taper "OUI")
# 3. Exécuter les opérations de nettoyage
# 4. Afficher le résumé final
```

#### 💡 Cas d'Usage Idéaux
- **Environnements de démonstration** : Préparation d'instances de démo propres
- **Instances de test** : Réinitialisation après tests
- **Déploiement initial** : Configuration d'environnements de production vierges
- **Migration système** : Nettoyage après migration de données
- **Formation** : Préparation d'environnements de formation

#### ⚠️ Important
- Le script requiert une confirmation explicite avant l'exécution
- **Créez une sauvegarde** avant d'utiliser ce script en production
- Le super admin par défaut est **sa.gec001** (configurable dans `app.py`)
- Toutes les opérations sont effectuées dans une transaction unique
- En cas d'erreur, aucune modification n'est appliquée (rollback automatique)

#### 📊 Exemple de Sortie

```
╔══════════════════════════════════════════════════════════╗
║          SCRIPT DE NETTOYAGE BASE DE DONNÉES GEC        ║
╚══════════════════════════════════════════════════════════╝

📊 Statistiques AVANT nettoyage:
Utilisateurs: 15
Courriers: 342
Commentaires: 89
Notifications: 127
Transferts: 56
Logs d'activité: 1250
Départements: 5
IP bloquées: 3

⚠️  ATTENTION: Cette opération va supprimer toutes les données
   sauf l'utilisateur super admin et les configurations système.

Tapez 'OUI' en majuscules pour confirmer: OUI

🔄 Démarrage du nettoyage...

✅ NETTOYAGE TERMINÉ AVEC SUCCÈS!

📊 Statistiques APRÈS nettoyage:
Utilisateurs: 1
Courriers: 0
Commentaires: 0
Notifications: 0
Transferts: 0
Logs d'activité: 0
Départements: 5
IP bloquées: 0
```

### Script de Vérification des Variables d'Environnement / Environment Variables Check Script

Le système inclut un utilitaire pratique (`show_env_keys.py`) pour vérifier et afficher les variables d'environnement configurées.

#### 📋 Fonctionnalités / Features
- **Affichage sécurisé** : Les valeurs sensibles sont automatiquement masquées partiellement
- **Vérification complète** : Affiche toutes les variables d'environnement GEC requises
- **Détection des valeurs manquantes** : Identifie les variables critiques non configurées
- **Mode export** : Option pour afficher les valeurs complètes (à utiliser avec précaution)
- **Support bilingue** : Affichage en français et anglais

#### 🔑 Variables Vérifiées / Checked Variables
- **DATABASE_URL** : URL de connexion PostgreSQL / PostgreSQL connection URL
- **SESSION_SECRET** : Clé secrète Flask / Flask session secret
- **GEC_MASTER_KEY** : Clé maître de chiffrement / Master encryption key ⚠️ CRITIQUE
- **GEC_PASSWORD_SALT** : Sel pour mots de passe / Password salt ⚠️ CRITIQUE
- **ADMIN_PASSWORD** : Mot de passe admin par défaut / Default admin password
- **SMTP_SERVER** : Serveur SMTP / SMTP server
- **SMTP_PORT** : Port SMTP / SMTP port
- **SMTP_EMAIL** : Email expéditeur / Sender email
- **SMTP_PASSWORD** : Mot de passe SMTP / SMTP password
- **SMTP_USE_TLS** : Utiliser TLS / Use TLS
- **SENDGRID_API_KEY** : Clé API SendGrid / SendGrid API key

#### 🚀 Utilisation du Script / How to Use

##### Mode Standard (Valeurs Masquées) / Standard Mode (Masked Values)
```bash
# Se positionner dans le répertoire du projet
cd /chemin/vers/votre/projet-gec

# Exécuter le script
python show_env_keys.py

# Le script va afficher :
# - Liste des variables configurées avec valeurs masquées
# - Liste des variables manquantes
# - Résumé des variables critiques
# - Suggestions de configuration
```

##### Mode Export (Valeurs Complètes) / Export Mode (Full Values)
```bash
# ⚠️ ATTENTION : Utilisez ce mode uniquement dans un environnement sécurisé
# ⚠️ WARNING: Use this mode only in a secure environment

python show_env_keys.py --export
# OU / OR
python show_env_keys.py --full

# Ce mode affiche les valeurs complètes non masquées
# This mode displays complete unmasked values
```

#### 📊 Exemple de Sortie / Sample Output

**Mode Standard :**
```
================================================================================
VARIABLES D'ENVIRONNEMENT GEC
GEC ENVIRONMENT VARIABLES
================================================================================

📋 VARIABLES CONFIGURÉES / CONFIGURED VARIABLES:
--------------------------------------------------------------------------------

✅ DATABASE_URL            = post************************************3b7a
   (URL de connexion PostgreSQL / PostgreSQL connection URL)

✅ SESSION_SECRET          = supe************************************ret1
   (Clé secrète Flask / Flask session secret)

✅ GEC_MASTER_KEY          = aB3d************************************C0d=
   (Clé maître de chiffrement / Master encryption key)

✅ GEC_PASSWORD_SALT       = zY9x************************************B6c=
   (Sel pour mots de passe / Password salt)

❌ SMTP_SERVER             = NON CONFIGURÉE / NOT SET
   (Serveur SMTP / SMTP server)

--------------------------------------------------------------------------------

📊 RÉSUMÉ / SUMMARY:
   Variables configurées / Configured: 4/10
   Variables manquantes / Missing: 6/10

💡 Pour voir les valeurs complètes (export) / To see full values (export):
   python show_env_keys.py --export

📝 SUGGESTIONS:
--------------------------------------------------------------------------------

1. Pour générer les clés de sécurité / To generate security keys:
   python generate_keys.py

2. Pour créer un fichier .env / To create a .env file:
   Copiez le modèle depuis README-ENV.md
   Copy the template from README-ENV.md

3. Sur Replit, utilisez l'onglet Secrets / On Replit, use the Secrets tab

================================================================================
```

#### 💡 Cas d'Usage Idéaux / Ideal Use Cases
- **Vérification de configuration** : S'assurer que toutes les variables sont configurées correctement
- **Débogage** : Identifier rapidement les variables manquantes ou mal configurées
- **Documentation** : Voir quelles variables sont utilisées par le système
- **Migration** : Vérifier la configuration avant/après migration
- **Audit de sécurité** : Vérifier que les variables critiques sont définies

#### ⚠️ Important / Important
- **Les valeurs sensibles sont masquées par défaut** pour la sécurité
- **N'utilisez le mode `--export` que dans un environnement sécurisé**
- **Ne partagez jamais les valeurs complètes publiquement**
- Les variables **GEC_MASTER_KEY** et **GEC_PASSWORD_SALT** sont **critiques** :
  - Sans elles, les données chiffrées seront perdues à chaque redémarrage
  - Utilisez `python generate_keys.py` pour les générer en toute sécurité
  - Conservez-les dans un endroit sécurisé (gestionnaire de secrets, coffre-fort)

#### 🔗 Voir Aussi / See Also
- **README-ENV.md** : Documentation complète des variables d'environnement
- **generate_keys.py** : Script pour générer les clés de sécurité
- **Onglet Secrets Replit** : Interface de gestion des secrets sur Replit

## Utilisation du Système

### Mise à Jour Système

#### Via Terminal (Recommandé)
```bash
# Se positionner dans le répertoire du projet
cd /chemin/vers/votre/projet-gec

# Créer une sauvegarde complète avant mise à jour
python -c "
from utils import create_pre_update_backup
backup_file = create_pre_update_backup()
print(f'Sauvegarde créée: {backup_file}')
"

# Effectuer la mise à jour Git
git fetch origin
git pull origin main

# Redémarrer le serveur
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

#### Via Interface Web
1. **Accès** : Menu → "Gestion des Sauvegardes"
2. **Sauvegarde** : Créer une sauvegarde avant mise à jour
3. **Mise à jour en ligne** : Via Git avec protection automatique
4. **Mise à jour hors ligne** : Upload d'un fichier ZIP

### Système Multi-langue

#### Pour les Utilisateurs
1. **Changement de langue** : Sélecteur dans la sidebar
2. **Persistance** : Choix sauvegardé automatiquement
3. **Langues disponibles** : Selon activation administrateur

#### Pour les Super Administrateurs
1. **Accès** : Menu → "Gérer les Langues" 🌐
2. **Activation/Désactivation** : Toggle switches
3. **Ajout de langue** : Upload fichier JSON
4. **Téléchargement** : Pour modifier traductions
5. **Suppression** : Protection français (référence)

### Structure des Fichiers de Traduction
```
lang/
├── fr.json          # Français (référence, protégé)
├── en.json          # Anglais
├── es.json          # Espagnol
├── de.json          # Allemand
├── it.json          # Italien
├── pt.json          # Portugais
├── ar.json          # Arabe
├── zh.json          # Chinois
├── ja.json          # Japonais
├── ru.json          # Russe
└── [code].json      # Autres langues...
```

### Gestion des Sauvegardes

#### Création de Sauvegarde
- **Interface** : Via page "Gestion des Sauvegardes"
- **Contenu** : Base de données + fichiers + configuration
- **Format** : Archive ZIP avec manifeste intégré
- **Validation** : Vérification intégrité automatique

#### Restauration Système
- **Compatible** : Restauration sur tout environnement
- **Sécurisé** : Sauvegarde avant restauration
- **Complet** : Tous les éléments système restaurés
- **Guidé** : Instructions intégrées dans chaque sauvegarde

## Support et Contribution

### 👨‍💻 Développeur et Concepteur
**AIsance KALONJI wa KALONJI**  
Expert en systèmes d'information et développement web

### 🏢 Copyright et Licence
**© 2025 MOA Digital Agency LLC** - Tous droits réservés

### 📞 Informations de Contact

**MOA Digital Agency**
- **📧 Email principal** : moa@myoneart.com
- **📧 Email alternatif** : moa.myoneart@gmail.com
- **📱 Téléphone Maroc** : +212 699 14 000 1
- **📱 Téléphone RDC** : +243 86 049 33 45
- **🌐 Site web** : [myoneart.com](https://myoneart.com)

### 🤝 Support Technique

Pour obtenir de l'aide technique, des modifications personnalisées ou des questions sur le déploiement :

1. **Support par email** : Contactez-nous à moa@myoneart.com
2. **Documentation complète** : Consultez ce README et les guides intégrés
3. **Personnalisation** : Services d'adaptation sur mesure disponibles
4. **Formation** : Sessions de formation pour administrateurs
5. **Maintenance** : Contrats de support et maintenance

### 💼 À Propos de MOA Digital Agency

MOA Digital Agency LLC est une agence de développement spécialisée dans la création de solutions digitales sur mesure pour les entreprises et institutions gouvernementales. Nous excellons dans le développement d'applications web robustes, sécurisées et évolutives.

**Domaines d'expertise** :
- **Applications web d'entreprise** avec architecture moderne
- **Systèmes de gestion administratifs** pour secteur public
- **Solutions de sécurité avancées** et chiffrement
- **Intégration et migration** de données complexes
- **Optimisation des performances** et scalabilité
- **Interface utilisateur** moderne et intuitive

**Certifications et Conformité** :
- Sécurité de niveau gouvernemental
- Conformité GDPR et protection données
- Standards d'accessibilité WCAG 2.1
- Architectures cloud-ready
- Support multi-plateforme

---

**GEC - Système de Gestion du Courrier**  
*Solution digitale complète pour l'administration moderne*

**Version** : 2.0.0 | **Dernière mise à jour** : 2025  
**Plateforme** : Web (Multi-navigateur) | **Licence** : Propriétaire