# GEC — Configuration Projet Claude

**Projet** : GEC - Gestion Électronique du Courrier
**Owner** : MOA Digital Agency
**GitHub** : `moa-digitalagency/gec`
**VPS** : VPS 2 (168.231.86.201) — port 5004 — `/var/websites/gec`
**Domaines** : solution-gec.com + demo.solution-gec.com
**Dernière mise à jour** : Mai 2026

---

## Stack Technique

| Couche       | Technologie                                                   |
|--------------|---------------------------------------------------------------|
| Backend      | Python 3.11 · Flask 3.1 · Gunicorn                           |
| ORM          | SQLAlchemy 2.0 · Flask-SQLAlchemy 3.1                        |
| Auth         | Flask-Login 0.6 · Flask-WTF (CSRF global) · TOTP 2FA        |
| Base données | PostgreSQL 14+ (prod) · SQLite (dev)                          |
| Frontend     | HTML · Tailwind CSS (vendor local) · JS vanilla               |
| Sécurité     | AES-256-GCM v2 (cryptography) · bcrypt · rate limiting        |
| PDF          | ReportLab 4.4                                                 |
| Email        | Resend API / SMTP configurable                                |
| Export       | pandas · xlsxwriter                                           |
| Multilingue  | Système custom via `lang/` + `utils/helpers.py`               |
| PWA          | manifest.json + service worker (`static/js/sw.js`)            |

---

## Architecture des Fichiers

```
gec/
├── app.py                      # Factory Flask + init DB + middlewares + user_loader
├── main.py                     # Point d'entrée (import app, run)
├── init_db.py                  # Initialisation base PostgreSQL (tables + données)
├── requirements.txt            # Dépendances Python
│
├── algorithms/                 # Logique algorithmique métier
├── config/                     # Configuration Flask
│
├── models/
│   ├── courrier.py             # Courrier, CourrierAttachment, CourrierActionSignature...
│   ├── user.py                 # User (_SUPER_ADMIN_MAIL_BLOCKED_PERMISSIONS INVIOLABLE)
│   └── __init__.py
│
├── routes/
│   ├── mail.py                 # Routes courrier (register, edit, forward, comment, sign...)
│   ├── api.py                  # API JSON (verify_signatures, search, stats...)
│   ├── auth.py                 # Login, logout, 2FA, session expiry
│   └── __init__.py
│
├── security/
│   ├── encryption.py           # AES-256-GCM v2 + compat v1 CBC · fail-fast master key
│   ├── auth.py                 # rate_limit, get_client_ip, audit_log, sanitize, headers
│   └── __init__.py
│
├── services/
│   └── email.py                # Notifications email (Resend API + SMTP fallback)
│
├── utils/
│   ├── helpers.py              # sign_courrier_action(), log_activity(), t(), format_date()...
│   ├── pdf.py                  # Génération PDF (accusé réception, liste courriers, logs)
│   ├── migrations.py           # Migrations automatiques colonnes manquantes
│   ├── performance.py          # Cache, stats dashboard
│   └── __init__.py
│
├── static/
│   ├── css/design-system.css   # Classes gec-*, skeleton loading
│   ├── js/sw.js                # Service worker PWA
│   ├── img/icon-192.svg · icon-512.svg
│   ├── manifest.json           # PWA manifest
│   ├── uploads/                # Fichiers joints (chiffrés AES-GCM en prod)
│   └── vendor/                 # Librairies JS/CSS tierces
│
├── templates/
│   ├── new_base.html           # Base template (PWA meta + SW + sidebar)
│   ├── mail_detail_new.html    # Détail courrier (timeline signature électronique)
│   ├── dashboard.html          # Tableau de bord (skeleton stat-cards)
│   ├── view_mail.html          # Liste courriers (skeleton table rows)
│   └── ...
│
├── lang/                       # Fichiers JSON de traduction (fr.json, en.json)
└── docs/                       # Documentation technique
```

---

## Modèles de Données

| Modèle                    | Rôle                                                          |
|---------------------------|---------------------------------------------------------------|
| `User`                    | Utilisateurs (super_admin / admin / user)                    |
| `Departement`             | Entités organisationnelles (code + chef)                     |
| `Courrier`                | Courrier entrant ou sortant (pièce centrale)                 |
| `CourrierAttachment`      | Pièces jointes supplémentaires (`fichier_encrypted` BOOLEAN) |
| `CourrierModification`    | Historique des modifications de courrier                     |
| `CourrierForward`         | Transmissions de courrier entre utilisateurs                 |
| `CourrierComment`         | Commentaires / annotations / instructions                    |
| `CourrierSignature`       | Circuit de signature hiérarchique                            |
| `CourrierActionSignature` | **NOUVEAU** — Hash chain SHA-256 non-répudiation             |
| `StatutCourrier`          | Statuts paramétrables (RECU, EN_COURS, etc.)                 |
| `TypeCourrierSortant`     | Types de courrier sortant (Note, Lettre, etc.)               |
| `Tag` / `CourrierTag`     | Tags sur courriers                                           |
| `Role` / `RolePermission` | Rôles personnalisés + permissions granulaires                |
| `Notification`            | Notifications in-app                                         |
| `IPBlock` / `IPWhitelist` | Sécurité IP                                                  |
| `ParametresSysteme`       | Config globale (logo, SMTP, footer, PDF...)                  |
| `LogActivite`             | Audit log des actions utilisateurs                           |
| `EmailTemplate`           | Templates email multilingues dynamiques                      |

