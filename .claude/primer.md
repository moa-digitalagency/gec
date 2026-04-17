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

## Fichiers principaux

| Fichier | Rôle |
|---|---|
| `app.py` | Factory Flask, init DB, middlewares, user_loader, scheduler rappels |
| `main.py` | Point d'entrée (import app, run) |
| `models.py` | Tous les modèles SQLAlchemy |
| `views.py` | Toutes les routes Flask (flat, pas de blueprint) |
| `email_utils.py` | Envoi email via Resend API + SMTP fallback |
| `migration_utils.py` | Migrations automatiques au démarrage |
| `performance_utils.py` | Cache Redis/mémoire, FTS, pagination |
| `security_utils.py` | Rate limit, IP block, audit log, sanitize |
| `encryption_utils.py` | AES-256 chiffrement données sensibles |

## Modèles clés

`User` · `Courrier` · `CourrierForward` · `CourrierComment` · `CourrierModification` · `CourrierAttachment` · `CourrierSignature` · `Tag` · `CourrierTag` · `StatutCourrier` · `Departement` · `Role` · `RolePermission` · `Notification` · `ParametresSysteme` · `LogActivite` · `EmailTemplate`

## Rôles

`super_admin` > `admin` > `user` — permissions granulaires via `RolePermission`

## Règles critiques

1. Jamais modifier directement sur le VPS — workflow local → GitHub → `git pull` VPS
2. Jamais committer `.env`, `venv/`, `uploads/`, `*.db`
3. `DEBUG=False` en production
4. Toute nouvelle route : `@login_required` + `has_permission()`
5. Fichier de dépendances unique : `requirements.txt`
