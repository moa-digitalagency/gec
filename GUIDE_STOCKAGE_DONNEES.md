# Guide de Stockage des Données - Système GEC

Ce guide explique où et comment sont stockées toutes les données du système GEC (Gestion Électronique du Courrier).

## 📊 Architecture de Stockage

### Vue d'Ensemble

```
projet-gec/
├── gec_mines.db              # Base de données SQLite (dev)
├── uploads/                  # Fichiers uploadés (pièces jointes)
├── exports/                  # Exports de courriers
├── backups/                  # Sauvegardes système
├── attached_assets/          # Assets attachés
├── static/                   # Ressources statiques (CSS, JS, images)
├── templates/                # Templates HTML
└── lang/                     # Fichiers de traduction
```

## 🗄️ Base de Données

### Emplacement

#### Mode Développement (SQLite)
- **Fichier** : `gec_mines.db` (racine du projet)
- **Type** : SQLite
- **Configuration** : `app.config["SQLALCHEMY_DATABASE_URI"]`

#### Mode Production (PostgreSQL)
- **Variable d'environnement** : `DATABASE_URL`
- **Format** : `postgresql://user:password@host:port/database`
- **Exemple** : `postgresql://gec_user:password@localhost:5432/gec_mines`

### Tables Principales

#### 1. **user** - Utilisateurs
Stocke les comptes utilisateurs et leurs informations
- **Données sensibles** :
  - `password_hash` : Mot de passe haché (bcrypt/argon2)
  - `email` : Email (peut être chiffré selon configuration)
- **Données** :
  - `username`, `nom_complet`, `role`, `langue`
  - `actif` : Statut actif/inactif
  - `departement_id` : Lien vers département

#### 2. **courrier** - Courriers Entrants
Stocke les courriers reçus avec **chiffrement des données sensibles**

**Données en clair** :
- `id`, `numero_accuse_reception`, `date_reception`
- `date_document`, `nature`, `priorite`
- `utilisateur_id`, `departement_id`, `statut_id`

**Données chiffrées** (champs `*_encrypted`) :
- `objet_encrypted` : Objet du courrier (AES-256-CBC)
- `expediteur_encrypted` : Expéditeur (AES-256-CBC)
- `destinataire_encrypted` : Destinataire (AES-256-CBC)
- `numero_reference_encrypted` : Numéro de référence (AES-256-CBC)

**Pièce jointe** :
- `fichier_nom` : Nom du fichier
- `fichier_chemin` : Chemin de stockage (ex: `uploads/123_document.pdf.encrypted`)
- `fichier_type` : Type MIME
- `fichier_checksum` : SHA-256 du fichier original
- `fichier_encrypted` : Boolean (True = fichier chiffré)

**Soft Delete** :
- `is_deleted` : Boolean
- `deleted_at` : Date de suppression
- `deleted_by_id` : Utilisateur ayant supprimé

#### 3. **courrier_sortant** - Courriers Sortants
Stocke les courriers envoyés (structure similaire à `courrier`)

#### 4. **courrier_forward** - Transmissions
Stocke les transmissions de courriers entre départements
- `courrier_id` : Courrier d'origine
- `from_departement_id` : Département expéditeur
- `to_departement_id` : Département destinataire
- `instructions_encrypted` : Instructions chiffrées
- `attached_file` : Pièce jointe de la transmission

#### 5. **departement** - Départements
Structure organisationnelle
- `nom`, `code`, `description`
- `chef_departement_id` : Responsable du département
- `actif` : Statut actif/inactif

#### 6. **statut_courrier** - Statuts
États possibles des courriers
- `nom`, `description`, `couleur`, `icone`
- `actif`, `ordre` : Affichage

#### 7. **role** & **role_permission** - Permissions
Système de gestion des droits
- Rôles : super_admin, admin, manager, user, lecteur
- Permissions granulaires par module

#### 8. **parametres_systeme** - Configuration
Paramètres globaux du système
- `nom_logiciel`, `logo_url`, `couleur_principale`
- `appellation_departement` : Nom personnalisé des entités
- `sendgrid_api_key_encrypted` : Clé SendGrid chiffrée
- `email_provider` : Fournisseur d'email

