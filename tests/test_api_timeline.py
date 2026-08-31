"""Tests de /api/courrier/<id>/timeline.

La chronologie n'était jamais exercée avec un commentaire en base : la branche
correspondante lisait des attributs inexistants (`contenu`, `auteur`) et
renvoyait donc une 500 dès qu'un courrier portait le moindre commentaire.
"""

import time
from datetime import date


def _purge_cache_login():
    """Le fixture `app` garde un unique app_context pour toute la session pytest :
    flask-login y met en cache l'utilisateur dans `g._login_user`. Sans purge, la
    session ouverte ici fuiterait sur les tests suivants (ex. /login qui redirige
    un utilisateur déjà connecté)."""
    from flask import g

    if hasattr(g, "_login_user"):
        del g._login_user


def _login(app, client, user_id):
    """Ouvre une session comme le vrai login() : `enforce_session_expiry`
    (routes/auth.py) considère expirée toute session sans `last_activity`."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
        sess["last_activity"] = time.time()
    _purge_cache_login()


def _courrier_avec_commentaire(app, auteur_username):
    from app import db
    from models import User, Courrier, CourrierComment

    with app.app_context():
        auteur = User.query.filter_by(username=auteur_username).first()
        auteur_id = auteur.id
        c = Courrier(
            numero_accuse_reception="GEC-TIMELINE-001",
            objet="Courrier pour la chronologie",
            type_courrier="ENTRANT",
            expediteur="Expéditeur test",
            destinataire="Destinataire test",
            date_redaction=date.today(),
            statut="RECU",
            utilisateur_id=auteur.id,
        )
        db.session.add(c)
        db.session.commit()

        db.session.add(
            CourrierComment(
                courrier_id=c.id,
                user_id=auteur.id,
                commentaire="Un commentaire qui doit apparaître dans la chronologie",
            )
        )
        db.session.commit()
        return c.id, auteur_id


def test_timeline_rend_les_commentaires(app):
    """La chronologie d'un courrier commenté ne doit pas tomber en 500."""
    cid, auteur_id = _courrier_avec_commentaire(app, "user_test")
    client = app.test_client()
    _login(app, client, auteur_id)

    try:
        r = client.get(f"/api/courrier/{cid}/timeline")
        assert r.status_code == 200, f"chronologie en échec : HTTP {r.status_code}"

        events = r.get_json()
        commentaires = [e for e in events if e["type"] == "comment"]
        assert commentaires, "le commentaire n'apparaît pas dans la chronologie"
        assert "chronologie" in commentaires[0]["detail"]
        assert (
            commentaires[0]["user"] != "?"
        ), "l'auteur du commentaire n'est pas résolu"
    finally:
        _purge_cache_login()
