"""Tests des 6 évolutions DPEM (Réf. MOA/CD/KIN/06003/2026)."""
import io
import re
import time
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


def _db():
    from app import db
    return db


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


@pytest.fixture(autouse=True)
def _reset_shared_login_cache(app):
    """Voir `_login()` ci-dessous : le fixture `app` (conftest.py) garde un seul
    app_context ouvert pour toute la session pytest, donc un seul `g` partagé
    par toutes les requêtes HTTP simulées de la suite. Sans ce nettoyage,
    l'identité authentifiée par un test de ce module resterait mise en cache
    dans ce `g` partagé et fuiterait vers les tests suivants (autres fichiers)
    qui s'attendent à un visiteur anonyme.
    """
    yield
    from flask import g
    if hasattr(g, "_login_user"):
        del g._login_user


def _db_app_client():
    """Nouveau test_client() indépendant, pour authentifier un 2e utilisateur
    (propriétaire d'un courrier distinct) sans piétiner la session du `client`
    fixture déjà utilisé dans le même test."""
    from app import app as flask_app
    return flask_app.test_client()


def _login(app, client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
        # `enforce_session_expiry` (routes/auth.py) traite une session sans
        # `last_activity` comme expirée dès la 1re requête ; le vrai login()
        # pose ce timestamp — on le reproduit ici pour simuler un login réel.
        sess["last_activity"] = time.time()
    # Le fixture `app` (conftest.py) garde un seul app_context ouvert pour
    # toute la session pytest. Flask ne pousse un app_context frais que s'il
    # n'y en a aucun d'actif (flask/ctx.py RequestContext.push) : comme celui
    # du fixture reste actif en permanence, TOUTES les requêtes HTTP simulées
    # de la suite partagent le même `g`. Si un test précédent a déjà évalué
    # `current_user` (ex. rendu d'un template avant login), flask-login met en
    # cache l'utilisateur (souvent anonyme) dans ce `g` partagé — et cette
    # valeur reste figée pour le reste de la suite. On purge ce cache après
    # avoir posé la session ci-dessus pour forcer flask-login à relire la
    # session fraîchement authentifiée à la prochaine requête.
    from flask import g
    if hasattr(g, "_login_user"):
        del g._login_user


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
        from models import Courrier, User
        db = _db()
        with app.app_context():
            n1 = generate_numero_suivi()
            assert re.match(r"^SUIVI-\d{4}-\d{5}$", n1)

            user = User.query.filter_by(username="admin_test").first()
            c1 = Courrier(
                numero_accuse_reception="ACC-TEST-UNIQ-1",
                objet="Test unicité numero_suivi 1",
                type_courrier="ENTRANT",
                numero_suivi=n1,
                utilisateur_id=user.id,
            )
            db.session.add(c1)
            db.session.commit()

            n2 = generate_numero_suivi()
            c2 = Courrier(
                numero_accuse_reception="ACC-TEST-UNIQ-2",
                objet="Test unicité numero_suivi 2",
                type_courrier="ENTRANT",
                numero_suivi=n2,
                utilisateur_id=user.id,
            )
            db.session.add(c2)
            db.session.commit()

            assert n1 != n2

    def test_new_permissions_in_catalog(self, app):
        from routes.admin import PERMISSIONS_CATALOG
        assert "add_director_annotation" in PERMISSIONS_CATALOG
        assert "edit_registration_date" in PERMISSIONS_CATALOG


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
            # `.order_by(id.desc())` : le DB de test est partagé (session-scope) entre
            # tous les appels de ce helper, donc plusieurs courriers portant le même
            # `objet` s'accumulent au fil des tests ; on veut celui tout juste créé.
            return Courrier.query.filter_by(objet="Courrier PJ commentaire")\
                                  .order_by(Courrier.id.desc()).first().id

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

    def test_comment_without_attachment_saved(self, app, client):
        """Non-régression : le flux commentaire classique (sans PJ) reste fonctionnel."""
        from models import CourrierComment
        cid = self._make_courrier_and_login(app, client)
        client.post(f"/add_comment/{cid}", data={
            "commentaire": "Commentaire sans pièce jointe", "type_comment": "comment",
        }, content_type="multipart/form-data", follow_redirects=True)
        with app.app_context():
            com = CourrierComment.query.filter_by(courrier_id=cid).first()
            assert com is not None
            assert com.commentaire == "Commentaire sans pièce jointe"
            assert com.fichier_nom is None

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


class TestStatutFige:
    def test_statut_force_recu_meme_si_autre_soumis(self, app, client):
        from models import Courrier
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


class TestAnnotationDirecteur:
    def _courrier_owned_by(self, app, role, perms, username):
        from models import Courrier
        client = _db_app_client()
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