#### 9. **migration_log** - Historique des Migrations
Log automatique des migrations de base de données
- `migration_name`, `applied_at`, `status`
- `error_message` : Détails en cas d'erreur

#### 10. **system_health** - Santé Système
Métriques de performance et santé
- `metric_name`, `metric_value`, `recorded_at`

#### 11. **audit_log** - Journal d'Audit
Traçabilité de toutes les actions
- `user_id`, `action`, `details`
- `ip_address`, `timestamp`

## 📁 Fichiers Uploadés

### Emplacement : `uploads/`

#### Structure de Stockage

```
uploads/
├── 1_document.pdf.encrypted          # Courrier ID 1, chiffré
├── 2_facture.xlsx.encrypted          # Courrier ID 2, chiffré
├── 3_photo.jpg                       # Courrier ID 3, non chiffré (ancien)
└── forward_5_instructions.pdf.encrypted  # Transmission ID 5
```

#### Nomenclature des Fichiers

**Fichier principal de courrier** :
- Format : `{courrier_id}_{nom_original}.{extension}.encrypted`
- Exemple : `123_rapport_annuel.pdf.encrypted`

**Fichier de transmission** :
- Format : `forward_{forward_id}_{nom_original}.{extension}.encrypted`
- Exemple : `forward_45_instructions.pdf.encrypted`

#### Chiffrement des Fichiers

**Algorithme** : AES-256-CBC avec IV aléatoire

**Processus de chiffrement** :
1. Génération d'un IV (Initialization Vector) aléatoire de 16 bytes
2. Chiffrement du fichier avec AES-256-CBC
3. Stockage : `[IV (16 bytes)][Données chiffrées]`
4. Calcul du checksum SHA-256 du fichier original
5. Extension `.encrypted` ajoutée

**Processus de déchiffrement** :
1. Lecture de l'IV (premiers 16 bytes)
2. Lecture des données chiffrées (reste du fichier)
3. Déchiffrement avec AES-256-CBC et la clé maître
4. Vérification du checksum (optionnel)

