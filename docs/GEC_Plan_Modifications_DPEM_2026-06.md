# Plan d'application — Évolutions GEC (DPEM) — Réf. MOA/CD/KIN/06003/2026

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** Intégrer au logiciel GEC les 6 évolutions demandées par la Direction de Protection de l'Environnement Minier (DPEM) dans la lettre du 18/06/2026, sans régression sur l'existant (sécurité AES-GCM, RBAC, signature de non-répudiation).

**Architecture :** Application Flask monolithique existante (routes plates dans `routes/`, modèles SQLAlchemy dans `models/`, templates Jinja dans `templates/`). Les évolutions s'ajoutent en **colonnes** sur les tables `courrier` et `courrier_comment` (aucune nouvelle table), en **permissions** dans le catalogue RBAC, et en **routes/vues** additionnelles. Le mécanisme de migration maison `utils/migrations.py::run_automatic_migrations()` (exécuté au démarrage, dev **et** prod) est la voie officielle d'ajout de colonnes.

**Tech Stack :** Python 3.11 · Flask 3.1 · SQLAlchemy 2.0 · Flask-Login · Flask-WTF (CSRF) · Tailwind (vendor local) · `qrcode[pil]==8.0` (déjà installé) · ReportLab · pytest.

---

## Note métier (lettre MOA/CD/KIN/06003/2026)

- **Faisabilité confirmée**, délai annoncé au client : **1 semaine**.
- Évolutions **offertes sans frais supplémentaire**.
- ⚠️ **Démarrage subordonné au paiement complet de la facture** de la livraison GEC déjà réceptionnée. **Ce plan est prêt ; l'exécution ne démarre qu'après régularisation.**

---

## Global Constraints

Chaque tâche hérite implicitement de ces règles (copiées du `CLAUDE.md` projet et du primer) :

- **Jamais modifier directement sur le VPS** — workflow local → PR GitHub → `git pull` VPS → `pm2 restart gec`. **Jamais push sur `main`** — toujours une PR.
- **Jamais committer** : `.env`, `venv/`, `static/uploads/`, `*.db`, `.claude/`, `tests/`, `exports/`.
- **`DEBUG=False` en production.** `GEC_MASTER_KEY` obligatoire (fail-fast au démarrage).
- **Toute route mutante sur un courrier** : `@login_required` + garde `can_view_courrier` / `can_edit_courrier` / `can_access_courrier` (anti-IDOR) + `sign_courrier_action(courrier.id, current_user, '<ACTION>', {...})` **avant** `db.session.commit()` + `log_activity(...)`.
- **RÈGLE INVIOLABLE** : `super_admin` n'accède jamais au courrier (`_SUPER_ADMIN_MAIL_BLOCKED_PERMISSIONS` dans `models/user.py`). Les nouvelles permissions courrier y sont ajoutées.
- **Pièces jointes** : `validate_file_upload()` → `encrypt_uploaded_file()` → téléchargement via fichier temp déchiffré avec `try: send_file(temp) finally: os.unlink(temp)`. Extensions autorisées = `ALLOWED_EXTENSIONS = {"pdf","png","jpg","jpeg","tiff","tif"}` (`utils/helpers.py:9`).
- **Migrations** : ajouter les colonnes dans `run_automatic_migrations()` (idempotent via `add_column_safely`). Ne pas casser la compat SQLite (dev) / PostgreSQL (prod).
- **i18n** : toute chaîne UI nouvelle → `lang/fr.json` **et** `lang/en.json`.
- **Après chaque modification UI** : `/validate-and-push` (captures Playwright desktop + mobile) puis STOP validation utilisateur avant PR.
- **Environnement de test (macOS)** : le `venv/` versionné est un venv Windows inutilisable ; utiliser l'interpréteur **`./.venv/bin/python`** (Python 3.13, dépendances installées). Lancer les tests via `./.venv/bin/python -m pytest ...` (ignorer les `source venv/bin/activate` des étapes). Le projet utilise une syntaxe f-string Python 3.12+ (backslashes) — ne pas rétrograder en 3.11. Baseline avant chantier : **15 passed / 6 failed pré-existants / 4 skipped** — ne pas régresser les 15 qui passent ; les 6 échecs pré-existants (chemins obsolètes, `admin_client`=super_admin bloqué) sont hors périmètre.

---

## Cartographie des fichiers touchés

| Fichier | Rôle dans ce chantier |
|---------|------------------------|
| `models/courrier.py` | Colonnes `Courrier.courrier_parent_id`, `Courrier.numero_suivi` + relation `reponses` ; colonnes PJ sur `CourrierComment` ; nouveaux types dans `CourrierActionSignature.ACTIONS` / `BADGE_COLORS` |
| `models/user.py` | Ajout des 2 nouvelles permissions à `_SUPER_ADMIN_MAIL_BLOCKED_PERMISSIONS` |
| `utils/migrations.py` | Bloc « Migration 17 : évolutions DPEM » (colonnes + backfill `numero_suivi`) |
| `utils/helpers.py` | Nouveau `generate_numero_suivi()` ; helper `qr_data_uri()` |
| `utils/__init__.py` | Export de `generate_numero_suivi` |
| `routes/admin.py` | 2 entrées dans `PERMISSIONS_CATALOG` (`add_director_annotation`, `edit_registration_date`) |
| `routes/mail.py` | #1 statut figé (`register_mail`) ; #3 upload PJ + route download (`add_comment`, nouvelle route) ; #2 annotation Directeur (`add_comment`) ; #4 pré-remplissage + lien parent (`register_mail`) ; #6 attribution `numero_suivi` + route `/courrier/<id>/etiquette` ; recherche par `numero_suivi` |
| `routes/search.py` | Recherche par `numero_suivi` (filtre) |
| `templates/register_mail.html` | #1 statut lecture seule ; #4 champs pré-remplis + `parent_id` caché |
| `templates/mail_detail_new.html` | #2 bloc « Annotation du Directeur » ; #3 input fichier + `enctype` + affichage PJ ; #4 bouton « Générer réponse » + cross-lien ; #6 bouton « Étiquette » |
| `templates/edit_courrier.html` | #5 champ conditionnel `date_enregistrement` |
| `templates/etiquette_courrier.html` | **Créé** — étiquette imprimable (numéro de suivi + QR) |
| `app.py` | Appel idempotent `ensure_dpem_permissions()` au boot (défaut `edit_registration_date` → admin) |
| `lang/fr.json`, `lang/en.json` | Nouvelles chaînes |
| `tests/test_dpem_evolutions.py` | **Créé** — tests des 6 évolutions |

**Note sur le harnais de test :** la suite existante authentifie via `admin_client` (rôle `super_admin`), **qui est bloqué du courrier**. Tous les tests de ce chantier utilisent `user_client` (rôle `user`, propriétaire du courrier) et, pour les cas gated, un helper `_role_with_perms()` qui sème un `Role` + `RolePermission` réels (le `has_permission()` retombe sinon sur un dict codé en dur qui ignore les nouvelles permissions).

---

## Task 1 : Couche de données & fondations transversales

**Files :**
- Modify: `models/courrier.py` (classe `Courrier` ~L8-51, `CourrierComment` ~L239-258, `CourrierActionSignature.ACTIONS` L323-338 et `BADGE_COLORS` L357-363)
- Modify: `models/user.py` (`_SUPER_ADMIN_MAIL_BLOCKED_PERMISSIONS`)
- Modify: `utils/migrations.py` (fin de `run_automatic_migrations`, avant le bloc `if migrations_applied > 0`)
- Modify: `utils/helpers.py` (ajout `generate_numero_suivi`, `qr_data_uri`) + `utils/__init__.py` (export)
- Modify: `routes/admin.py` (`PERMISSIONS_CATALOG`)
- Test: `tests/test_dpem_evolutions.py`

