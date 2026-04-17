# GEC — Configuration Projet Claude

**Projet** : GEC - Gestion Électronique du Courrier  
**Owner** : MOA Digital Agency  
**GitHub** : `moa-digitalagency/gec`  
**VPS** : VPS 2 (168.231.86.201) — port 5004 — `/var/websites/gec`  
**Dernière mise à jour** : 17 Avril 2026

---

## Stack Technique

| Couche       | Technologie                              |
|--------------|------------------------------------------|
| Backend      | Python 3.11 · Flask 3.1 · Gunicorn       |
| ORM          | SQLAlchemy 2.0 · Flask-SQLAlchemy 3.1    |
| Auth         | Flask-Login 0.6                          |
| Base données | PostgreSQL 14+ (prod) · SQLite (dev)     |
| Frontend     | HTML · Tailwind CSS · JS vanilla         |
| Sécurité     | cryptography (AES-256) · bcrypt · pycryptodome |
| PDF          | ReportLab 4.4                            |
| Email        | Resend API / SMTP configurable           |
| Export       | pandas · xlsxwriter                      |
| Multilingue  | Système custom via `lang/` + `lang_utils.py` |

---

## Architecture des Fichiers

```
gec/
├── app.py              # Factory Flask + init DB + middlewares + user_loader
├── main.py             # Point d'entrée (import app, run)
├── models.py           # Tous les modèles SQLAlchemy
├── views.py            # Toutes les routes Flask (Blueprint-less, flat)
├── utils.py            # Helpers : PDF, accuse reception, logs, langue, export
├── encryption_utils.py # AES-256 : encrypt/decrypt données sensibles
├── security_utils.py   # Rate limit, IP block, audit log, sanitize, headers
├── email_utils.py      # Notifications email (SendGrid/SMTP)
├── performance_utils.py# Cache, stats dashboard, optimisation requêtes
├── migration_utils.py  # Migrations automatiques colonnes manquantes
├── export_import_utils.py # Backup/restore complet (ZIP + DB)
├── lang_utils.py       # Gestion fichiers de langue
├── lang/               # Fichiers JSON de traduction (fr.json, en.json)
├── templates/          # Templates Jinja2 (Tailwind inline)
├── static/             # CSS, JS, images, vendor
├── uploads/            # Fichiers joints (courriers, photos profil)
└── docs/               # Documentation technique et fonctionnelle
```

---

## Modèles de Données

| Modèle               | Rôle                                              |
|----------------------|---------------------------------------------------|
| `User`               | Utilisateurs (super_admin / admin / user)         |
| `Departement`        | Entités organisationnelles (code + chef)          |
| `Courrier`           | Courrier entrant ou sortant (pièce centrale)      |
| `CourrierModification` | Historique des modifications de courrier        |
| `CourrierForward`    | Transmissions de courrier entre utilisateurs      |
| `CourrierComment`    | Commentaires / annotations / instructions         |
| `StatutCourrier`     | Statuts paramétrables (RECU, EN_COURS, etc.)      |
| `TypeCourrierSortant`| Types de courrier sortant (Note, Lettre, etc.)    |
| `Role`               | Rôles personnalisés                               |
| `RolePermission`     | Permissions granulaires par rôle                  |
| `Notification`       | Notifications in-app                              |
| `IPBlock`            | IPs bloquées temporairement                       |
| `IPWhitelist`        | IPs en liste blanche                              |
| `ParametresSysteme`  | Config globale (logo, SMTP, footer, PDF...)       |
| `LogActivite`        | Audit log des actions utilisateurs                |
| `EmailTemplate`      | Templates email multilingues dynamiques           |

---

## Système de Rôles & Permissions

**Hiérarchie** : `super_admin` > `admin` > `user`

| Permission clé         | Rôle minimum |
|------------------------|--------------|
| `manage_users`         | super_admin  |
| `manage_roles`         | super_admin  |
| `manage_system_settings` | admin      |
| `read_all_mail`        | super_admin  |
| `read_department_mail` | admin        |
| `read_own_mail`        | user         |
| `edit_all_mail`        | super_admin  |
| `edit_department_mail` | admin        |
| `delete_mail`          | super_admin  |
| `view_trash`           | super_admin  |
| `export_data`          | user+        |
| `manage_backup`        | super_admin  |
| `manage_updates`       | super_admin  |

---

## Conventions de Code

### Sécurité des données
- Les champs sensibles (`email`, `nom_complet`, `objet`, `expediteur`, etc.) ont une colonne `_encrypted` en parallèle
- Pattern : `set_encrypted_X()` / `get_decrypted_X()` avec fallback clair
- Ne jamais stocker de clés en dur — utiliser `.env` : `GEC_MASTER_KEY`, `GEC_PASSWORD_SALT`

### Variables d'environnement obligatoires
```
DATABASE_URL=postgresql://user:password@localhost/gecmines
SESSION_SECRET=...
GEC_MASTER_KEY=...
GEC_PASSWORD_SALT=...
FLASK_ENV=production|development
ADMIN_PASSWORD=...
```

### Numérotation courrier
- Mode `automatique` : format configurable, ex. `GEC-{year}-{counter:05d}`
- Mode `manuel` : saisi par l'utilisateur
- Paramétrable dans `ParametresSysteme`

### Multilingue
- Fonction de traduction : `t('clé')` (importée dans views + context_processor)
- Fichiers : `lang/fr.json`, `lang/en.json`
- La langue active est en session utilisateur (`langue` field sur `User`)

### Migrations
- `migration_utils.run_automatic_migrations()` — détecte les colonnes manquantes et les ajoute à chaud
- Exécuté automatiquement au démarrage dans `app.py`

### Soft delete
- Les courriers ne sont jamais supprimés physiquement : `is_deleted = True` + `deleted_at` + `deleted_by_id`
- Vue `/trash` pour consulter et restaurer

---

## Règles de Développement

1. **Jamais modifier directement sur le VPS** — workflow local → GitHub → `git pull` VPS
2. **Jamais committer** : `.env`, `venv/`, `uploads/`, `*.db`, `screenshots/`
3. **Jamais `DEBUG=True` en production**
4. **Toujours** lancer `/validate-and-push` après une modification
5. **Toujours créer une PR** — jamais push sur `main` directement
6. **Avant toute route nouvelle** : vérifier `@login_required` + permission check via `current_user.has_permission()`

---

## Déploiement VPS 2

```bash
# Connexion
ssh -i ~/.ssh/vps1_access root@168.231.86.201

# Déployer
cd /var/websites/gec
git pull origin main
pm2 restart gec  # ou le nom PM2 exact

# Vérifier
curl http://localhost:5004
pm2 logs gec
```
