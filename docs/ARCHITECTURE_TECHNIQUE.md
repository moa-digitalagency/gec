# Architecture Technique - GEC

## Vue d'Ensemble

Le GEC (Gestion Électronique du Courrier) est une application web développée en Python avec le framework Flask. L'application suit une architecture MVC (Modèle-Vue-Contrôleur) adaptée aux conventions Flask.

---

## Stack Technologique

### Backend

| Composant | Technologie | Version |
|-----------|-------------|---------|
| Langage | Python | 3.11 |
| Framework Web | Flask | 3.1.x |
| ORM | SQLAlchemy | 2.x |
| Base de données | PostgreSQL | 15+ |
| Serveur WSGI | Gunicorn | 23.x |
| Authentification | Flask-Login | 0.6.x |

### Frontend

| Composant | Technologie |
|-----------|-------------|
| CSS Framework | Tailwind CSS (CDN) |
| UI Components | Bootstrap 5 |
| Icons | Font Awesome |
| Tableaux | DataTables |
| Graphiques | Chart.js |
| Recadrage Images | Cropper.js |
| JavaScript | jQuery 3.7.1 |

### Sécurité

| Composant | Technologie |
|-----------|-------------|
| Chiffrement | AES-256-CBC |
| Hachage | bcrypt + PBKDF2 |
| Bibliothèques | cryptography, pycryptodome |

### Services Externes

| Service | Usage |
|---------|-------|
| SendGrid | Envoi d'emails |
| PostgreSQL (Neon) | Base de données cloud |

---

## Structure des Fichiers

```
gec/
├── app.py                    # Configuration Flask, initialisation app
├── main.py                   # Point d'entrée WSGI
├── models.py                 # Modèles SQLAlchemy (ORM)
├── views.py                  # Routes et contrôleurs
├── utils.py                  # Fonctions utilitaires générales
├── security_utils.py         # Sécurité, rate limiting, validation
├── encryption_utils.py       # Chiffrement AES, gestion des clés
├── email_utils.py            # Envoi emails (SendGrid/SMTP)
├── migration_utils.py        # Migrations automatiques BDD
├── export_import_utils.py    # Export/Import de courriers
├── performance_utils.py      # Cache, optimisations
├── lang_utils.py             # Gestion multilingue
├── generate_keys.py          # Génération clés de chiffrement
├── cleanup_database.py       # Nettoyage base de données
│
├── lang/                     # Fichiers de traduction
│   ├── fr.json
│   └── en.json
│
├── static/                   # Ressources statiques
│   ├── css/style.css
│   ├── js/app.js
│   ├── images/
│   └── vendor/               # Bibliothèques tierces
│       ├── bootstrap/
│       ├── chartjs/
│       ├── datatables/
│       ├── fontawesome/
│       ├── jquery/
│       └── tailwind/
│
├── templates/                # Templates Jinja2
│   ├── new_base.html         # Template de base
│   ├── login.html
│   ├── dashboard.html
│   ├── register_mail.html
│   └── ...
│
├── uploads/                  # Fichiers uploadés (courriers)
├── exports/                  # Fichiers d'export générés
├── backups/                  # Sauvegardes système
│
└── docs/                     # Documentation
```

---

## Modèle de Données

### Entités Principales

#### User (Utilisateur)
```
User
├── id (PK)
├── username (unique)
├── email (unique)
├── nom_complet
├── password_hash
├── role (super_admin, admin, user)
├── departement_id (FK)
├── langue
├── photo_profile
├── actif
├── matricule
├── fonction
└── *_encrypted (champs chiffrés)
```

#### Courrier
```
Courrier
├── id (PK)
├── numero_accuse_reception (unique)
├── numero_reference
├── objet
├── type_courrier (ENTRANT/SORTANT)
├── type_courrier_sortant_id (FK)
├── expediteur
├── destinataire
├── date_redaction
├── date_enregistrement
├── statut
├── fichier_nom
├── fichier_chemin
├── fichier_encrypted
├── secretaire_general_copie
├── is_deleted
├── utilisateur_id (FK)
└── *_encrypted (champs chiffrés)
```

