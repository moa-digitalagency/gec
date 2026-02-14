# Installation et Configuration - GEC

## Prérequis Système

### Logiciels Requis

| Logiciel | Version Minimum |
|----------|-----------------|
| Python | 3.11+ |
| PostgreSQL | 14+ |
| pip | 23+ |

### Dépendances Python

Le fichier `pyproject.toml` contient toutes les dépendances nécessaires :

```
flask>=3.0.0
flask-login>=0.6.0
flask-sqlalchemy>=3.1.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
gunicorn>=21.0.0
werkzeug>=3.0.0
bcrypt>=4.0.0
cryptography>=41.0.0
pycryptodome>=3.19.0
sendgrid>=6.0.0
reportlab>=4.0.0
xlsxwriter>=3.0.0
pandas>=2.0.0
pillow>=10.0.0
opencv-python>=4.0.0
pyyaml>=6.0.0
email-validator>=2.0.0
requests>=2.31.0
```

---

## Installation sur Replit

### Étapes

1. **Créer un nouveau Repl** Python

2. **Importer les fichiers** du projet

3. **Les dépendances s'installent automatiquement** via pyproject.toml

4. **Créer la base de données PostgreSQL** via l'outil Replit Database

5. **Configurer les variables d'environnement** (Secrets) :
   - `DATABASE_URL` : fourni automatiquement par Replit
   - `SESSION_SECRET` : fourni automatiquement par Replit
   - `GEC_MASTER_KEY` : à générer (voir section Clés)
   - `GEC_PASSWORD_SALT` : à générer (voir section Clés)

6. **Lancer l'application** : le workflow est configuré pour démarrer automatiquement

### Vérification

L'application est accessible sur `https://[nom-du-repl].[utilisateur].repl.co`

---

## Installation Locale

### Linux (Ubuntu/Debian)

```bash
# Installer Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# Installer PostgreSQL
sudo apt install postgresql postgresql-contrib

# Créer la base de données
sudo -u postgres createuser gec_user
sudo -u postgres createdb gec_db -O gec_user
sudo -u postgres psql -c "ALTER USER gec_user PASSWORD 'votre_mot_de_passe';"

# Cloner le projet
git clone [url_du_depot] gec
cd gec

# Créer l'environnement virtuel
python3.11 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
# ou
pip install .

# Configurer les variables d'environnement
export DATABASE_URL="postgresql://gec_user:votre_mot_de_passe@localhost:5432/gec_db"
export SESSION_SECRET="votre_secret_session_32_caracteres_minimum"
export GEC_MASTER_KEY="clé_générée_base64"
export GEC_PASSWORD_SALT="sel_généré_base64"

# Lancer l'application
gunicorn --bind 0.0.0.0:5000 main:app
```

### Windows

```powershell
# Installer Python 3.11 depuis python.org

# Installer PostgreSQL depuis postgresql.org

# Créer la base de données via pgAdmin ou psql

# Cloner le projet
git clone [url_du_depot] gec
cd gec

# Créer l'environnement virtuel
python -m venv venv
.\venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
$env:DATABASE_URL = "postgresql://gec_user:votre_mot_de_passe@localhost:5432/gec_db"
$env:SESSION_SECRET = "votre_secret_session_32_caracteres_minimum"
$env:GEC_MASTER_KEY = "clé_générée_base64"
$env:GEC_PASSWORD_SALT = "sel_généré_base64"

# Lancer l'application
python -m gunicorn --bind 0.0.0.0:5000 main:app
```

### macOS

```bash
# Installer Homebrew si nécessaire
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Installer Python et PostgreSQL
brew install python@3.11 postgresql@14

# Démarrer PostgreSQL
brew services start postgresql@14

# Créer la base de données
createuser gec_user
createdb gec_db -O gec_user
psql -c "ALTER USER gec_user PASSWORD 'votre_mot_de_passe';"

# Suite identique à Linux...
```

---

## Génération des Clés de Chiffrement

### Utilisation du Script

```bash
python generate_keys.py
```

Le script affiche les clés à configurer.

### Génération Manuelle

```bash
# Générer GEC_MASTER_KEY
python -c "import secrets, base64; print('GEC_MASTER_KEY=' + base64.b64encode(secrets.token_bytes(32)).decode())"

# Générer GEC_PASSWORD_SALT
python -c "import secrets, base64; print('GEC_PASSWORD_SALT=' + base64.b64encode(secrets.token_bytes(32)).decode())"
```

### Vérification des Clés

```bash
python show_env_keys.py
```

---

## Configuration des Variables d'Environnement

### Variables Obligatoires

| Variable | Description | Exemple |
|----------|-------------|---------|
| DATABASE_URL | URL de connexion PostgreSQL | postgresql://user:pass@host:5432/db |
| SESSION_SECRET | Secret pour les sessions Flask | chaîne aléatoire 32+ caractères |

### Variables Critiques (Production)

| Variable | Description |
|----------|-------------|
| GEC_MASTER_KEY | Clé de chiffrement AES-256 (Base64) |
| GEC_PASSWORD_SALT | Sel pour hachage mots de passe (Base64) |