---

## Système de Rôles & Permissions

**Hiérarchie** : `super_admin` > `admin` > `user`

**INVIOLABLE** : `_SUPER_ADMIN_MAIL_BLOCKED_PERMISSIONS` frozenset dans `models/user.py` — le super_admin n'a JAMAIS accès aux courriers (6 points de contrôle).

| Permission clé           | Rôle minimum |
|--------------------------|--------------|
| `manage_users`           | super_admin  |
| `manage_roles`           | super_admin  |
| `manage_system_settings` | admin        |
| `read_all_mail`          | super_admin  |
| `read_department_mail`   | admin        |
| `read_own_mail`          | user         |
| `edit_all_mail`          | super_admin  |
| `edit_department_mail`   | admin        |
| `delete_mail`            | super_admin  |
| `view_trash`             | super_admin  |
| `export_data`            | user+        |
| `manage_backup`          | super_admin  |
| `manage_updates`         | super_admin  |

---

## Conventions de Code

### Imports

```python
from models import User, Courrier, CourrierActionSignature, ...
from security import rate_limit, sanitize_input, audit_log
from security import encrypt_uploaded_file, decrypt_file_for_download
from services.email import send_new_mail_notification, send_comment_notification
from utils import t, get_current_language, format_date, sign_courrier_action
from utils.migrations import run_automatic_migrations
from utils.performance import cache_result, get_dashboard_statistics
```

### Sécurité des données

- Chiffrement fichiers : `encrypt_uploaded_file()` / `decrypt_file_for_download()` — AES-256-GCM v2
- Fichiers temp après déchiffrement : `try: send_file(temp) finally: os.unlink(temp)`
- Champs DB : `set_encrypted_*()` dans `register_mail()` et `edit_courrier()`
- `GEC_MASTER_KEY` absente → fail-fast au démarrage (log CRITICAL)

### Signature électronique — règle obligatoire

```python
# Avant CHAQUE db.session.commit() dans les routes courrier :
sign_courrier_action(courrier.id, current_user, 'ACTION_TYPE', {'clé': 'valeur'})
db.session.commit()
```

Types : CREATION · MODIF_STATUT · MODIF_CHAMP · TRANSMISSION · COMMENTAIRE · ANNOTATION · INSTRUCTION · TELECHARGEMENT · VISUALISATION · SIGNATURE · REJET · SUPPRESSION · RESTAURATION · CIRCUIT_INIT

### Variables d'environnement obligatoires

```
DATABASE_URL=postgresql://user:password@localhost/gec_db
SESSION_SECRET=...
GEC_MASTER_KEY=...           ← OBLIGATOIRE — fail-fast si absent
GEC_PASSWORD_SALT=...
FLASK_ENV=production|development
ADMIN_PASSWORD=...
```

### Numérotation courrier

- Mode `automatique` : format configurable, ex. `GEC-{year}-{counter:05d}`
- Mode `manuel` : saisi par l'utilisateur
- Paramétrable dans `ParametresSysteme`

### Multilingue

- Fonction : `t('clé')` (importée dans routes + context_processor)
- Fichiers : `lang/fr.json`, `lang/en.json`

### Migrations

- `utils.migrations.run_automatic_migrations()` — détecte colonnes manquantes, exécuté au démarrage
- Flask-Migrate pour les nouvelles tables : `flask db migrate` + `flask db upgrade`

**⚠️ Migration en attente sur VPS** :
```bash
flask db migrate -m "add courrier_action_signature and fichier_encrypted"
flask db upgrade
```

### Soft delete

Courriers jamais supprimés physiquement : `is_deleted = True` + `deleted_at` + `deleted_by_id`. Vue `/trash` pour restaurer.

---

## Règles de Développement

1. **Jamais modifier directement sur le VPS** — workflow local → GitHub → `git pull` VPS
2. **Jamais committer** : `.env`, `venv/`, `static/uploads/`, `*.db`, `.claude/`, `tests/`, `exports/`
3. **Jamais `DEBUG=True` en production**
4. **Toujours** lancer `/validate-and-push` après une modification
5. **Toujours créer une PR** — jamais push sur `main` directement
6. **Avant toute route nouvelle** : `@login_required` + `current_user.has_permission()`
7. **`sign_courrier_action()`** : appeler avant chaque commit dans les routes courrier

---

## Déploiement VPS 2

```bash
# Connexion
ssh -i ~/.ssh/vps1_access root@168.231.86.201

# Déployer
cd /var/websites/gec
git pull origin main
pm2 restart gec

# Si migration nécessaire
source venv/bin/activate
flask db migrate -m "description"
flask db upgrade
pm2 restart gec

# Vérifier
curl http://localhost:5004
pm2 logs gec
```