#### Departement
```
Departement
├── id (PK)
├── nom (unique)
├── code (unique)
├── description
├── chef_departement_id (FK)
└── actif
```

#### CourrierForward (Transmission)
```
CourrierForward
├── id (PK)
├── courrier_id (FK)
├── from_department_id (FK)
├── to_department_id (FK)
├── forwarded_to_id (FK, User)
├── forward_date
├── comments
├── attached_file
├── is_read
└── read_date
```

#### Role et RolePermission
```
Role
├── id (PK)
├── nom
├── description
└── permissions (relation)

RolePermission
├── id (PK)
├── role_id (FK)
├── permission_code
└── description
```

### Relations

```
User ──────< Courrier
User ──────< LogActivite
User ──────< Notification
Departement ──────< User
Courrier ──────< CourrierForward
Courrier ──────< CourrierComment
Role ──────< RolePermission
TypeCourrierSortant ──────< Courrier
StatutCourrier ──────< Courrier
```

---

## Système d'Authentification

### Flux de Connexion

1. L'utilisateur soumet ses identifiants
2. Rate limiting vérifié (30 requêtes/15min)
3. Vérification si l'IP est bloquée
4. Recherche utilisateur en base
5. Vérification du hash du mot de passe (bcrypt + sel personnalisé)
6. Création de session Flask-Login
7. Journalisation de l'activité

### Gestion des Permissions

```python
# Permissions disponibles
- manage_users          # Gestion utilisateurs
- manage_roles          # Gestion rôles
- manage_departments    # Gestion départements
- manage_statuses       # Gestion statuts
- manage_system_settings # Paramètres système
- read_all_mail         # Lire tous les courriers
- read_department_mail  # Lire courriers département
- read_own_mail         # Lire ses propres courriers
- edit_all_mail         # Modifier tous les courriers
- edit_department_mail  # Modifier courriers département
- edit_own_mail         # Modifier ses propres courriers
- view_trash            # Voir corbeille
- restore_trash         # Restaurer de la corbeille
- permanent_delete      # Suppression définitive
```

### Hiérarchie des Rôles

1. **super_admin** : Toutes les permissions, accès total
2. **admin** : Gestion département, courriers, utilisateurs limités
3. **user** : Consultation et création de courriers personnels

---

## Système de Chiffrement

### Architecture

```
┌─────────────────────────────────────────────┐
│           EncryptionManager                 │
├─────────────────────────────────────────────┤
│ master_key  ← GEC_MASTER_KEY (env)          │
│ password_salt ← GEC_PASSWORD_SALT (env)     │
├─────────────────────────────────────────────┤
│ encrypt_data(plaintext) → ciphertext        │
│ decrypt_data(ciphertext) → plaintext        │
│ encrypt_file(path) → encrypted_path         │
│ decrypt_file(path) → decrypted_path         │
└─────────────────────────────────────────────┘
```

### Algorithmes

- **Chiffrement données** : AES-256-CBC avec IV aléatoire
- **Dérivation clé** : PBKDF2-HMAC-SHA256 (100 000 itérations)
- **Hachage mots de passe** : bcrypt (12 rounds) + sel applicatif

### Données Chiffrées

| Entité | Champs chiffrés |
|--------|-----------------|
| User | email, nom_complet, matricule, fonction, password_hash |
| Courrier | objet, expediteur, destinataire, numero_reference |
| ParametresSysteme | sendgrid_api_key, smtp_password |

---

## Sécurité Applicative

### Protection contre les Attaques

#### Injection SQL
- Utilisation exclusive de l'ORM SQLAlchemy
- Paramètres bindés pour les requêtes brutes
- Détection de patterns d'injection

#### XSS (Cross-Site Scripting)
- Échappement automatique Jinja2
- Sanitization des entrées utilisateur
- Headers de sécurité (Content-Security-Policy)

#### CSRF
- Tokens de session générés aléatoirement
- Validation sur les formulaires POST

#### Brute Force
- Rate limiting configurable par route
- Blocage IP après 8 tentatives échouées
- Lockout de 15 minutes