**Clé de chiffrement** : `GEC_MASTER_KEY` (variable d'environnement)

#### Métadonnées dans la Base de Données

Pour chaque fichier, la table `courrier` stocke :
- `fichier_nom` : "rapport_annuel.pdf" (nom original)
- `fichier_chemin` : "uploads/123_rapport_annuel.pdf.encrypted"
- `fichier_type` : "application/pdf"
- `fichier_checksum` : "sha256:abcdef123456..." (fichier original)
- `fichier_encrypted` : True

## 💾 Exports de Courriers

### Emplacement : `exports/`

#### Structure d'un Export

```
exports/
└── export_courriers_20251015_143022.zip
    ├── courriers_data.json           # Données déchiffrées
    └── attachments/                  # Fichiers déchiffrés
        ├── 1_document.pdf
        ├── 2_facture.xlsx
        └── ...
```

#### Format JSON d'Export

```json
{
  "version": "1.0.0",
  "export_date": "2025-10-15T14:30:22Z",
  "total_courriers": 150,
  "courriers": [
    {
      "id": 1,
      "numero_accuse_reception": "GEC-2025-001",
      "objet": "Objet en clair (déchiffré)",
      "expediteur": "Expéditeur en clair",
      "destinataire": "Destinataire en clair",
      "numero_reference": "REF-2025-001",
      "fichier_nom": "document.pdf",
      "forwards": [...]
    }
  ],
  "attachments": [
    {
      "courrier_id": 1,
      "type": "main",
      "filename": "document.pdf",
      "path": "uploads/1_document.pdf.encrypted",
      "encrypted": true,
      "checksum": "sha256:..."
    }
  ]
}
```

**⚠️ IMPORTANT** : Les exports contiennent des **données déchiffrées** !
- Stockez-les de manière sécurisée
- Supprimez-les après utilisation
- Ne les partagez pas sans chiffrement

## 🔄 Sauvegardes Système

### Emplacement : `backups/`

#### Types de Sauvegardes

**1. Sauvegarde Complète**
```
backups/
└── backup_20251015_143022.zip
    ├── database_backup.sql           # Dump de la BD
    ├── settings.json                 # Paramètres système
    ├── users_backup.json             # Utilisateurs
    └── metadata.json                 # Métadonnées
```

**2. Sauvegarde de Sécurité (avant MAJ)**
- Contient uniquement les paramètres critiques
- Format JSON léger
- Restauration rapide

#### Contenu d'une Sauvegarde

**database_backup.sql** :
- Dump complet de la base de données
- **ATTENTION** : Contient des données **chiffrées**
- La clé `GEC_MASTER_KEY` est nécessaire pour les déchiffrer

**settings.json** :
```json
{
  "parametres_systeme": {
    "nom_logiciel": "GEC Mines",
    "logo_url": "...",
    "sendgrid_api_key_encrypted": "..."
  }
}
```

**users_backup.json** :
```json
{
  "users": [
    {
      "username": "sa.gec001",
      "email": "admin@mines.gov.cd",
      "role": "super_admin",
      "password_hash": "..."
    }
  ]
}
```

## 🔐 Variables d'Environnement et Secrets

### Emplacement

#### Replit
- **Secrets** : Stockés dans les Secrets Replit (chiffrés)
- Accessibles via `os.environ.get("NOM_VARIABLE")`

#### Local
- **Fichier** : `.env` (racine du projet)
- **⚠️ CRITIQUE** : Ne jamais commiter ce fichier !
- Ajouté au `.gitignore`

### Variables Critiques

#### 1. **GEC_MASTER_KEY** (CRITIQUE)
- **Usage** : Clé de chiffrement principale (AES-256)
- **Format** : Base64, 32+ caractères
- **Génération** : `python generate_keys.py`
- **Stockage** : Fichier `.env` ou Secrets Replit
- **⚠️ PERTE = DONNÉES IRRÉCUPÉRABLES**

#### 2. **GEC_PASSWORD_SALT** (CRITIQUE)
- **Usage** : Sel pour le hachage des mots de passe
- **Format** : Base64, 16+ caractères
- **Génération** : `python generate_keys.py`
- **⚠️ PERTE = IMPOSSIBLE DE SE CONNECTER**

#### 3. **SESSION_SECRET**
- **Usage** : Secret pour les sessions Flask
- **Format** : Chaîne aléatoire
- **Défaut** : "dev-secret-key-gec-mines" (à changer en prod)

#### 4. **DATABASE_URL**
- **Usage** : URL de connexion à la base de données
- **Format** : 
  - SQLite: `sqlite:///gec_mines.db`
  - PostgreSQL: `postgresql://user:pass@host:port/db`

#### 5. **ADMIN_PASSWORD**
- **Usage** : Mot de passe initial de l'admin
- **Défaut** : "TempPassword123!"
- **⚠️ À CHANGER IMMÉDIATEMENT**

### Stockage Sécurisé

```bash
# Sauvegarder les secrets
echo "GEC_MASTER_KEY=$GEC_MASTER_KEY" > .env.backup
echo "GEC_PASSWORD_SALT=$GEC_PASSWORD_SALT" >> .env.backup

# Chiffrer le backup (recommandé)
gpg --symmetric --cipher-algo AES256 .env.backup
rm .env.backup  # Supprimer la version non chiffrée

# Restaurer
gpg --decrypt .env.backup.gpg > .env.backup
source .env.backup
```

## 🌍 Fichiers de Traduction

### Emplacement : `lang/`

```
lang/
├── fr.json    # Français (langue par défaut)
└── en.json    # Anglais
```

**Format** :
```json
{
  "login": "Connexion",
  "dashboard": "Tableau de Bord",
  "courriers": "Courriers",
  "settings": "Paramètres"
}
```

**Changement de langue** :
- Par utilisateur : Stocké dans `user.langue`
- Appliqué via le context processor `inject_language_functions()`

## 📊 Taille et Capacité

### Estimations de Stockage

#### Base de Données
- **Courrier moyen** : ~2 KB (sans pièce jointe)
- **1000 courriers** : ~2 MB
- **10000 courriers** : ~20 MB
- **Index et métadonnées** : +30%

#### Fichiers Uploadés
- Dépend du type de fichier
- **PDF moyen** : 200-500 KB
- **Image moyenne** : 100-300 KB
- **Chiffrement** : +1-2% de taille (IV overhead)

#### Exemple pour 10000 Courriers
- Base de données : ~25 MB
- Fichiers (250 KB moy.) : ~2.5 GB
- **Total** : ~2.5 GB

### Limites

#### SQLite (Mode Développement)
- **Taille max** : 281 TB (théorique)
- **Recommandé** : < 100 GB
- **Performance optimale** : < 1 GB

#### PostgreSQL (Mode Production)
- **Taille max** : Illimitée (pratiquement)
- **Recommandé** : Dépend du serveur
- **Configuration** : `pool_recycle=300`, `pool_pre_ping=True`

## 🧹 Nettoyage et Maintenance

### Suppression Soft vs Hard

#### Soft Delete (Recommandé)
- `courrier.is_deleted = True`
- `courrier.deleted_at = now()`
- **Fichiers** : Conservés
- **Restauration** : Possible

#### Hard Delete (Permanent)
```python
# Supprimer le fichier physique
if courrier.fichier_chemin:
    os.remove(courrier.fichier_chemin)

# Supprimer de la BD
db.session.delete(courrier)
db.session.commit()
```

### Nettoyage des Fichiers Orphelins

```python
# Script de nettoyage (cleanup_database.py)
# Trouve les fichiers sans courrier associé
orphan_files = []
for filename in os.listdir('uploads'):
    courrier_id = int(filename.split('_')[0])
    if not Courrier.query.get(courrier_id):
        orphan_files.append(filename)

# Supprimer les orphelins
for filename in orphan_files:
    os.remove(os.path.join('uploads', filename))
```

### Archivage

**Courriers anciens** (> 1 an) :
1. Exporter vers ZIP
2. Soft delete dans la BD
3. Conserver l'export dans `archives/`

## 🔍 Debugging et Inspection

### Voir les Données Chiffrées

```python
from encryption_utils import decrypt_sensitive_data

# Déchiffrer un champ
courrier = Courrier.query.get(1)
objet_clair = decrypt_sensitive_data(courrier.objet_encrypted)
print(objet_clair)
```

### Vérifier l'Intégrité

```python
import hashlib

# Vérifier le checksum d'un fichier
with open(courrier.fichier_chemin, 'rb') as f:
    # Skip IV (16 bytes)
    iv = f.read(16)
    encrypted_data = f.read()
    
# Déchiffrer et calculer checksum
# Comparer avec courrier.fichier_checksum
```

### Logs de Stockage

```bash
# Activer les logs SQL
export SQLALCHEMY_ECHO=True
python main.py

# Vous verrez toutes les requêtes SQL
# INSERT, UPDATE, DELETE, SELECT
```

## ⚠️ Points Critiques de Sécurité

### ❌ NE JAMAIS

1. **Commiter les secrets** dans Git
   - `.env`, `.env.backup`, `GEC_MASTER_KEY`

2. **Partager les exports non chiffrés**
   - Contiennent des données sensibles en clair

3. **Perdre la clé GEC_MASTER_KEY**
   - Données chiffrées définitivement perdues

4. **Exposer le dossier `uploads/`** via HTTP
   - Contient des fichiers sensibles

5. **Stocker des mots de passe en clair**
   - Toujours utiliser `generate_password_hash()`

### ✅ TOUJOURS

1. **Sauvegarder régulièrement** :
   - Base de données (quotidien)
   - Variables d'environnement (après chaque changement)
   - Fichiers uploads (hebdomadaire)

2. **Chiffrer les données sensibles** :
   - Utiliser `encrypt_sensitive_data()` pour les nouveaux champs

3. **Valider les uploads** :
   - Type de fichier
   - Taille maximale
   - Scan antivirus (recommandé)

4. **Logger les accès** :
   - Audit trail dans `audit_log`
   - IP, utilisateur, action

## 📋 Checklist de Vérification

- [ ] `gec_mines.db` ou PostgreSQL accessible
- [ ] Dossier `uploads/` existe avec permissions correctes
- [ ] `GEC_MASTER_KEY` configurée et sauvegardée
- [ ] `GEC_PASSWORD_SALT` configurée et sauvegardée
- [ ] Sauvegardes automatiques configurées
- [ ] Espace disque suffisant (>5 GB libre recommandé)
- [ ] Accès aux logs pour debugging
- [ ] `.env` dans `.gitignore`
- [ ] Fichiers uploadés non accessibles via HTTP direct
