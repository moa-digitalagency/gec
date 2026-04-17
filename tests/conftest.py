"""
Shared fixtures for GEC test suite.
Uses SQLite in-memory for speed; CSRF disabled in tests.
"""
import os
import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SESSION_SECRET", "test-secret-key-for-ci")
os.environ.setdefault("WTF_CSRF_ENABLED", "False")


@pytest.fixture(scope="session")
def app():
    from app import app as flask_app, db

    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SESSION_IDLE_TIMEOUT=0,  # disable idle timeout in tests
    )

    with flask_app.app_context():
        db.create_all()
        _seed_db(db, flask_app)
        yield flask_app
        db.session.remove()
        db.drop_all()


def _seed_db(db, app):
    from models import User, ParametresSysteme
    from werkzeug.security import generate_password_hash

    # Create parametres_systeme row required by many routes
    if not ParametresSysteme.query.first():
        params = ParametresSysteme()
        db.session.add(params)

    # super_admin
    if not User.query.filter_by(username="admin_test").first():
        u = User(
            username="admin_test",
            email="admin@test.com",
            nom_complet="Admin Test",
            role="super_admin",
            actif=True,
        )
        u.set_password("AdminPass123!")
        db.session.add(u)

    # regular user
    if not User.query.filter_by(username="user_test").first():
        u2 = User(
            username="user_test",
            email="user@test.com",
            nom_complet="User Test",
            role="user",
            actif=True,
        )
        u2.set_password("UserPass123!")
        db.session.add(u2)

    db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_client(app):
    """Authenticated client as super_admin."""
    client = app.test_client()
    with client.session_transaction() as sess:
        from models import User
        with app.app_context():
            u = User.query.filter_by(username="admin_test").first()
            sess["_user_id"] = str(u.id)
            sess["_fresh"] = True
    return client


@pytest.fixture
def user_client(app):
    """Authenticated client as regular user."""
    client = app.test_client()
    with client.session_transaction() as sess:
        from models import User
        with app.app_context():
            u = User.query.filter_by(username="user_test").first()
            sess["_user_id"] = str(u.id)
            sess["_fresh"] = True
    return client
