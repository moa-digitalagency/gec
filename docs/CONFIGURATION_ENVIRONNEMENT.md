# Environment Variables Configuration / Configuration des Variables d'Environnement

## English Version

### Required Environment Variables

This application requires several environment variables to function properly. Create a `.env` file in the root directory with the following variables:

#### 1. Database Configuration
- **DATABASE_URL** (Required)
  - PostgreSQL database connection string
  - Format: `postgresql://username:password@host:port/database`
  - Example: `postgresql://user:pass@localhost:5432/gec_db`
  - Provided automatically by Replit

#### 2. Security & Encryption
- **SESSION_SECRET** (Required)
  - Flask session secret key for secure session management
  - Must be a long random string (32+ characters recommended)
  - Example: `your-super-secret-session-key-here-32chars-min`
  - Provided automatically by Replit

- **GEC_MASTER_KEY** (Critical - Required for Production)
  - Master encryption key for sensitive data (Base64 encoded)
  - Used to encrypt/decrypt sensitive information in the database
  - **IMPORTANT**: If not set, a new key is generated on each restart, making previous encrypted data unrecoverable
  - Generate with: `python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"`
  - Example: `aB3dE6fG9hI0jK1lM2nO3pQ4rS5tU6vW7xY8zA9bC0d=`

- **GEC_PASSWORD_SALT** (Critical - Required for Production)
  - Salt for password hashing (Base64 encoded)
  - **IMPORTANT**: If not set, a new salt is generated on each restart, making previous password hashes invalid
  - Generate with: `python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"`
  - Example: `zY9xW8vU7tS6rQ5pO4nM3lK2jI1hG0fE9dC8bA7aB6c=`

#### 3. Admin Access
- **ADMIN_PASSWORD** (Optional)
  - Default password for the super admin account (sa.gec001)
  - Default if not set: `TempPassword123!`
  - **Recommendation**: Set a strong password for production

#### 4. Email Configuration (Optional - for notifications)
- **SMTP_SERVER** (Optional)
  - SMTP server hostname
  - Default: `localhost`
  - Example: `smtp.gmail.com`

- **SMTP_PORT** (Optional)
  - SMTP server port
  - Default: `587`
  - Common values: `587` (TLS), `465` (SSL), `25` (unsecured)

- **SMTP_EMAIL** (Optional)
  - Email address used as sender
  - Default: `noreply@gec.local`
  - Example: `notifications@yourdomain.com`

- **SMTP_PASSWORD** (Optional)
  - Password for SMTP authentication
  - Required if your SMTP server requires authentication

- **SMTP_USE_TLS** (Optional)
  - Enable TLS encryption for SMTP
  - Default: `True`
  - Values: `True` or `False`

### .env File Template

```env
# Database (Provided by Replit)
DATABASE_URL=postgresql://user:password@host:port/database

# Security (Provided by Replit)
SESSION_SECRET=your-super-secret-session-key-here-minimum-32-characters

# Encryption Keys (CRITICAL - Generate once and keep secure)
GEC_MASTER_KEY=generate-with-python-command-base64-32-bytes
GEC_PASSWORD_SALT=generate-with-python-command-base64-32-bytes

# Admin Access (Optional)
ADMIN_PASSWORD=YourSecurePassword123!

# Email Configuration (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=notifications@yourdomain.com
SMTP_PASSWORD=your-smtp-password
SMTP_USE_TLS=True
```

### Security Best Practices

1. **Never commit `.env` file to version control** - Add it to `.gitignore`
2. **Backup encryption keys securely** - Store `GEC_MASTER_KEY` and `GEC_PASSWORD_SALT` in a secure location
3. **Rotate keys periodically** - Change passwords and keys regularly
4. **Use environment-specific values** - Different keys for development, staging, and production
5. **Restrict access** - Limit who can view production environment variables

### Generating Encryption Keys

Run these commands to generate secure encryption keys:

```bash
# Generate GEC_MASTER_KEY
python -c "import secrets, base64; print('GEC_MASTER_KEY=' + base64.b64encode(secrets.token_bytes(32)).decode())"

# Generate GEC_PASSWORD_SALT
python -c "import secrets, base64; print('GEC_PASSWORD_SALT=' + base64.b64encode(secrets.token_bytes(32)).decode())"
```

---

## Version Française

### Variables d'Environnement Requises

Cette application nécessite plusieurs variables d'environnement pour fonctionner correctement. Créez un fichier `.env` dans le répertoire racine avec les variables suivantes :

#### 1. Configuration de la Base de Données
- **DATABASE_URL** (Requis)
  - Chaîne de connexion PostgreSQL
  - Format : `postgresql://utilisateur:motdepasse@hote:port/basededonnees`
  - Exemple : `postgresql://user:pass@localhost:5432/gec_db`
  - Fourni automatiquement par Replit

#### 2. Sécurité et Chiffrement
- **SESSION_SECRET** (Requis)
  - Clé secrète pour la gestion sécurisée des sessions Flask
  - Doit être une longue chaîne aléatoire (32+ caractères recommandés)
  - Exemple : `votre-cle-secrete-session-ici-minimum-32-caracteres`
  - Fourni automatiquement par Replit

