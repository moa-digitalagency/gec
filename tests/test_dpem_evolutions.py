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