**Interfaces :**
- Produces: `Courrier.courrier_parent_id` (int, FK `courrier.id`, nullable), `Courrier.numero_suivi` (str, unique, nullable), `Courrier.reponses` (backref liste), `Courrier.parent` (relationship) ; colonnes `CourrierComment.fichier_nom/fichier_chemin/fichier_type/fichier_taille/fichier_encrypted` ; `generate_numero_suivi() -> str` (format `SUIVI-{year}-{counter:05d}`, unique) ; `qr_data_uri(text: str) -> str` (data URI PNG) ; permissions `add_director_annotation`, `edit_registration_date` ; action types `ANNOTATION_DIRECTEUR`, `MODIF_DATE_ENREG`, `GEN_SORTANT`.

- [ ] **Step 1 : Écrire le test qui échoue (colonnes + générateur)**

Créer `tests/test_dpem_evolutions.py` :

```python
"""Tests des 6 évolutions DPEM (Réf. MOA/CD/KIN/06003/2026)."""
import io
import re
import pytest


def _pdf_bytes():
    return b"%PDF-1.4 1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"


def _png_bytes():
    # PNG 1x1 valide (magic bytes reconnus par validate_file_upload)
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42m\n"
        "NkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )


def _role_with_perms(app, db, nom, perms, niveau=30, username=None):
    """Sème un Role réel + ses RolePermission, et (optionnel) un User portant ce rôle."""
    from models import Role, RolePermission, User
    with app.app_context():
        r = Role.query.filter_by(nom=nom).first()
        if not r:
            r = Role(nom=nom, nom_affichage=nom.title(), niveau=niveau)
            db.session.add(r)
            db.session.flush()
        for p in perms:
            if not RolePermission.query.filter_by(role_id=r.id, permission_nom=p).first():
                db.session.add(RolePermission(role_id=r.id, permission_nom=p))
        uid = None
        if username:
            u = User.query.filter_by(username=username).first()
            if not u:
                from werkzeug.security import generate_password_hash
                u = User(username=username, email=f"{username}@test.com",
                         nom_complet=username.title(), role=nom, actif=True,
                         password_hash=generate_password_hash("Pass123!"))
                db.session.add(u)
            else:
                u.role = nom
            db.session.flush()
            uid = u.id
        db.session.commit()
        return uid


def _login(app, client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


class TestFoundations:
    def test_courrier_has_new_columns(self, app):
        from models import Courrier
        cols = {c.name for c in Courrier.__table__.columns}
        assert {"courrier_parent_id", "numero_suivi"} <= cols

    def test_comment_has_attachment_columns(self, app):
        from models import CourrierComment
        cols = {c.name for c in CourrierComment.__table__.columns}
        assert {"fichier_nom", "fichier_chemin", "fichier_type",
                "fichier_taille", "fichier_encrypted"} <= cols

    def test_generate_numero_suivi_format_and_unique(self, app):
        from utils.helpers import generate_numero_suivi
        with app.app_context():
            n1 = generate_numero_suivi()
            assert re.match(r"^SUIVI-\d{4}-\d{5}$", n1)

    def test_new_permissions_in_catalog(self, app):
        from routes.admin import PERMISSIONS_CATALOG
        assert "add_director_annotation" in PERMISSIONS_CATALOG
        assert "edit_registration_date" in PERMISSIONS_CATALOG
```

- [ ] **Step 2 : Lancer le test → échec attendu**

Run: `cd gec && source venv/bin/activate && python -m pytest tests/test_dpem_evolutions.py::TestFoundations -v`
Expected: FAIL (`courrier_parent_id` absent, `generate_numero_suivi` inexistant, permissions absentes).

- [ ] **Step 3 : Ajouter les colonnes modèles**

Dans `models/courrier.py`, classe `Courrier`, après `modifie_par_id` (~L46) :

```python
    # Évolutions DPEM (juin 2026)
    courrier_parent_id = db.Column(db.Integer, db.ForeignKey('courrier.id'), nullable=True, index=True)
    numero_suivi = db.Column(db.String(50), unique=True, nullable=True, index=True)

    reponses = db.relationship(
        'Courrier',
        backref=db.backref('parent', remote_side=[id]),
        foreign_keys=[courrier_parent_id],
    )
```

Dans `models/courrier.py`, classe `CourrierComment`, après `actif` (~L251) :

```python
    # Pièce jointe (PDF/image) — évolution DPEM #3
    fichier_nom = db.Column(db.String(255), nullable=True)
    fichier_chemin = db.Column(db.String(500), nullable=True)
    fichier_type = db.Column(db.String(50), nullable=True)
    fichier_taille = db.Column(db.Integer, nullable=True)
    fichier_encrypted = db.Column(db.Boolean, default=False, nullable=False)
```

Dans `CourrierActionSignature.ACTIONS` (L323-338), ajouter 3 entrées :

```python
        'ANNOTATION_DIRECTEUR': ('fas fa-user-tie', 'text-amber-700', 'Annotation du Directeur'),
        'MODIF_DATE_ENREG':     ('fas fa-calendar-day', 'text-blue-600', "Modification date d'enregistrement"),
        'GEN_SORTANT':          ('fas fa-reply', 'text-purple-600', 'Courrier sortant lié généré'),
```

Dans `BADGE_COLORS` (L357-363), ajouter :

```python
        'ANNOTATION_DIRECTEUR': 'yellow', 'MODIF_DATE_ENREG': 'blue', 'GEN_SORTANT': 'blue',
```

- [ ] **Step 4 : Ajouter les colonnes à la migration auto**

Dans `utils/migrations.py`, dans `run_automatic_migrations`, **juste avant** `if migrations_applied > 0:` (~L371), insérer :

```python
        # Migration 17 : Évolutions DPEM (Réf. MOA/CD/KIN/06003/2026)
        dpem_columns = [
            ('courrier_comment', 'fichier_nom', 'VARCHAR(255)'),
            ('courrier_comment', 'fichier_chemin', 'VARCHAR(500)'),
            ('courrier_comment', 'fichier_type', 'VARCHAR(50)'),
            ('courrier_comment', 'fichier_taille', 'INTEGER'),
            ('courrier_comment', 'fichier_encrypted', 'BOOLEAN DEFAULT FALSE'),
            ('courrier', 'courrier_parent_id', 'INTEGER'),
            ('courrier', 'numero_suivi', 'VARCHAR(50)'),
        ]
        for table, col, defn in dpem_columns:
            if add_column_safely(engine, table, col, defn):
                migrations_applied += 1
                logging.info(f"✓ Migration 17 (DPEM): Colonne {col} ajoutée à {table}")

        # Backfill numero_suivi pour les courriers existants (idempotent)
        try:
            from models import Courrier
            from utils.helpers import generate_numero_suivi
            sans_suivi = Courrier.query.filter(
                (Courrier.numero_suivi.is_(None)) | (Courrier.numero_suivi == '')
            ).all()
            for c in sans_suivi:
                c.numero_suivi = generate_numero_suivi()
            if sans_suivi:
                db.session.commit()
                logging.info(f"✓ Migration 17 (DPEM): {len(sans_suivi)} numéro(s) de suivi backfillé(s)")
        except Exception as e:
            db.session.rollback()
            logging.warning(f"Backfill numero_suivi ignoré : {e}")
```

- [ ] **Step 5 : Ajouter `generate_numero_suivi()` et `qr_data_uri()`**

Dans `utils/helpers.py`, après `generate_accuse_reception()` (~L322) :