- **GEC_MASTER_KEY** (Critique - Requis pour la Production)
  - Clé maître de chiffrement pour les données sensibles (encodée en Base64)
  - Utilisée pour chiffrer/déchiffrer les informations sensibles dans la base de données
  - **IMPORTANT** : Si non définie, une nouvelle clé est générée à chaque redémarrage, rendant les données précédemment chiffrées irrécupérables
  - Générer avec : `python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"`
  - Exemple : `aB3dE6fG9hI0jK1lM2nO3pQ4rS5tU6vW7xY8zA9bC0d=`

- **GEC_PASSWORD_SALT** (Critique - Requis pour la Production)
  - Sel pour le hachage des mots de passe (encodé en Base64)
  - **IMPORTANT** : Si non défini, un nouveau sel est généré à chaque redémarrage, rendant les anciens hachages de mots de passe invalides
  - Générer avec : `python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"`
  - Exemple : `zY9xW8vU7tS6rQ5pO4nM3lK2jI1hG0fE9dC8bA7aB6c=`

#### 3. Accès Administrateur
- **ADMIN_PASSWORD** (Optionnel)
  - Mot de passe par défaut pour le compte super administrateur (sa.gec001)
  - Par défaut si non défini : `TempPassword123!`
  - **Recommandation** : Définir un mot de passe fort pour la production

#### 4. Configuration Email (Optionnel - pour les notifications)
- **SMTP_SERVER** (Optionnel)
  - Nom d'hôte du serveur SMTP
  - Par défaut : `localhost`
  - Exemple : `smtp.gmail.com`

- **SMTP_PORT** (Optionnel)
  - Port du serveur SMTP
  - Par défaut : `587`
  - Valeurs courantes : `587` (TLS), `465` (SSL), `25` (non sécurisé)

- **SMTP_EMAIL** (Optionnel)
  - Adresse email utilisée comme expéditeur
  - Par défaut : `noreply@gec.local`
  - Exemple : `notifications@votredomaine.com`

- **SMTP_PASSWORD** (Optionnel)
  - Mot de passe pour l'authentification SMTP
  - Requis si votre serveur SMTP nécessite une authentification

- **SMTP_USE_TLS** (Optionnel)
  - Activer le chiffrement TLS pour SMTP
  - Par défaut : `True`
  - Valeurs : `True` ou `False`

### Modèle de Fichier .env

```env
# Base de données (Fourni par Replit)
DATABASE_URL=postgresql://utilisateur:motdepasse@hote:port/basededonnees

# Sécurité (Fourni par Replit)
SESSION_SECRET=votre-cle-secrete-session-ici-minimum-32-caracteres

# Clés de Chiffrement (CRITIQUE - Générer une fois et conserver en sécurité)
GEC_MASTER_KEY=generer-avec-commande-python-base64-32-octets
GEC_PASSWORD_SALT=generer-avec-commande-python-base64-32-octets

# Accès Administrateur (Optionnel)
ADMIN_PASSWORD=VotreMotDePasseSecurise123!

# Configuration Email (Optionnel)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=notifications@votredomaine.com
SMTP_PASSWORD=votre-mot-de-passe-smtp
SMTP_USE_TLS=True
```

### Bonnes Pratiques de Sécurité

1. **Ne jamais commiter le fichier `.env` dans le contrôle de version** - Ajoutez-le à `.gitignore`
2. **Sauvegarder les clés de chiffrement en sécurité** - Stockez `GEC_MASTER_KEY` et `GEC_PASSWORD_SALT` dans un endroit sécurisé
3. **Rotation périodique des clés** - Changez régulièrement les mots de passe et les clés
4. **Utiliser des valeurs spécifiques à l'environnement** - Clés différentes pour développement, staging et production
5. **Restreindre l'accès** - Limiter qui peut voir les variables d'environnement de production

### Génération des Clés de Chiffrement

Exécutez ces commandes pour générer des clés de chiffrement sécurisées :

```bash
# Générer GEC_MASTER_KEY
python -c "import secrets, base64; print('GEC_MASTER_KEY=' + base64.b64encode(secrets.token_bytes(32)).decode())"

# Générer GEC_PASSWORD_SALT
python -c "import secrets, base64; print('GEC_PASSWORD_SALT=' + base64.b64encode(secrets.token_bytes(32)).decode())"
```

---

## Quick Setup / Configuration Rapide

1. Copy the .env template above / Copiez le modèle .env ci-dessus
2. Generate encryption keys using the Python commands / Générez les clés de chiffrement avec les commandes Python
3. Fill in your SMTP details if you want email notifications / Remplissez vos détails SMTP si vous voulez les notifications email
4. Save as `.env` in the root directory / Enregistrez comme `.env` dans le répertoire racine
5. Restart the application / Redémarrez l'application

## Support

For questions or issues related to environment configuration, please contact your DevOps team.

Pour toute question ou problème lié à la configuration de l'environnement, veuillez contacter votre équipe DevOps.
