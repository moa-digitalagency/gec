# GEC — Primer (État Session)

**Dernière mise à jour** : 17 Avril 2026  
**Statut général** : Application en production sur VPS 2 (port 5004)

---

## État Actuel

| Composant           | Statut      | Notes                                      |
|---------------------|-------------|--------------------------------------------|
| Backend Flask       | Stable      | Python 3.11, Flask 3.1                     |
| Base de données     | PostgreSQL  | Prod VPS 2 — SQLite en dev local           |
| Authentification    | Fonctionnel | Flask-Login + roles/permissions            |
| Courriers ENTRANT   | Fonctionnel | Numérotation auto/manuelle                 |
| Courriers SORTANT   | Fonctionnel | Types configurables                        |
| Transmissions       | Fonctionnel | CourrierForward + notifications            |
| Export PDF/Excel    | Fonctionnel | ReportLab + pandas/xlsxwriter              |
| Email notifications | Fonctionnel | SendGrid ou SMTP (configurable en UI)      |
| Multilingue FR/EN   | Fonctionnel | lang/ + lang_utils.py                      |
| Chiffrement AES-256 | Actif       | encryption_utils.py — champs _encrypted    |
| Backup/Restore      | Fonctionnel | export_import_utils.py + UI admin          |
| Mise à jour système | Fonctionnel | Git (online) + ZIP (offline) via UI admin  |
| Déploiement VPS 2   | Actif       | PM2 port 5004, /var/websites/gec           |

---

## Session du 17 Avril 2026

- [x] Clone du repo depuis GitHub (`moa-digitalagency/gec`)
- [x] Initialisation du dossier `.claude/` complet

---

## TODOs Actifs

_(Aucun TODO actif pour l'instant — à remplir en début de prochaine session)_

---

## Contexte de la dernière modification

Première initialisation `.claude/` — pas de modification du code source.  
Le projet est cloné dans `C:\Users\shaba\Projets Claude\gec`.