### Variables Optionnelles

| Variable | Description | Défaut |
|----------|-------------|--------|
| ADMIN_PASSWORD | Mot de passe admin initial | TempPassword123! |
| SMTP_SERVER | Serveur SMTP | localhost |
| SMTP_PORT | Port SMTP | 587 |
| SMTP_EMAIL | Email expéditeur | noreply@gec.local |
| SMTP_PASSWORD | Mot de passe SMTP | (vide) |
| SMTP_USE_TLS | Activer TLS | True |

### Fichier .env (Développement Local)

```env
# Base de données
DATABASE_URL=postgresql://gec_user:password@localhost:5432/gec_db

# Sécurité
SESSION_SECRET=dev-secret-key-change-in-production-minimum-32-chars
GEC_MASTER_KEY=aB3dE6fG9hI0jK1lM2nO3pQ4rS5tU6vW7xY8zA9bC0d=
GEC_PASSWORD_SALT=zY9xW8vU7tS6rQ5pO4nM3lK2jI1hG0fE9dC8bA7aB6c=

# Admin
ADMIN_PASSWORD=MonMotDePasseSecurise123!

# Email (optionnel)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=notifications@example.com
SMTP_PASSWORD=mot_de_passe_application
SMTP_USE_TLS=True
```

---

## Configuration Email

### SendGrid (Recommandé)

1. Créer un compte sur sendgrid.com
2. Générer une clé API
3. Configurer dans l'interface GEC :
   - Paramètres → Configuration Email
   - Coller la clé API SendGrid
   - Sélectionner le fournisseur "SendGrid"

### SMTP Traditionnel

1. Configurer dans l'interface GEC :
   - Paramètres → Configuration Email
   - Renseigner serveur, port, identifiants
   - Sélectionner le fournisseur "SMTP"

### Test de Configuration

1. Aller dans Paramètres → Configuration Email
2. Saisir une adresse email de test
3. Cliquer sur "Tester la configuration"
4. Vérifier la réception de l'email de test

---

## Premier Démarrage

### Initialisation Automatique

Au premier lancement, l'application :

1. Crée les tables de la base de données
2. Exécute les migrations automatiques
3. Crée les départements par défaut
4. Crée les statuts par défaut
5. Crée les rôles et permissions par défaut
6. Crée les types de courrier sortant par défaut
7. Crée le compte super administrateur

### Première Connexion

1. Accéder à l'application
2. Se connecter avec :
   - Utilisateur : `sa.gec001`
   - Mot de passe : `TempPassword123!` (ou ADMIN_PASSWORD si configuré)
3. **Changer immédiatement le mot de passe**

### Configuration Initiale

1. Modifier les paramètres système (nom du logiciel, logo, etc.)
2. Créer les départements de votre organisation
3. Créer les comptes utilisateurs
4. Configurer les notifications email

---

## Mise à Jour

### Procédure

1. **Créer une sauvegarde** via l'interface (Gestion des Sauvegardes)

2. **Arrêter l'application**

3. **Mettre à jour les fichiers**
   ```bash
   git pull origin main
   ```

4. **Mettre à jour les dépendances**
   ```bash
   pip install -r requirements.txt --upgrade
   ```

5. **Redémarrer l'application**

Les migrations de base de données sont automatiques.

---

## Structure des Dossiers

Après installation, la structure doit être :

```
gec/
├── uploads/           # Fichiers uploadés (créé automatiquement)
├── exports/           # Fichiers d'export (créé automatiquement)
├── backups/           # Sauvegardes (créé automatiquement)
├── lang/              # Fichiers de traduction
├── static/            # Ressources statiques
├── templates/         # Templates HTML
├── docs/              # Documentation
├── *.py               # Code source Python
├── pyproject.toml     # Dépendances
└── .env               # Variables d'environnement (local uniquement)
```

### Permissions

```bash
# S'assurer que les dossiers sont accessibles en écriture
chmod 755 uploads exports backups
```

---

## Dépannage

### L'application ne démarre pas

**Vérifier** :
- Python 3.11+ installé
- Toutes les dépendances installées
- Variable DATABASE_URL correcte
- PostgreSQL en fonctionnement

### Erreur de connexion à la base de données

**Vérifier** :
- PostgreSQL démarré
- Utilisateur et mot de passe corrects
- Base de données créée
- Accès réseau autorisé

### Les clés de chiffrement ne fonctionnent pas

**Symptôme** : Messages CRITICAL au démarrage

**Solution** : Configurer GEC_MASTER_KEY et GEC_PASSWORD_SALT

### Les emails ne s'envoient pas

**Vérifier** :
- Configuration SendGrid/SMTP correcte
- Connexion internet active
- Adresse email expéditeur vérifiée (SendGrid)

### Page blanche ou erreur 500

**Vérifier** :
- Logs de l'application
- Configuration des templates
- Permissions sur les dossiers

---

## Support

Pour toute question :
1. Consulter la documentation dans /docs
2. Vérifier les logs de l'application
3. Contacter l'administrateur système
