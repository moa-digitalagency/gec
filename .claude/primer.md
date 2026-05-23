# GEC — Primer technique

GEC (Gestion Électronique du Courrier) est une application Flask de gestion de courrier administratif pour les institutions africaines (focus RDC). Déployée sur VPS 2 (168.231.86.201) port 5004, gérée via PM2. Domaines : solution-gec.com + demo.solution-gec.com.

**Dernière session** : Mai 2026 — refonte sécurité + nouvelles fonctionnalités majeures.

---

## Stack

- **Backend** : Python 3.11 · Flask 3.1 · SQLAlchemy 2.0 · Gunicorn
- **Auth** : Flask-Login 0.6 · Flask-WTF (CSRF global)
- **DB** : PostgreSQL 14+ (prod) · SQLite (dev)
- **Frontend** : HTML · Tailwind CSS (local vendor) · JS vanilla
- **Sécurité** : AES-256-GCM v2 (cryptography) · bcrypt · rate limiting · audit log
- **Email** : Resend API (`resend` SDK) + SMTP fallback
- **2FA** : TOTP via pyotp (super_admin uniquement)
- **PDF** : ReportLab · Export Excel : xlsxwriter
- **PWA** : manifest.json + service worker (cache-first static, network-first HTML)

---

## Structure des dossiers

```text
gec/
├── app.py              # Factory Flask, init DB, middlewares, user_loader
├── main.py             # Point d'entrée
├── init_db.py          # Init base PostgreSQL
├── requirements.txt
│
├── models/             # Modèles SQLAlchemy
├── routes/             # Routes Flask (Blueprint-less, flat)
│   ├── mail.py         # Routes courrier principales (register, edit, forward, comment...)
│   ├── api.py          # API JSON (verify_signatures, search...)
│   └── ...
├── security/           # AES-256-GCM, rate limit, IP block, audit log
│   ├── encryption.py   # encrypt_uploaded_file / decrypt_file_for_download (v2 GCM + compat v1 CBC)
│   └── auth.py         # get_client_ip, rate_limit, audit_log
├── services/           # email.py
├── utils/
│   ├── helpers.py      # sign_courrier_action(), log_activity(), generate_accuse_reception()...
│   └── ...
│
├── static/
│   ├── css/design-system.css   # classes gec-*, skeleton loading
│   ├── js/sw.js                # service worker PWA
│   ├── img/icon-192.svg · icon-512.svg
│   └── manifest.json           # PWA manifest
├── templates/
│   ├── new_base.html           # base template (PWA meta + SW register)
│   ├── mail_detail_new.html    # détail courrier (timeline signature)
│   └── ...
└── docs/
```

---

## Modèles clés

`User` · `Courrier` · `CourrierAttachment` · `CourrierForward` · `CourrierComment`
`CourrierModification` · `CourrierSignature` · `CourrierActionSignature` ← **nouveau mai 2026**
`Tag` · `CourrierTag` · `StatutCourrier` · `Departement` · `Role` · `RolePermission`
`Notification` · `ParametresSysteme` · `LogActivite` · `EmailTemplate`

---

## Règles critiques

1. Jamais modifier directement sur le VPS — workflow local → GitHub → `git pull` VPS
2. Jamais committer : `.env`, `venv/`, `static/uploads/`, `*.db`, `.claude/`, `tests/`, `exports/`
3. `DEBUG=False` en production
4. Toute nouvelle route : `@login_required` + `has_permission()`
5. `sign_courrier_action()` avant chaque `db.session.commit()` dans les routes courrier
6. `_SUPER_ADMIN_MAIL_BLOCKED_PERMISSIONS` — INVIOLABLE (6 points de contrôle)

---

## Nouveautés Mai 2026

### Sécurité
- **AES-256-GCM v2** : fichiers chiffrés avec magic `b'GEC2'` + nonce + tag. Backward-compat v1 AES-CBC.
- **Champs DB v2** : préfixe `v2:base64(nonce+tag+ciphertext)`. Fallback v1 = raw base64.
- **Fail-fast** : GEC_MASTER_KEY absente → log CRITICAL + exception (plus de clé volatile en RAM)
- **Bugs B1-B7 fixés** : fichier_encrypted sur CourrierAttachment, validate_file_upload tuple, can_view_courrier sur view_file, @login_required sur /uploads, cleanup fichiers temp, fail-fast master key

### Signature électronique non-répudiation
- **`CourrierActionSignature`** : nouvelle table — hash chain SHA-256 sur toutes les actions courrier
- **`sign_courrier_action()`** dans `utils/helpers.py` — intégrée dans toutes les routes mail
- **Timeline "Historique Signé"** dans `mail_detail_new.html`
- **Route** `GET /api/courrier/<id>/verify_signatures` → `{valid, entries, broken_at}`

### PWA
- `static/manifest.json` + `static/js/sw.js` + icônes SVG 192/512
- Meta tags dans `new_base.html` + registration SW en fin de body

### Skeleton Loading
- Classes CSS dans `design-system.css` : `.gec-skeleton`, `.gec-skeleton-text`, `.gec-skeleton-card`, `.gec-skeleton-row`
- Intégrées dans `dashboard.html`, `view_mail.html`, `mail_detail_new.html`

---

## À FAIRE — Déploiement VPS (⚠️ PAS encore fait)

```bash
ssh vps2
cd /var/websites/gec
git pull origin main
source venv/bin/activate
flask db migrate -m "add courrier_action_signature and fichier_encrypted"
flask db upgrade
pm2 restart gec
curl http://localhost:5004
pm2 logs gec
```

---

## Déploiement VPS 2

```bash
ssh -i ~/.ssh/vps1_access root@168.231.86.201
cd /var/websites/gec
git pull origin main
pm2 restart gec
curl http://localhost:5004
pm2 logs gec
```
