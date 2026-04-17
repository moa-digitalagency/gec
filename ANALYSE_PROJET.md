# Prompt — Analyse d'un projet similaire à GEC

> Copiez ce prompt dans une nouvelle conversation Claude Code en ouvrant le projet cible.
> Remplacez les sections entre `[crochets]` par les infos du projet concerné.

---

## Prompt à utiliser

```
Tu vas analyser le projet Flask "[NOM_DU_PROJET]" situé dans ce dossier de travail.
Ce projet est similaire à GEC (Gestion Électronique du Courrier) : application Flask
avec SQLAlchemy, Flask-Login, Tailwind CSS, déployée sur un VPS via PM2/Gunicorn.

---

## Étape 1 — Cartographie complète

Lis la structure du projet et produis un rapport avec :

### 1.1 Architecture générale
- Point d'entrée (app.py / main.py / wsgi.py ?)
- Fichier de config / factory pattern ?
- Blueprints ou routes plates dans views.py ?
- Séparation modèles / vues / utilitaires ?

### 1.2 Stack technique détectée
- Framework + version (Flask, FastAPI, Django ?)
- ORM (SQLAlchemy, Peewee, Django ORM ?)
- Auth (Flask-Login, JWT, session custom ?)
- Base de données (PostgreSQL, SQLite, MySQL ?)
- Frontend (Tailwind, Bootstrap, vanilla ?)
- Email (Resend, SMTP, autre ?)
- Cache (Redis, mémoire, aucun ?)
- Tests (pytest, unittest, aucun ?)

### 1.3 Fichier de dépendances
- Quel fichier fait autorité (requirements.txt) ?
- Y a-t-il des doublons / fichiers obsolètes (pyproject.toml, uv.lock, setup.cfg) ?
- Dépendances inutilisées ou manquantes détectées ?

### 1.4 Modèles de données
- Liste tous les modèles SQLAlchemy avec leurs colonnes principales
- Relations many-to-many, foreign keys critiques
- Colonnes chiffrées ou sensibles ?
- Système de soft-delete ?

### 1.5 Système de rôles et permissions
- Y a-t-il un RBAC ? Comment est-il implémenté ?
- Quels décorateurs protègent les routes ?

---

## Étape 2 — Audit qualité

### 2.1 Sécurité
- CSRF : Flask-WTF global ou par formulaire ?
- Injection SQL : ORM strict ou raw queries exposées ?
- XSS : sanitize_input appliqué ?
- Upload fichiers : validation type + taille ?
- Rate limiting : implémenté ?
- Secrets en dur dans le code ?

### 2.2 Qualité du code
- Routes sans @login_required ?
- Fonctions > 100 lignes (God functions) ?
- Imports circulaires ?
- Print() de debug laissés en production ?
- Gestion des erreurs : try/except globaux ou par fonction ?

### 2.3 Performance
- N+1 queries (lazy loading non optimisé) ?
- Pagination implémentée ou chargement complet ?
- Index DB définis sur les colonnes filtrées ?
- Cache utilisé pour les requêtes lourdes ?

### 2.4 Maintenabilité
- Migrations : Flask-Migrate, Alembic, ou manuel ?
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
| Email Resend API | ✅ | ? | ? |
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

---

## Étape 4 — Plan d'action priorisé

Sur la base de l'audit, propose un plan en 3 niveaux :

### P0 — Bloquant (sécurité ou crash)
Liste les issues critiques à corriger immédiatement.

### P1 — Important (qualité et maintenabilité)
Liste les améliorations structurelles recommandées.

### P2 — Nice-to-have (fonctionnalités GEC manquantes)
Liste les features de GEC à porter dans ce projet si pertinent.

---

## Format de sortie attendu

Rends un rapport Markdown structuré avec :
- Un résumé exécutif (5 lignes max)
- Les sections 1 à 4 ci-dessus
- Un score global /10 par catégorie (Sécurité, Qualité, Performance, Maintenabilité)
- Les 3 actions les plus urgentes en gras

**STOP après le rapport — attendre "go" avant de toucher au code.**
```

---

## Notes d'utilisation

- Ce prompt est conçu pour des projets Flask/Python avec SQLAlchemy et Tailwind
- Pour un projet Django ou FastAPI, adapter la section 1.2 et 2.1
- La section "Comparaison avec GEC" peut être retirée si le projet est très différent
- Toujours lire **tous** les fichiers `.py` de la racine avant de répondre (app.py, models.py, views.py, utils.py)
- Si le projet a des blueprints, lire aussi chaque `routes.py` ou `views.py` dans les sous-dossiers

## Projets analysés avec ce prompt

| Projet | Date | Score moyen | Actions P0 résolues |
|---|---|---|---|
| GEC | 2026-04-04 | 8.5/10 | Sprints 1-4 complétés |
| [À compléter] | | | |