### Headers de Sécurité

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; ...
Permissions-Policy: camera=(), microphone=(), ...
Cache-Control: no-cache, no-store, must-revalidate
```

---

## Système de Cache

### Implémentation

```python
# Cache en mémoire avec TTL
cache_result(ttl_seconds=300)
def get_dashboard_statistics():
    # Calculs coûteux...
    return stats
```

### Éléments mis en cache

- Statistiques du tableau de bord (5 min)
- Paramètres système (10 min)
- Listes de départements (10 min)
- Compteurs de notifications (1 min)

---

## Système d'Email

### Architecture Multi-Provider

```
┌─────────────────────────────────────────────┐
│       send_email_from_system_config()       │
├─────────────────────────────────────────────┤
│                    │                        │
│   ┌────────────────▼────────────────┐       │
│   │  email_provider == 'sendgrid'?  │       │
│   └────────────────┬────────────────┘       │
│         Oui        │        Non             │
│   ┌────────────────▼────┐  ┌───────▼──────┐ │
│   │ send_with_sendgrid()│  │send_with_smtp│ │
│   └─────────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────┘
```

### Types d'Emails

- Notification nouveau courrier
- Notification transmission
- Test de configuration SMTP
- Templates personnalisables (EmailTemplate)

---

## Migrations Automatiques

### Fonctionnement

Au démarrage de l'application :

1. Vérification des tables manquantes
2. Ajout des colonnes manquantes
3. Application des corrections spécifiques à la BDD
4. Journalisation des modifications

### Tables Gérées

- migration_log : historique des migrations
- system_health : état du système

---

## Export/Import

### Format d'Export

```
export_courriers_YYYYMMDD_HHMMSS.zip
├── courriers_data.json    # Métadonnées (déchiffrées)
└── attachments/           # Fichiers (déchiffrés)
    └── {courrier_id}_{filename}
```

### Processus

**Export** :
1. Déchiffrement des données sensibles
2. Déchiffrement des fichiers attachés
3. Création du package ZIP

**Import** :
1. Extraction du package
2. Re-chiffrement avec la clé de l'instance
3. Création des enregistrements
4. Gestion des doublons

---

## Internationalisation

### Structure

```
lang/
├── fr.json    # Français (par défaut)
└── en.json    # Anglais
```

### Utilisation

```python
# Dans le code Python
from utils import t
message = t('dashboard.welcome')

# Dans les templates Jinja2
{{ t('common.save') }}
```

### Détection de Langue

1. Session utilisateur
2. Cookie de préférence
3. Préférence utilisateur (base de données)
4. En-tête Accept-Language du navigateur
5. Langue par défaut (français)

---

## Performance

### Optimisations Appliquées

- Index sur les colonnes fréquemment interrogées
- Pool de connexions PostgreSQL (pool_recycle=300)
- Cache en mémoire pour les données statiques
- Pagination des listes
- Lazy loading des relations

### Monitoring

```python
with PerformanceMonitor("operation_name"):
    # Code à mesurer
    pass
# Les temps sont journalisés
```

---

## Déploiement

### Configuration Gunicorn

```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

### Variables d'Environnement Requises

| Variable | Description | Obligatoire |
|----------|-------------|-------------|
| DATABASE_URL | URL PostgreSQL | Oui |
| SESSION_SECRET | Secret Flask | Oui |
| GEC_MASTER_KEY | Clé de chiffrement | Oui (production) |
| GEC_PASSWORD_SALT | Sel mots de passe | Oui (production) |
| ADMIN_PASSWORD | Mot de passe admin initial | Non |

---

## Logs et Audit

### Niveaux de Log

- DEBUG : Détails techniques
- INFO : Actions utilisateur
- WARNING : Événements anormaux
- ERROR : Erreurs applicatives
- CRITICAL : Erreurs fatales

### Audit Trail

Toutes les actions importantes sont enregistrées :
- Connexions/déconnexions
- Création/modification/suppression de courriers
- Transmissions
- Modifications de paramètres
- Tentatives d'accès refusées