```python
def generate_numero_suivi():
    """Numéro de suivi court et unique d'un dossier (étiquette). Format: SUIVI-{year}-{counter:05d}."""
    from models import Courrier
    now = datetime.now()
    try:
        counter = Courrier.query.filter(
            Courrier.date_enregistrement >= datetime(now.year, 1, 1)
        ).count() + 1
    except Exception:
        counter = 1
    # Garantir l'unicité (backfill / concurrence)
    while True:
        candidate = f"SUIVI-{now.year}-{counter:05d}"
        if not Courrier.query.filter_by(numero_suivi=candidate).first():
            return candidate
        counter += 1


def qr_data_uri(text):
    """Retourne un QR code (PNG, data URI base64) encodant `text` en clair."""
    import io, base64
    import qrcode
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')
```

Dans `utils/__init__.py`, ajouter `generate_numero_suivi` (et `qr_data_uri` si l'`__init__` réexporte les helpers) à la liste des symboles importés/exportés depuis `utils.helpers`.

- [ ] **Step 6 : Déclarer les permissions dans le catalogue RBAC**

Dans `routes/admin.py`, dans `PERMISSIONS_CATALOG` (après L53, catégorie « Édition Courrier ») :

```python
    'add_director_annotation': {'name': 'Annotation du Directeur',        'description': "Poser l'annotation unique du Directeur sur un courrier",         'category': 'Courrier'},
    'edit_registration_date':  {'name': "Modifier la date d'enregistrement", 'description': "Modifier manuellement la date d'enregistrement d'un courrier", 'category': 'Édition Courrier'},
```

Dans `models/user.py`, ajouter les deux permissions au frozenset `_SUPER_ADMIN_MAIL_BLOCKED_PERMISSIONS` (garder le super_admin exclu du courrier) :

```python
    'add_director_annotation',
    'edit_registration_date',
```

- [ ] **Step 7 : Lancer les tests → succès attendu**

Run: `python -m pytest tests/test_dpem_evolutions.py::TestFoundations -v`
Expected: PASS (4 tests).

- [ ] **Step 8 : Commit**

```bash
git add models/courrier.py models/user.py utils/migrations.py utils/helpers.py utils/__init__.py routes/admin.py tests/test_dpem_evolutions.py
git commit -m "feat(dpem): fondations — colonnes courrier/comment, numero_suivi, permissions RBAC"
```

---

## Task 2 : Évolution #1 — Statut figé à l'enregistrement

Un seul statut initial (`RECU`) est assigné à l'enregistrement ; les statuts suivants restent gérés par `change_status()` / `edit_courrier()` (traitement par les autres agents). Aucun changement de modèle.

**Files :**
- Modify: `routes/mail.py` (`register_mail`, ligne `statut = request.form.get('statut', 'RECU')` → L47)
- Modify: `templates/register_mail.html` (bloc `<select name="statut">` L121-137)
- Test: `tests/test_dpem_evolutions.py`

**Interfaces :**
- Consumes: modèle `Courrier` (Task 1). Produces: constante `STATUT_INITIAL = 'RECU'` dans `routes/mail.py`.

- [ ] **Step 1 : Écrire le test qui échoue**

Ajouter à `tests/test_dpem_evolutions.py` :

```python
class TestStatutFige:
    def test_statut_force_recu_meme_si_autre_soumis(self, app, client):
        from models import User, Courrier
        uid = _role_with_perms(app, db=_db(), nom="agent_saisie",
                               perms=["register_mail", "read_own_mail"],
                               username="agent1")
        _login(app, client, uid)
        data = {
            "objet": "Courrier statut force",
            "type_courrier": "ENTRANT",
            "expediteur": "Exp Test",
            "secretaire_general_copie": "Non",
            "statut": "TRAITE",  # tentative de forcer un autre statut
            "fichier": (io.BytesIO(_pdf_bytes()), "s.pdf"),
        }
        client.post("/register_mail", data=data,
                    content_type="multipart/form-data", follow_redirects=True)
        with app.app_context():
            c = Courrier.query.filter_by(objet="Courrier statut force").first()
            assert c is not None
            assert c.statut == "RECU"  # ignoré → RECU imposé
```

Ajouter en haut du fichier un helper d'accès au `db` :

```python
def _db():
    from app import db
    return db
```

- [ ] **Step 2 : Lancer → échec attendu**

Run: `python -m pytest tests/test_dpem_evolutions.py::TestStatutFige -v`
Expected: FAIL (statut = "TRAITE").

- [ ] **Step 3 : Forcer le statut initial côté serveur**

Dans `routes/mail.py`, en tête de module (près des imports), ajouter :

```python
STATUT_INITIAL = 'RECU'  # Évolution DPEM #1 : statut imposé à l'enregistrement
```

Dans `register_mail()`, remplacer la ligne 47 :

```python
        statut = request.form.get('statut', 'RECU')
```

par :

```python
        # Évolution DPEM #1 : le statut n'est plus choisi à l'enregistrement.
        statut = STATUT_INITIAL
```

(Le reste de la fonction utilise déjà `statut=statut` à la création — inchangé.)

- [ ] **Step 4 : Neutraliser le sélecteur dans le formulaire**

Dans `templates/register_mail.html`, remplacer le bloc `<label ...>Statut Initial</label> <select ...>…</select>` (L121-137) par un affichage lecture seule :

```html
            <label class="gec-label"><i class="fas fa-flag" style="color:var(--primary);font-size:.75rem;"></i> Statut initial</label>
            <div class="gec-input" style="display:flex;align-items:center;gap:.5rem;background:rgba(0,0,0,.03);">
              <span class="gec-badge gec-badge-blue">RECU</span>
              <span class="gec-form-hint" style="margin:0;">Assigné automatiquement — les statuts suivants sont attribués lors du traitement.</span>
            </div>
```

(Aucun `name="statut"` n'est plus soumis ; le serveur impose `RECU`.)

- [ ] **Step 5 : Lancer → succès attendu**

Run: `python -m pytest tests/test_dpem_evolutions.py::TestStatutFige -v`
Expected: PASS.

- [ ] **Step 6 : Commit**

```bash
git add routes/mail.py templates/register_mail.html tests/test_dpem_evolutions.py
git commit -m "feat(dpem #1): statut initial RECU imposé à l'enregistrement"
```

---

## Task 3 : Évolution #6 — Numéro de suivi + étiquette QR

Attribuer `numero_suivi` à la création ; produire une étiquette imprimable (numéro de suivi + QR encodant **le numéro de suivi en texte brut**, choix retenu) ; rendre le dossier retrouvable par scan (recherche sur `numero_suivi`).

**Files :**
- Modify: `routes/mail.py` (`register_mail` création du `Courrier` ~L180-197 ; nouvelle route `etiquette_courrier`)
- Create: `templates/etiquette_courrier.html`
- Modify: `templates/mail_detail_new.html` (bouton « Étiquette »)
- Modify: `routes/search.py` (filtre `numero_suivi`)
- Test: `tests/test_dpem_evolutions.py`

**Interfaces :**
- Consumes: `generate_numero_suivi()`, `qr_data_uri()` (Task 1). Produces: route `GET /courrier/<int:id>/etiquette`.

- [ ] **Step 1 : Écrire le test qui échoue**

```python
class TestNumeroSuivi:
    def _create(self, app, client):
        from models import Courrier
        uid = _role_with_perms(app, _db(), "agent_suivi",
                               ["register_mail", "read_own_mail"], username="agent_suivi_u")
        _login(app, client, uid)
        client.post("/register_mail", data={
            "objet": "Courrier avec suivi", "type_courrier": "ENTRANT",
            "expediteur": "Exp", "secretaire_general_copie": "Non",
            "fichier": (io.BytesIO(_pdf_bytes()), "x.pdf"),
        }, content_type="multipart/form-data", follow_redirects=True)
        with app.app_context():
            return Courrier.query.filter_by(objet="Courrier avec suivi").first()

    def test_numero_suivi_assigned_on_create(self, app, client):
        c = self._create(app, client)
        assert c.numero_suivi and c.numero_suivi.startswith("SUIVI-")

    def test_etiquette_page_renders_qr(self, app, client):
        c = self._create(app, client)
        resp = client.get(f"/courrier/{c.id}/etiquette")
        assert resp.status_code == 200
        body = resp.data.decode()
        assert c.numero_suivi in body
        assert "data:image/png;base64," in body  # QR inline
```

- [ ] **Step 2 : Lancer → échec attendu**

Run: `python -m pytest tests/test_dpem_evolutions.py::TestNumeroSuivi -v`
Expected: FAIL (`numero_suivi` None ; route 404).

- [ ] **Step 3 : Attribuer `numero_suivi` à la création**

Dans `routes/mail.py`, importer le helper en tête de fichier (ajouter à l'import `from utils import ...`) : `generate_numero_suivi`, `qr_data_uri`.

Dans `register_mail()`, à la construction du `Courrier(...)` (~L180), ajouter l'argument :

```python
            numero_suivi=generate_numero_suivi(),
```

- [ ] **Step 4 : Ajouter la route étiquette**

Dans `routes/mail.py`, après `mail_detail` (ou près de `download_file`) :

```python
@app.route('/courrier/<int:id>/etiquette')
@login_required
def etiquette_courrier(id):
    """Étiquette imprimable (numéro de suivi + QR code) à apposer sur le document."""
    courrier = Courrier.query.get_or_404(id)
    if not current_user.can_view_courrier(courrier):
        abort(403)
    if not courrier.numero_suivi:
        courrier.numero_suivi = generate_numero_suivi()
        db.session.commit()
    qr = qr_data_uri(courrier.numero_suivi)  # QR = numéro de suivi en clair
    log_activity(current_user.id, "GENERATION_ETIQUETTE",
                 f"Étiquette générée pour {courrier.numero_accuse_reception}", courrier.id)
    return render_template('etiquette_courrier.html', courrier=courrier, qr=qr)
```

- [ ] **Step 5 : Créer le template `templates/etiquette_courrier.html`**

```html
{% extends "new_base.html" %}
{% block content %}
<div class="etq-wrap">
  <div class="etq-card">
    <div class="etq-head">
      <span class="etq-org">{{ parametres.nom_logiciel if parametres else 'GEC' }}</span>
      <span class="etq-title">Étiquette de suivi</span>
    </div>
    <div class="etq-body">
      <img class="etq-qr" src="{{ qr }}" alt="QR {{ courrier.numero_suivi }}">
      <div class="etq-meta">
        <div class="etq-suivi">{{ courrier.numero_suivi }}</div>
        <div class="etq-line"><b>Accusé :</b> {{ courrier.numero_accuse_reception }}</div>
        <div class="etq-line"><b>Objet :</b> {{ courrier.objet[:60] }}</div>
        <div class="etq-line"><b>Date :</b> {{ courrier.date_enregistrement.strftime('%d/%m/%Y') if courrier.date_enregistrement }}</div>
      </div>
    </div>
    <button class="gec-btn gec-btn-primary etq-print" onclick="window.print()"><i class="fas fa-print"></i> Imprimer</button>
  </div>
</div>
<style>
  .etq-wrap{display:flex;justify-content:center;padding:2rem;}
  .etq-card{border:1px solid #d1d5db;border-radius:12px;padding:1rem 1.25rem;width:340px;background:#fff;color:#111;}
  .etq-head{display:flex;flex-direction:column;border-bottom:1px dashed #cbd5e1;padding-bottom:.5rem;margin-bottom:.75rem;}
  .etq-org{font-weight:700;font-size:.8rem;color:#2563eb;}
  .etq-title{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:#6b7280;}
  .etq-body{display:flex;gap:.9rem;align-items:center;}
  .etq-qr{width:120px;height:120px;}
  .etq-suivi{font-size:1.05rem;font-weight:800;letter-spacing:.02em;margin-bottom:.4rem;}
  .etq-line{font-size:.72rem;color:#374151;margin:.1rem 0;}
  .etq-print{margin-top:.9rem;width:100%;}
  @media print{.etq-print,.gec-sidebar,.gec-topbar{display:none!important;} .etq-wrap{padding:0;}}
</style>
{% endblock %}
```

(Passer `parametres` au template si `new_base.html` ne l'expose pas déjà via context_processor ; sinon retirer la ligne `nom_logiciel`.)

- [ ] **Step 6 : Bouton « Étiquette » dans le détail**

Dans `templates/mail_detail_new.html`, dans la barre d'actions (près du bouton de transmission ~L711), ajouter :

```html
<a href="{{ url_for('etiquette_courrier', id=courrier.id) }}" target="_blank" class="gec-btn gec-btn-secondary">
  <i class="fas fa-qrcode"></i> Étiquette
</a>
```

- [ ] **Step 7 : Recherche par numéro de suivi**

Dans `routes/search.py`, là où la clause `or_(...)` filtre sur `numero_accuse_reception` / `numero_reference`, ajouter la condition `Courrier.numero_suivi.ilike(f"%{search}%")`. (Idem dans `view_mail` de `routes/mail.py` si un champ de recherche y filtre les colonnes — reprendre le même `or_`.)

- [ ] **Step 8 : Lancer → succès attendu**

Run: `python -m pytest tests/test_dpem_evolutions.py::TestNumeroSuivi -v`
Expected: PASS.

- [ ] **Step 9 : Commit**

```bash
git add routes/mail.py routes/search.py templates/etiquette_courrier.html templates/mail_detail_new.html tests/test_dpem_evolutions.py
git commit -m "feat(dpem #6): numero_suivi + étiquette imprimable QR + recherche"
```

---

## Task 4 : Évolution #3 — Pièce jointe (PDF/image) sur commentaires & annotations

**Files :**
- Modify: `routes/mail.py` (`add_comment` ~L1600-1719 ; nouvelle route `download_comment_attachment`)
- Modify: `templates/mail_detail_new.html` (form L446 : ajout `enctype` + input fichier ; affichage PJ dans le fil L479+)
- Test: `tests/test_dpem_evolutions.py`

**Interfaces :**
- Consumes: colonnes PJ de `CourrierComment` (Task 1), `validate_file_upload`, `encrypt_uploaded_file`, `decrypt_file_for_download`. Produces: route `GET /download_comment_attachment/<int:comment_id>`.

- [ ] **Step 1 : Écrire le test qui échoue**

```python
class TestCommentAttachment:
    def _make_courrier_and_login(self, app, client):
        from models import Courrier
        uid = _role_with_perms(app, _db(), "agent_pj",
                               ["register_mail", "read_own_mail"], username="agent_pj_u")
        _login(app, client, uid)
        client.post("/register_mail", data={
            "objet": "Courrier PJ commentaire", "type_courrier": "ENTRANT",
            "expediteur": "Exp", "secretaire_general_copie": "Non",
            "fichier": (io.BytesIO(_pdf_bytes()), "base.pdf"),
        }, content_type="multipart/form-data", follow_redirects=True)
        with app.app_context():
            return Courrier.query.filter_by(objet="Courrier PJ commentaire").first().id

    def test_comment_with_attachment_saved(self, app, client):
        from models import CourrierComment
        cid = self._make_courrier_and_login(app, client)
        client.post(f"/add_comment/{cid}", data={
            "commentaire": "Voir pièce jointe", "type_comment": "annotation",
            "piece_jointe": (io.BytesIO(_png_bytes()), "preuve.png"),
        }, content_type="multipart/form-data", follow_redirects=True)
        with app.app_context():
            com = CourrierComment.query.filter_by(courrier_id=cid).first()
            assert com is not None
            assert com.fichier_nom == "preuve.png"
            assert com.fichier_chemin

    def test_download_comment_attachment_requires_view(self, app, client):
        # Un utilisateur tiers sans accès au courrier => 403
        from models import CourrierComment
        cid = self._make_courrier_and_login(app, client)
        client.post(f"/add_comment/{cid}", data={
            "commentaire": "PJ", "type_comment": "comment",
            "piece_jointe": (io.BytesIO(_png_bytes()), "p.png"),
        }, content_type="multipart/form-data", follow_redirects=True)
        with app.app_context():
            com_id = CourrierComment.query.filter_by(courrier_id=cid).first().id
        other = app.test_client()
        intrus = _role_with_perms(app, _db(), "intrus", ["read_own_mail"], username="intrus_u")
        _login(app, other, intrus)
        resp = other.get(f"/download_comment_attachment/{com_id}", follow_redirects=False)
        assert resp.status_code in (403, 302)
```

- [ ] **Step 2 : Lancer → échec attendu**

Run: `python -m pytest tests/test_dpem_evolutions.py::TestCommentAttachment -v`
Expected: FAIL (colonnes non renseignées ; route download 404).

- [ ] **Step 3 : Gérer l'upload dans `add_comment`**

Dans `routes/mail.py::add_comment`, après la création de l'objet `comment` (~L1624) et **avant** `db.session.add(comment)`, insérer le traitement fichier :

```python
    # Évolution DPEM #3 : pièce jointe (PDF/image) sur commentaire/annotation
    pj = request.files.get('piece_jointe')
    if pj and pj.filename:
        ext = pj.filename.rsplit('.', 1)[-1].lower() if '.' in pj.filename else ''
        if ext not in {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif'}:
            flash('Pièce jointe refusée : seuls les fichiers PDF ou image sont acceptés.', 'error')
            return redirect(url_for('mail_detail', id=courrier_id))
        is_valid_pj, msg_pj = validate_file_upload(pj)
        if not is_valid_pj:
            flash(f'Pièce jointe refusée : {msg_pj}', 'error')
            return redirect(url_for('mail_detail', id=courrier_id))
        pj_name = secure_filename(pj.filename)
        pj_ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        pj_stored = f"{pj_ts}_{pj_name}"
        pj_path = os.path.join('uploads', pj_stored)
        os.makedirs('uploads', exist_ok=True)
        pj.seek(0)
        pj.save(pj_path)
        pj_encrypted = False
        try:
            enc = encrypt_uploaded_file(pj_path)
            if enc:
                pj_path = enc
                pj_encrypted = True
        except Exception as e_pj:
            logging.warning(f"Chiffrement PJ commentaire ignoré : {e_pj}")
        comment.fichier_nom = pj.filename
        comment.fichier_chemin = pj_path
        comment.fichier_type = pj_stored.rsplit('.', 1)[-1].lower()
        comment.fichier_taille = os.path.getsize(pj_path)
        comment.fichier_encrypted = pj_encrypted
```

Vérifier que `encrypt_uploaded_file` est bien importé dans `routes/mail.py` (via `from security import ...`) ; sinon l'ajouter.

- [ ] **Step 4 : Ajouter la route de téléchargement sécurisée**

Dans `routes/mail.py`, après `download_forward_attachment` :

```python
@app.route('/download_comment_attachment/<int:comment_id>')
@login_required
def download_comment_attachment(comment_id):
    """Télécharger la pièce jointe d'un commentaire/annotation (déchiffrée à la volée)."""
    comment = CourrierComment.query.get_or_404(comment_id)
    courrier = Courrier.query.get_or_404(comment.courrier_id)
    if not current_user.can_view_courrier(courrier):
        abort(403)
    if not comment.fichier_chemin:
        flash('Aucune pièce jointe pour ce commentaire.', 'error')
        return redirect(url_for('mail_detail', id=comment.courrier_id))
    log_activity(current_user.id, "DOWNLOAD_PJ_COMMENTAIRE",
                 f"Téléchargement PJ commentaire {comment_id}", comment.courrier_id)
    if comment.fichier_encrypted:
        temp_path = decrypt_file_for_download(comment.fichier_chemin)
        try:
            return send_file(temp_path, as_attachment=True, download_name=comment.fichier_nom)
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    return send_file(comment.fichier_chemin, as_attachment=True, download_name=comment.fichier_nom)
```

Vérifier l'import de `decrypt_file_for_download` (`from security import decrypt_file_for_download`).

- [ ] **Step 5 : Formulaire + affichage template**

Dans `templates/mail_detail_new.html` :
- Sur le `<form ... action="{{ url_for('add_comment', ...) }}">` (L446), ajouter `enctype="multipart/form-data"`.
- Sous le `<textarea>` du commentaire, ajouter :

```html
<div class="gec-form-group">
  <label class="gec-label" for="piece_jointe"><i class="fas fa-paperclip"></i> Pièce jointe (PDF ou image, optionnel)</label>
  <input type="file" id="piece_jointe" name="piece_jointe" accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif" class="gec-input">
</div>
```

- Dans la boucle d'affichage des commentaires (près L479-482), après le texte du commentaire, ajouter le lien PJ :

```html
{% if comment.fichier_nom %}
<a href="{{ url_for('download_comment_attachment', comment_id=comment.id) }}" class="gec-link" style="font-size:.72rem;">
  <i class="fas fa-paperclip"></i> {{ comment.fichier_nom }}
</a>
{% endif %}
```

- [ ] **Step 6 : Lancer → succès attendu**

Run: `python -m pytest tests/test_dpem_evolutions.py::TestCommentAttachment -v`
Expected: PASS.

- [ ] **Step 7 : Commit**

```bash
git add routes/mail.py templates/mail_detail_new.html tests/test_dpem_evolutions.py
git commit -m "feat(dpem #3): pièce jointe PDF/image sur commentaires et annotations (chiffrée, anti-IDOR)"
```

---

## Task 5 : Évolution #2 — Annotation du Directeur (unique, permission dédiée)

Nouveau `type_comment='annotation_directeur'`. Réservé aux porteurs de la permission `add_director_annotation`. **Une seule** annotation Directeur active par courrier (si elle existe, on la met à jour). Affichage dans un bloc distinct.

**Files :**
- Modify: `routes/mail.py` (`add_comment` : gating + unicité + action signée)
- Modify: `templates/mail_detail_new.html` (option de type conditionnelle + bloc dédié)
- Test: `tests/test_dpem_evolutions.py`

**Interfaces :**
- Consumes: permission `add_director_annotation` (Task 1), colonnes PJ (Task 4 — l'annotation Directeur peut aussi porter une PJ). Produces: valeur `type_comment == 'annotation_directeur'` (unique par courrier).

- [ ] **Step 1 : Écrire le test qui échoue**

```python
class TestAnnotationDirecteur:
    def _courrier_owned_by(self, app, role, perms, username):
        from models import Courrier
        client = _db_app_client()  # voir helper ci-dessous
        uid = _role_with_perms(app, _db(), role, perms, username=username)
        _login(app, client, uid)
        client.post("/register_mail", data={
            "objet": f"Courrier {username}", "type_courrier": "ENTRANT",
            "expediteur": "Exp", "secretaire_general_copie": "Non",
            "fichier": (io.BytesIO(_pdf_bytes()), "b.pdf"),
        }, content_type="multipart/form-data", follow_redirects=True)
        with app.app_context():
            cid = Courrier.query.filter_by(objet=f"Courrier {username}").first().id
        return client, cid

    def test_sans_permission_refuse(self, app):
        client, cid = self._courrier_owned_by(
            app, "agent_simple", ["register_mail", "read_own_mail"], "simple_u")
        from models import CourrierComment
        client.post(f"/add_comment/{cid}", data={
            "commentaire": "Décision", "type_comment": "annotation_directeur",
        }, follow_redirects=True)
        with app.app_context():
            assert CourrierComment.query.filter_by(
                courrier_id=cid, type_comment="annotation_directeur").count() == 0

    def test_avec_permission_unique(self, app):
        client, cid = self._courrier_owned_by(
            app, "directeur", ["register_mail", "read_all_mail", "add_director_annotation"], "dir_u")
        from models import CourrierComment
        for txt in ("Première décision", "Décision corrigée"):
            client.post(f"/add_comment/{cid}", data={
                "commentaire": txt, "type_comment": "annotation_directeur",
            }, follow_redirects=True)
        with app.app_context():
            q = CourrierComment.query.filter_by(
                courrier_id=cid, type_comment="annotation_directeur", actif=True)
            assert q.count() == 1                     # unique
            assert q.first().commentaire == "Décision corrigée"  # mise à jour
```

Ajouter le helper `_db_app_client` en haut du fichier :

```python
def _db_app_client():
    from app import app as flask_app
    return flask_app.test_client()
```

- [ ] **Step 2 : Lancer → échec attendu**

Run: `python -m pytest tests/test_dpem_evolutions.py::TestAnnotationDirecteur -v`
Expected: FAIL (pas de gating ni d'unicité).

- [ ] **Step 3 : Gating + unicité dans `add_comment`**

Dans `routes/mail.py::add_comment`, juste après la lecture de `type_comment` (~L1612) et **avant** la création du `comment` :

```python
    # Évolution DPEM #2 : Annotation du Directeur — permission dédiée + unicité
    if type_comment == 'annotation_directeur':
        if not current_user.has_permission('add_director_annotation'):
            flash("Vous n'êtes pas autorisé à poser l'annotation du Directeur.", 'error')
            return redirect(url_for('mail_detail', id=courrier_id))
        existante = CourrierComment.query.filter_by(
            courrier_id=courrier_id, type_comment='annotation_directeur', actif=True
        ).first()
        if existante:
            existante.commentaire = commentaire
            existante.date_modification = datetime.utcnow()
            existante.modifie_par_id = current_user.id
            sign_courrier_action(courrier_id, current_user, 'ANNOTATION_DIRECTEUR',
                                 {'maj': True, 'extrait': commentaire[:200]})
            db.session.commit()
            log_activity(current_user.id, "ANNOTATION_DIRECTEUR",
                         f"Mise à jour de l'annotation du Directeur — {courrier.numero_accuse_reception}", courrier_id)
            flash("Annotation du Directeur mise à jour.", 'success')
            return redirect(url_for('mail_detail', id=courrier_id))
```

Compléter le mapping d'action (`action_type_map`, ~L1626) :

```python
        'annotation_directeur': 'ANNOTATION_DIRECTEUR',
```

(Le chemin « création » existant gère alors la première annotation Directeur, y compris sa PJ via Task 4.)

- [ ] **Step 4 : Template — option de type + bloc dédié**

Dans `templates/mail_detail_new.html`, dans le `<select name="type_comment">` (L455), ajouter conditionnellement l'option :

```html
{% if current_user.has_permission('add_director_annotation') %}
<option value="annotation_directeur">Annotation du Directeur</option>
{% endif %}
```

Au-dessus du fil des commentaires, ajouter un bloc distinct pour l'annotation unique du Directeur :

```html
{% set annot_dir = courrier.comments | selectattr('type_comment','equalto','annotation_directeur') | selectattr('actif') | list | first %}
{% if annot_dir %}
<div class="gec-card" style="border-left:4px solid #b45309;background:rgba(180,83,9,.06);margin-bottom:1rem;">
  <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.35rem;">
    <i class="fas fa-user-tie" style="color:#b45309;"></i>
    <strong>Annotation du Directeur</strong>
    <span class="gec-form-hint" style="margin:0;">— {{ annot_dir.user.nom_complet }}</span>
  </div>
  <div style="white-space:pre-wrap;">{{ annot_dir.commentaire }}</div>
  {% if annot_dir.fichier_nom %}
  <a href="{{ url_for('download_comment_attachment', comment_id=annot_dir.id) }}" class="gec-link" style="font-size:.72rem;">
    <i class="fas fa-paperclip"></i> {{ annot_dir.fichier_nom }}
  </a>
  {% endif %}
</div>
{% endif %}
```

Optionnel : exclure `annotation_directeur` du fil générique des commentaires pour éviter le doublon (`{% if comment.type_comment != 'annotation_directeur' %}` autour de chaque item de la boucle).

- [ ] **Step 5 : Lancer → succès attendu**

Run: `python -m pytest tests/test_dpem_evolutions.py::TestAnnotationDirecteur -v`
Expected: PASS.

- [ ] **Step 6 : Commit**

```bash
git add routes/mail.py templates/mail_detail_new.html tests/test_dpem_evolutions.py
git commit -m "feat(dpem #2): Annotation du Directeur unique, permission dédiée, bloc distinct"
```

---

## Task 6 : Évolution #5 — Date d'enregistrement modifiable (RBAC)

Permission `edit_registration_date` (défaut : rôle `admin`, révocable via l'éditeur de rôles). `edit_courrier()` accepte `date_enregistrement` si l'utilisateur a la permission.

**Files :**
- Modify: `routes/mail.py` (`edit_courrier` ~L718-816)
- Modify: `templates/edit_courrier.html` (champ conditionnel)
- Modify: `app.py` (seed idempotent `ensure_dpem_permissions()`)
- Test: `tests/test_dpem_evolutions.py`

**Interfaces :**
- Consumes: permission `edit_registration_date` (Task 1). Produces: fonction `ensure_dpem_permissions()` (idempotente, appelée au boot).

- [ ] **Step 1 : Écrire le test qui échoue**

```python
class TestDateEnregistrement:
    def _courrier(self, app, client, perms):
        from models import Courrier
        uid = _role_with_perms(app, _db(), "editeur_date",
                               ["register_mail", "read_own_mail", "edit_own_mail"] + perms,
                               username="ed_date_u")
        _login(app, client, uid)
        client.post("/register_mail", data={
            "objet": "Courrier date", "type_courrier": "ENTRANT", "expediteur": "Exp",
            "secretaire_general_copie": "Non",
            "fichier": (io.BytesIO(_pdf_bytes()), "d.pdf"),
        }, content_type="multipart/form-data", follow_redirects=True)
        with app.app_context():
            return Courrier.query.filter_by(objet="Courrier date").first().id

    def test_sans_permission_date_inchangee(self, app, client):
        from models import Courrier
        cid = self._courrier(app, client, perms=[])
        client.post(f"/edit_courrier/{cid}", data={
            "objet": "Courrier date", "type_courrier": "ENTRANT", "expediteur": "Exp",
            "date_enregistrement": "2020-01-01T08:00",
        }, follow_redirects=True)
        with app.app_context():
            c = Courrier.query.get(cid)
            assert c.date_enregistrement.year != 2020

    def test_avec_permission_date_modifiee(self, app, client):
        from models import Courrier
        cid = self._courrier(app, client, perms=["edit_registration_date"])
        client.post(f"/edit_courrier/{cid}", data={
            "objet": "Courrier date", "type_courrier": "ENTRANT", "expediteur": "Exp",
            "date_enregistrement": "2020-01-01T08:00",
        }, follow_redirects=True)
        with app.app_context():
            c = Courrier.query.get(cid)
            assert c.date_enregistrement.year == 2020
```

- [ ] **Step 2 : Lancer → échec attendu**

Run: `python -m pytest tests/test_dpem_evolutions.py::TestDateEnregistrement -v`
Expected: FAIL (date ignorée dans les deux cas).

- [ ] **Step 3 : Gérer `date_enregistrement` dans `edit_courrier`**

Dans `routes/mail.py::edit_courrier`, dans le bloc `POST`, après le traitement du `new_statut` (~L806) et avant `courrier.modifie_par_id = current_user.id` (L809) :

```python
            # Évolution DPEM #5 : modification manuelle de la date d'enregistrement (RBAC)
            if current_user.has_permission('edit_registration_date'):
                raw_date = request.form.get('date_enregistrement', '').strip()
                if raw_date:
                    parsed = None
                    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
                        try:
                            parsed = datetime.strptime(raw_date, fmt)
                            break
                        except ValueError:
                            continue
                    if parsed and parsed != courrier.date_enregistrement:
                        log_courrier_modification(courrier.id, current_user.id, 'date_enregistrement',
                                                  str(courrier.date_enregistrement), str(parsed))
                        courrier.date_enregistrement = parsed
                        sign_courrier_action(courrier.id, current_user, 'MODIF_DATE_ENREG',
                                             {'nouvelle_date': str(parsed)})
                        changes.append("date d'enregistrement")
```

- [ ] **Step 4 : Champ conditionnel dans le template**

Dans `templates/edit_courrier.html`, dans le formulaire (près des autres champs date) :

```html
{% if current_user.has_permission('edit_registration_date') %}
<div class="gec-form-group">
  <label class="gec-label" for="date_enregistrement"><i class="fas fa-calendar-day"></i> Date d'enregistrement</label>
  <input type="datetime-local" id="date_enregistrement" name="date_enregistrement" class="gec-input"
         value="{{ courrier.date_enregistrement.strftime('%Y-%m-%dT%H:%M') if courrier.date_enregistrement }}">
  <p class="gec-form-hint">Réservé aux utilisateurs autorisés — journalisé.</p>
</div>
{% endif %}
```

- [ ] **Step 5 : Seed idempotent de la permission par défaut (admin)**

Dans `app.py`, dans le bloc d'initialisation au démarrage (après `models.RolePermission.init_default_permissions()` / `models.Role.ensure_hierarchy()`, ~L168), ajouter l'appel puis définir la fonction :

```python
    ensure_dpem_permissions()
```

Définir (dans `app.py`, ou dans `models/rbac.py` et importer) :

```python
def ensure_dpem_permissions():
    """Attribue par défaut edit_registration_date au rôle admin (idempotent, révocable via l'UI)."""
    from models import Role, RolePermission, db
    role = Role.query.filter_by(nom='admin').first()
    if role and not RolePermission.query.filter_by(role_id=role.id,
                                                    permission_nom='edit_registration_date').first():
        db.session.add(RolePermission(role_id=role.id, permission_nom='edit_registration_date'))
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
```

(`add_director_annotation` reste **sans attribution par défaut** — assignée manuellement au Directeur via l'éditeur de rôles, conformément au choix « permission seule ».)

- [ ] **Step 6 : Lancer → succès attendu**

Run: `python -m pytest tests/test_dpem_evolutions.py::TestDateEnregistrement -v`
Expected: PASS.

- [ ] **Step 7 : Commit**

```bash
git add routes/mail.py templates/edit_courrier.html app.py tests/test_dpem_evolutions.py
git commit -m "feat(dpem #5): date d'enregistrement modifiable via permission edit_registration_date"
```

---

## Task 7 : Évolution #4 — Courrier sortant adossé (lié) au courrier entrant

Depuis la fiche d'un courrier entrant, bouton « Générer un courrier sortant lié » → ouvre `register_mail` pré-rempli (type SORTANT, destinataire = expéditeur du parent) ; au POST, `courrier_parent_id` est renseigné. Cross-lien affiché sur les deux fiches.

**Files :**
- Modify: `routes/mail.py` (`register_mail` : lecture `parent_id` en GET et POST, garde d'accès, affectation FK, action `GEN_SORTANT`)
- Modify: `templates/register_mail.html` (`parent_id` caché + valeurs pré-remplies)
- Modify: `templates/mail_detail_new.html` (bouton « Générer réponse » + section cross-lien)
- Test: `tests/test_dpem_evolutions.py`

**Interfaces :**
- Consumes: `Courrier.courrier_parent_id`, `Courrier.reponses`, `Courrier.parent` (Task 1). Produces: paramètre `?parent_id=<id>` sur `register_mail`.

- [ ] **Step 1 : Écrire le test qui échoue**

```python
class TestCourrierAdosse:
    def test_sortant_lie_au_parent(self, app, client):
        from models import Courrier
        uid = _role_with_perms(app, _db(), "agent_lien",
                               ["register_mail", "read_all_mail"], username="lien_u")
        _login(app, client, uid)
        # 1) courrier entrant parent
        client.post("/register_mail", data={
            "objet": "Entrant parent", "type_courrier": "ENTRANT", "expediteur": "Ministère X",
            "secretaire_general_copie": "Non",
            "fichier": (io.BytesIO(_pdf_bytes()), "in.pdf"),
        }, content_type="multipart/form-data", follow_redirects=True)
        with app.app_context():
            parent = Courrier.query.filter_by(objet="Entrant parent").first()
            pid = parent.id
        # 2) GET pré-rempli
        resp = client.get(f"/register_mail?parent_id={pid}")
        assert resp.status_code == 200
        assert "Ministère X" in resp.data.decode()  # destinataire pré-rempli
        # 3) POST sortant lié
        client.post("/register_mail", data={
            "objet": "Réponse sortante", "type_courrier": "SORTANT", "destinataire": "Ministère X",
            "type_courrier_sortant_id": "", "date_redaction": "2026-06-20",
            "parent_id": str(pid),
            "fichier": (io.BytesIO(_pdf_bytes()), "out.pdf"),
        }, content_type="multipart/form-data", follow_redirects=True)
        with app.app_context():
            enfant = Courrier.query.filter_by(objet="Réponse sortante").first()
            assert enfant is not None
            assert enfant.courrier_parent_id == pid
            assert enfant in Courrier.query.get(pid).reponses
```

> Note : si `type_courrier_sortant_id` est obligatoire côté serveur (validation existante), le test doit fournir un id de `TypeCourrierSortant` semé via `_role_with_perms`-style ou `TypeCourrierSortant.init_default_types()` dans un `app_context`. Ajouter au besoin, dans le test, la création d'un type actif et passer son `id`.

- [ ] **Step 2 : Lancer → échec attendu**

Run: `python -m pytest tests/test_dpem_evolutions.py::TestCourrierAdosse -v`
Expected: FAIL (`courrier_parent_id` None ; GET non pré-rempli).

- [ ] **Step 3 : Lecture `parent_id` + pré-remplissage (GET) et affectation (POST)**

Dans `routes/mail.py::register_mail` :

Au **POST**, après la construction du `Courrier(...)` et **avant** `db.session.commit()` de création (donc juste après `courrier = Courrier(...)`, ~L197), lier le parent :

```python
        parent_id = request.form.get('parent_id', '').strip()
        parent = None
        if parent_id:
            parent = Courrier.query.get(int(parent_id)) if parent_id.isdigit() else None
            if parent and current_user.can_view_courrier(parent):
                courrier.courrier_parent_id = parent.id
```

Après le `db.session.commit()` de création + `sign_courrier_action(... 'CREATION' ...)` (~L207), si un parent est lié, signer côté parent :

```python
        if courrier.courrier_parent_id:
            sign_courrier_action(courrier.courrier_parent_id, current_user, 'GEN_SORTANT',
                                 {'courrier_lie_id': courrier.id, 'numero': numero_accuse})
            db.session.commit()
```

Au **GET** (fin de fonction, ~L343-353), calculer un contexte de pré-remplissage :

```python
    prefill = {}
    parent_id = request.args.get('parent_id', '')
    if parent_id.isdigit():
        parent = Courrier.query.get(int(parent_id))
        if parent and current_user.can_view_courrier(parent):
            prefill = {
                'parent_id': parent.id,
                'type_courrier': 'SORTANT',
                'destinataire': parent.get_decrypted_expediteur() or parent.expediteur,
                'numero_reference': f"Réf. {parent.numero_accuse_reception}",
                'objet': f"Réponse à : {parent.objet}",
            }
    return render_template('register_mail.html', statuts_disponibles=statuts_disponibles,
                         departements=departements, parametres=parametres,
                         types_courrier_sortant=types_courrier_sortant, prefill=prefill)
```

- [ ] **Step 4 : Champs pré-remplis dans `register_mail.html`**

Dans `templates/register_mail.html` :
- Ajouter un champ caché dans le `<form>` : `<input type="hidden" name="parent_id" value="{{ prefill.parent_id if prefill else '' }}">`.
- Pré-remplir les `value=` / sélection : par ex. `value="{{ prefill.destinataire if prefill else '' }}"` sur le champ destinataire, idem `objet`, `numero_reference` ; si `prefill.type_courrier == 'SORTANT'`, sélectionner l'onglet/option SORTANT par défaut. Utiliser `{{ prefill.get('champ','') }}` avec un `{% set prefill = prefill or {} %}` en tête de template pour éviter les erreurs quand `prefill` est absent.

- [ ] **Step 5 : Bouton + cross-lien dans le détail**

Dans `templates/mail_detail_new.html` :
- Dans la barre d'actions, pour un courrier **ENTRANT**, ajouter :

```html
{% if courrier.type_courrier == 'ENTRANT' %}
<a href="{{ url_for('register_mail', parent_id=courrier.id) }}" class="gec-btn gec-btn-primary">
  <i class="fas fa-reply"></i> Générer un courrier sortant lié
</a>
{% endif %}
```

- Ajouter une section de liens croisés :

```html
{% if courrier.parent %}
<div class="gec-form-hint"><i class="fas fa-link"></i> En réponse à :
  <a href="{{ url_for('mail_detail', id=courrier.parent.id) }}">{{ courrier.parent.numero_accuse_reception }}</a>
</div>
{% endif %}
{% if courrier.reponses and courrier.reponses|length %}
<div class="gec-form-hint"><i class="fas fa-link"></i> Courrier(s) sortant(s) lié(s) :
  {% for r in courrier.reponses %}
  <a href="{{ url_for('mail_detail', id=r.id) }}">{{ r.numero_accuse_reception }}</a>{% if not loop.last %}, {% endif %}
  {% endfor %}
</div>
{% endif %}
```

- [ ] **Step 6 : Lancer → succès attendu**

Run: `python -m pytest tests/test_dpem_evolutions.py::TestCourrierAdosse -v`
Expected: PASS.

- [ ] **Step 7 : Commit**

```bash
git add routes/mail.py templates/register_mail.html templates/mail_detail_new.html tests/test_dpem_evolutions.py
git commit -m "feat(dpem #4): courrier sortant adossé au courrier entrant (formulaire pré-rempli + cross-lien)"
```

---

## Task 8 : Intégration, i18n, validation visuelle & déploiement

**Files :**
- Modify: `lang/fr.json`, `lang/en.json`
- Modify: `docs/GEC_Changelog.md` (entrée de version)
- Test: toute la suite

- [ ] **Step 1 : Chaînes i18n**

Ajouter dans `lang/fr.json` et `lang/en.json` les clés utilisées (labels : « Annotation du Directeur », « Étiquette », « Pièce jointe (PDF ou image) », « Générer un courrier sortant lié », « Date d'enregistrement », « Statut initial »). Respecter le format existant des fichiers (mêmes clés dans les deux langues).

- [ ] **Step 2 : Lancer toute la suite de tests**

Run: `python -m pytest tests/ -v`
Expected: la nouvelle suite `tests/test_dpem_evolutions.py` PASS ; pas de régression sur les tests préexistants qui passaient déjà. (Rappel : certains tests historiques utilisent des chemins/rôles obsolètes — ne pas les « réparer » dans ce chantier, seulement ne pas les casser davantage.)

- [ ] **Step 3 : Vérifier le démarrage réel (migration auto + backfill)**

```bash
cd gec && source venv/bin/activate
python -c "import app"   # doit logguer 'Migration 17 (DPEM)…' sans erreur (sur DB dev)
```

Expected: colonnes ajoutées, backfill `numero_suivi` sur les courriers existants, aucun crash.

- [ ] **Step 4 : Validation visuelle (obligatoire avant PR)**

Lancer `/validate-and-push` : captures Playwright desktop + mobile des écrans touchés — register_mail (statut lecture seule), détail courrier (annotation Directeur, PJ commentaire, boutons Étiquette / Générer sortant), étiquette imprimable, edit_courrier (champ date), éditeur de rôles (nouvelles permissions visibles). **STOP** → validation utilisateur.

- [ ] **Step 5 : Changelog + PR (jamais sur `main`)**

Ajouter une entrée dans `docs/GEC_Changelog.md` (6 évolutions DPEM). Puis :

```bash
git checkout -b feat/dpem-evolutions-06003
git push -u origin feat/dpem-evolutions-06003
gh pr create --title "Évolutions GEC DPEM (Réf. MOA/CD/KIN/06003/2026)" \
  --body "Implémente les 6 évolutions demandées par la DPEM : statut figé, annotation Directeur, PJ commentaires, courrier sortant adossé, date d'enregistrement modifiable, QR + numéro de suivi."
```

- [ ] **Step 6 : Déploiement VPS 2 (après merge de la PR)**

```bash
ssh -i ~/.ssh/vps1_access root@168.231.86.201
cd /var/websites/gec
git pull origin main
source venv/bin/activate
# La migration auto s'exécute au boot ; si Flask-Migrate est utilisé en complément :
# flask db migrate -m "dpem evolutions" && flask db upgrade
pm2 restart gec
curl http://localhost:5004
pm2 logs gec --lines 40   # vérifier 'Migration 17 (DPEM)' et absence d'erreur
```

- [ ] **Step 7 : Documenter le déploiement**

Consigner la mise en ligne dans un `DEPLOIEMENT.md` du projet **et** en mémoire (URL solution-gec.com, repo, VPS2, pm2 `gec` port 5004, migration appliquée, date).

---

## Auto-revue du plan (couverture spec)

| Évolution (lettre) | Tâche(s) | Statut couverture |
|---|---|---|
| #1 Statut figé à l'enregistrement | Task 2 | ✅ serveur force `RECU` + UI lecture seule |
| #2 Annotation du Directeur (unique) | Task 1 (perm/action) + Task 5 | ✅ permission dédiée + unicité + bloc distinct |
| #3 PJ (PDF/image) sur annotations & commentaires | Task 1 (colonnes) + Task 4 | ✅ upload chiffré + download anti-IDOR |
| #4 Courrier sortant adossé | Task 1 (FK) + Task 7 | ✅ pré-remplissage + `courrier_parent_id` + cross-lien |
| #5 Date d'enregistrement modifiable (RBAC) | Task 1 (perm) + Task 6 | ✅ permission `edit_registration_date` + défaut admin |
| #6 QR code + numéro de suivi | Task 1 (colonne/générateur) + Task 3 | ✅ `numero_suivi` + étiquette QR + recherche |

**Transversal :** migration auto (Task 1) · signature de non-répudiation sur chaque action (Tasks 2-7) · i18n (Task 8) · validation visuelle + PR + déploiement (Task 8). **Note métier :** exécution conditionnée au paiement complet de la facture (en-tête).
