# GEC — Primer technique

GEC (Gestion Électronique du Courrier) est une application Flask de gestion de courrier administratif pour les institutions africaines (focus RDC). Déployée sur VPS 2 (168.231.86.201) port 5004, gérée via PM2.

## Stack

- **Backend** : Python 3.11 · Flask 3.1 · SQLAlchemy 2.0 · Gunicorn
- **Auth** : Flask-Login 0.6 · Flask-WTF (CSRF global)
- **DB** : PostgreSQL 14+ (prod) · SQLite (dev/tests)
- **Frontend** : HTML · Tailwind CSS (local vendor) · JS vanilla
- **Sécurité** : AES-256 (cryptography) · bcrypt · rate limiting · audit log
- **Email** : Resend API (`resend` SDK) + SMTP fallback
- **2FA** : TOTP via pyotp (super_admin uniquement)
- **PDF** : ReportLab · Export Excel : xlsxwriter
- **Cache** : Redis (optionnel) + fallback in-memory

## Structure des dossiers

```text
gec/
├── app.py              # Factory Flask, init DB, middlewares, user_loader, scheduler
├── main.py             # Point d'entrée (import app, run)
├── init_db.py          # Init base PostgreSQL (tables + données + super admin)
├── requirements.txt    # Dépendances Python (fichier unique)
│
├── models/             # Modèles SQLAlchemy
├── routes/             # Routes Flask (Blueprint-less, flat)
├── security/           # AES-256, rate limit, IP block, audit log, sanitize
├── services/           # email.py (Resend API + SMTP fallback)
├── utils/              # Helpers, migrations, performance, export/import, lang
│
├── algorithms/         # Logique algorithmique métier
├── config/             # Configuration Flask
├── scripts/            # Scripts de maintenance
│
├── lang/               # Fichiers JSON de traduction (fr.json, en.json)
├── templates/          # Templates Jinja2
├── static/
│   ├── css/ · js/ · img/ · vendor/
│   └── uploads/        # Fichiers joints (courriers, photos profil)
└── docs/               # Documentation technique
```

## Imports à utiliser

```python
from models import User, Courrier, ...          # modèles
from security import rate_limit, audit_log, ... # sécurité + chiffrement
from services.email import send_new_mail_notification
from utils import t, format_date, ...           # helpers
from utils.migrations import run_automatic_migrations
from utils.performance import cache_result
from utils.export_import import validate_backup_integrity
```

## Modèles clés

`User` · `Courrier` · `CourrierForward` · `CourrierComment` · `CourrierModification`
`CourrierAttachment` · `CourrierSignature` · `Tag` · `CourrierTag` · `StatutCourrier`
`Departement` · `Role` · `RolePermission` · `Notification` · `ParametresSysteme`
`LogActivite` · `EmailTemplate`

## Rôles

`super_admin` > `admin` > `user` — permissions granulaires via `RolePermission`

## Règles critiques

1. Jamais modifier directement sur le VPS — workflow local → GitHub → `git pull` VPS
2. Jamais committer `.env`, `venv/`, `static/uploads/`, `*.db`
3. `DEBUG=False` en production
4. Toute nouvelle route : `@login_required` + `has_permission()`
5. Fichier de dépendances unique : `requirements.txt`
6. Email : Resend API uniquement (`re_xxx`), jamais SendGrid
