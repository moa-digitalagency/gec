# Prompt — Analyse et synchronisation d'un projet similaire à GEC

> Copiez ce prompt dans une nouvelle conversation Claude Code en ouvrant le projet cible.
> Remplacez les sections entre `[crochets]` par les infos du projet concerné.

---

## Prompt à utiliser

```
Tu vas analyser le projet Flask "[NOM_DU_PROJET]" situé dans ce dossier de travail,
puis proposer un plan de modifications concret pour l'aligner sur les standards GEC.

Ce projet est similaire à GEC (Gestion Électronique du Courrier) :
application Flask avec SQLAlchemy, Flask-Login, Tailwind CSS, déployée sur VPS via PM2/Gunicorn.

**RÉFÉRENCE GEC** : stack et conventions documentées dans `.claude/primer.md` ou `.claude/CLAUDE.md`
si ce projet est GEC lui-même, sinon utilise les infos ci-dessous comme référence externe.

Stack de référence GEC :
- Backend : Flask 3.1 · SQLAlchemy 2.0 · Gunicorn
- Auth : Flask-Login 0.6 · Flask-WTF (CSRF global)
- DB : PostgreSQL (prod) · SQLite (dev)
- Frontend : HTML · Tailwind CSS · JS vanilla
- Email : **Resend API** (resend SDK, clé format `re_xxx`) + SMTP fallback — JAMAIS SendGrid
- Sécurité : AES-256 (cryptography) · bcrypt · rate limiting · audit log
- 2FA : TOTP via pyotp (super_admin uniquement)
- PDF : ReportLab · Export Excel : xlsxwriter
- Cache : Redis optionnel + fallback in-memory
- Dépendances : fichier unique `requirements.txt`

---

## Étape 1 — Cartographie complète

Lis TOUS les fichiers .py de la racine + tous les sous-dossiers. Produis un rapport avec :

### 1.1 Architecture générale
- Point d'entrée (app.py / main.py / wsgi.py ?)
- Fichier de config / factory pattern ?
- Blueprints ou routes plates dans views.py ?
- Séparation modèles / vues / utilitaires ?

### 1.2 Stack technique détectée
- Framework + version
- ORM
- Auth
- Base de données
- Frontend
- **Email : quel provider ? (SendGrid → à migrer, Resend → OK, SMTP → OK)**
- Cache
- Tests

### 1.3 Fichier de dépendances
- Quel fichier fait autorité ?
- Y a-t-il des doublons (pyproject.toml, uv.lock, setup.cfg, project-dependencies.txt) ?
- Dépendances inutilisées ou manquantes ?
- **SendGrid (sendgrid) présent dans requirements → à remplacer par resend**

### 1.4 Modèles de données
- Liste tous les modèles SQLAlchemy avec colonnes principales
- Relations many-to-many, foreign keys critiques
- Colonnes chiffrées ou sensibles ?
- Soft-delete implémenté ?

### 1.5 Système de rôles et permissions
- Y a-t-il un RBAC ? Comment est-il implémenté ?
- Quels décorateurs protègent les routes ?

---

## Étape 2 — Audit qualité

### 2.1 Sécurité
- CSRF : Flask-WTF global ou par formulaire ?
- Injection SQL : ORM strict ou raw queries ?
- XSS : sanitize_input appliqué ?
- Upload fichiers : validation type + taille ?
- Rate limiting : implémenté ?
- Secrets en dur dans le code ?
- **SendGrid API key dans le code ou .env → blocker P0**

### 2.2 Qualité du code
- Routes sans @login_required ?
- Fonctions > 100 lignes (God functions) ?
- Imports circulaires ?
- Print() de debug laissés ?
- Gestion des erreurs : try/except globaux ou par fonction ?

### 2.3 Performance
- N+1 queries (lazy loading non optimisé) ?
- Pagination implémentée ?
- Index DB définis sur les colonnes filtrées ?
- Cache utilisé pour les requêtes lourdes ?

### 2.4 Maintenabilité
- Migrations : Flask-Migrate, Alembic, migration_utils.py ou manuel ?
- Tests : couverture estimée ?
- Variables d'environnement documentées (.env.example) ?
- Logs : niveau approprié en prod ?

---

## Étape 3 — Comparaison avec GEC

Compare ce projet avec GEC sur ces points :

| Fonctionnalité | GEC | [NOM_DU_PROJET] | Écart |
|---|---|---|---|
| RBAC granulaire | ✅ RolePermission | ? | ? |
| Chiffrement AES-256 | ✅ | ? | ? |
| Migrations automatiques | ✅ migration_utils.py | ? | ? |
| **Email Resend API** | ✅ resend SDK | ? | **Migrer si SendGrid** |
| 2FA TOTP | ✅ super_admin | ? | ? |
| Export Excel/PDF | ✅ | ? | ? |
| Kanban drag & drop | ✅ | ? | ? |
| Tags sur entités | ✅ | ? | ? |
| Timeline / historique | ✅ | ? | ? |
| Dark mode | ✅ | ? | ? |
| Recherche full-text | ✅ PostgreSQL GIN | ? | ? |
| Cache Redis + fallback | ✅ | ? | ? |
| Circuit de signature | ✅ | ? | ? |
| Rappels automatiques | ✅ scheduler thread | ? | ? |
| Fichier deps unique | ✅ requirements.txt | ? | ? |
| Pas de scripts Replit | ✅ | ? | ? |

---

## Étape 4 — Plan d'action priorisé

### P0 — Bloquant (sécurité ou crash)
Issues critiques à corriger immédiatement.
**Inclure obligatoirement** :
- Toute clé API SendGrid en dur → remplacer par Resend
- Tout `DEBUG=True` en dur
- Routes sans `@login_required`
- Secrets commités

### P1 — Important (migration Resend + qualité)
- Si SendGrid présent dans requirements.txt → remplacer par `resend==2.10.0`
- Si `email_utils.py` utilise `sendgrid` → réécrire pour Resend API
- Si plusieurs fichiers de dépendances → consolider en `requirements.txt` unique
- Si scripts install Replit/install.sh obsolètes → supprimer
- Améliorations structurelles recommandées

### P2 — Nice-to-have (features GEC manquantes)
Features de GEC à porter dans ce projet si pertinent.

---

## Étape 5 — Exécution des modifications

**STOP après le rapport — attendre "go" avant de toucher au code.**

Une fois "go" reçu, appliquer dans cet ordre :

### 5.1 Nettoyage (P0 d'abord)
1. Supprimer fichiers obsolètes : `.replit`, `replit.md`, `pyproject.toml`, `uv.lock`,
   `project-dependencies.txt`, `install-*.sh`, `install-*.bat`
2. Consolider les dépendances dans `requirements.txt` unique
3. Corriger toute secret en dur

### 5.2 Migration Resend (si SendGrid détecté)
1. Dans `requirements.txt` : retirer `sendgrid` → ajouter `resend==2.10.0`
2. Réécrire `email_utils.py` (ou équivalent) :
   - Supprimer tout import `sendgrid`
   - Implémenter `send_email_with_resend()` via `resend.Emails.send()`
   - Clé API format `re_xxx` depuis config/DB (jamais en dur)
   - Fallback SMTP conservé
3. Dans les modèles : renommer `sendgrid_api_key` → `resend_api_key`
4. Dans les migrations : ajouter colonne `resend_api_key`, mettre `DEFAULT 'resend'`
5. Dans les templates settings : mettre à jour les champs et labels
6. Dans les fichiers de langue (lang/*.json) : renommer les clés `sendgrid_*` → `resend_*`
7. Grep final pour confirmer 0 référence SendGrid

### 5.3 Features GEC à porter (P2 validés)
Appliquer les features retenues du plan P2.

### 5.4 Validation finale
- Grep `sendgrid` → 0 résultat attendu
- Grep `DEBUG=True` → 0 résultat attendu
- Vérifier que toutes les routes ont `@login_required`
- Lancer `/validate-and-push` pour screenshots + PR

---

## Format de sortie attendu (rapport)

Rends un rapport Markdown structuré avec :
- Un résumé exécutif (5 lignes max)
- Les sections 1 à 4 ci-dessus
- Un score global /10 par catégorie (Sécurité, Qualité, Performance, Maintenabilité)
- **Les 3 actions les plus urgentes en gras**
- Liste explicite des fichiers à modifier dans le plan d'action
```

---

## Notes d'utilisation

- Ce prompt couvre l'analyse **ET** les modifications (rapport → validation → exécution)
- La section Resend est systématique : tout projet similaire doit utiliser Resend, jamais SendGrid
- Pour un projet Django ou FastAPI, adapter les sections 1.2 et 2.1
- Toujours lire **tous** les fichiers `.py` de la racine avant de répondre
- Si le projet a des blueprints, lire aussi chaque `routes.py` / `views.py` dans les sous-dossiers
- Workflow après modifications : `/validate-and-push` → screenshots → PR (jamais push direct sur main)

## Projets analysés avec ce prompt

| Projet | Date | Score moyen | P0 résolus | Migration Resend |
| --- | --- | --- | --- | --- |
| GEC | 2026-04-04 | 8.5/10 | Sprints 1-4 complétés | ✅ Avril 2026 |
| [À compléter] | | | | |
