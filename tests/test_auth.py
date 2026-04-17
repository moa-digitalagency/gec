"""
Tests for authentication routes: login, logout, session security.
"""
import pytest


class TestLogin:
    def test_login_page_loads(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_login_success_redirects(self, client):
        resp = client.post("/login", data={
            "username": "admin_test",
            "password": "AdminPass123!",
        }, follow_redirects=False)
        # Should redirect away from login on success
        assert resp.status_code in (302, 303)
        assert "/login" not in (resp.headers.get("Location") or "")

    def test_login_wrong_password(self, client):
        resp = client.post("/login", data={
            "username": "admin_test",
            "password": "WrongPassword!",
        }, follow_redirects=True)
        assert resp.status_code == 200
        body = resp.data.decode()
        assert "login" in body.lower() or "mot de passe" in body.lower() or "invalide" in body.lower() or "incorrect" in body.lower()

    def test_login_unknown_user(self, client):
        resp = client.post("/login", data={
            "username": "nobody",
            "password": "Whatever1!",
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_dashboard_requires_login(self, client):
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code in (302, 303)
        location = resp.headers.get("Location", "")
        assert "login" in location

    def test_logout_redirects_to_login(self, admin_client):
        resp = admin_client.get("/logout", follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_authenticated_dashboard_loads(self, admin_client):
        resp = admin_client.get("/dashboard")
        assert resp.status_code == 200


class TestPasswordSecurity:
    def test_bcrypt_hash_not_exposed(self, app):
        """Password hash must not be the plain password."""
        from models import User
        with app.app_context():
            u = User.query.filter_by(username="admin_test").first()
            assert u.password_hash != "AdminPass123!"
            assert len(u.password_hash) > 20

    def test_check_password_correct(self, app):
        from models import User
        with app.app_context():
            u = User.query.filter_by(username="admin_test").first()
            assert u.check_password("AdminPass123!")

    def test_check_password_wrong(self, app):
        from models import User
        with app.app_context():
            u = User.query.filter_by(username="admin_test").first()
            assert not u.check_password("WrongPassword!")
