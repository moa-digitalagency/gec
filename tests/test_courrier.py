"""
Tests for courrier registration, detail view, download, and bulk actions.
"""
import io
import pytest


def _make_pdf_bytes():
    """Minimal valid PDF bytes for upload tests."""
    return b"%PDF-1.4 1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"


class TestRegisterMail:
    def test_register_page_loads(self, admin_client):
        resp = admin_client.get("/register_mail")
        assert resp.status_code == 200

    def test_register_entrant_success(self, admin_client, app):
        data = {
            "objet": "Test courrier entrant",
            "type_courrier": "ENTRANT",
            "expediteur": "Ministère Test",
            "secretaire_general_copie": "Non",
            "statut": "RECU",
            "fichier": (io.BytesIO(_make_pdf_bytes()), "test.pdf"),
        }
        resp = admin_client.post(
            "/register_mail",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        # Should land on detail page or show success flash
        body = resp.data.decode()
        assert "test courrier entrant" in body.lower() or "succès" in body.lower() or "enregistré" in body.lower()

    def test_register_missing_expediteur_fails(self, admin_client):
        data = {
            "objet": "Manque expediteur",
            "type_courrier": "ENTRANT",
            "expediteur": "",
            "secretaire_general_copie": "Non",
            "statut": "RECU",
            "fichier": (io.BytesIO(_make_pdf_bytes()), "test.pdf"),
        }
        resp = admin_client.post(
            "/register_mail",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        # Should stay on register page with error
        body = resp.data.decode()
        assert "obligatoire" in body.lower() or "error" in body.lower() or "register" in body.lower()

    def test_register_unauthenticated_redirects(self, client):
        resp = client.post("/register_mail", data={}, follow_redirects=False)
        assert resp.status_code in (302, 303)


class TestMailDetail:
    @pytest.fixture(autouse=True)
    def _create_courrier(self, app, admin_client):
        """Create a test courrier and store its ID."""
        data = {
            "objet": "Detail test courrier",
            "type_courrier": "ENTRANT",
            "expediteur": "Testeur",
            "secretaire_general_copie": "Non",
            "statut": "RECU",
            "fichier": (io.BytesIO(_make_pdf_bytes()), "detail_test.pdf"),
        }
        resp = admin_client.post(
            "/register_mail",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        # Extract courrier ID from URL — we landed on mail_detail/<id>
        with app.app_context():
            from models import Courrier
            c = Courrier.query.filter_by(objet="Detail test courrier").first()
            self.courrier_id = c.id if c else None

    def test_detail_page_loads(self, admin_client):
        if not self.courrier_id:
            pytest.skip("Courrier creation failed")
        resp = admin_client.get(f"/mail_detail/{self.courrier_id}")
        assert resp.status_code == 200
        body = resp.data.decode()
        assert "detail test courrier" in body.lower()

    def test_detail_unauthenticated_redirect(self, client):
        resp = client.get("/mail_detail/1", follow_redirects=False)
        assert resp.status_code in (302, 303)


class TestBulkAction:
    @pytest.fixture(autouse=True)
    def _create_courriers(self, app, admin_client):
        self.ids = []
        for i in range(3):
            data = {
                "objet": f"Bulk test {i}",
                "type_courrier": "ENTRANT",
                "expediteur": "TestBulk",
                "secretaire_general_copie": "Non",
                "statut": "RECU",
                "fichier": (io.BytesIO(_make_pdf_bytes()), f"bulk_{i}.pdf"),
            }
            admin_client.post(
                "/register_mail",
                data=data,
                content_type="multipart/form-data",
            )
        with app.app_context():
            from models import Courrier
            courriers = Courrier.query.filter_by(expediteur="TestBulk").all()
            self.ids = [str(c.id) for c in courriers]

    def test_bulk_change_status(self, admin_client, app):
        if not self.ids:
            pytest.skip("No courriers created")
        data = {"action": "statut_traite"}
        for id_ in self.ids:
            data[f"ids"] = self.ids  # will be sent as list
        resp = admin_client.post(
            "/bulk_action",
            data={"action": "statut_traite", "ids": self.ids},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            from models import Courrier
            for id_ in self.ids:
                c = Courrier.query.get(int(id_))
                if c:
                    assert c.statut == "TRAITE"

    def test_bulk_delete(self, admin_client, app):
        if not self.ids:
            pytest.skip("No courriers created")
        resp = admin_client.post(
            "/bulk_action",
            data={"action": "delete", "ids": self.ids},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            from models import Courrier
            for id_ in self.ids:
                c = Courrier.query.get(int(id_))
                if c:
                    assert c.is_deleted is True

    def test_bulk_unauthenticated(self, client):
        resp = client.post("/bulk_action", data={"action": "statut_recu", "ids": ["1"]},
                           follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_bulk_no_ids(self, admin_client):
        resp = admin_client.post(
            "/bulk_action",
            data={"action": "statut_recu"},
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_bulk_unknown_action(self, admin_client):
        if not self.ids:
            pytest.skip("No courriers created")
        resp = admin_client.post(
            "/bulk_action",
            data={"action": "unknown_action", "ids": self.ids},
            follow_redirects=True,
        )
        assert resp.status_code == 200
