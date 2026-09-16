"""Aucune pièce jointe déchiffrée ne doit rester en clair sur le disque.

Pour servir une pièce jointe chiffrée, GEC la déchiffre dans security/temp puis
la supprime. Supprimer le fichier juste après send_file() fonctionne sous Linux,
où l'on peut effacer un fichier encore ouvert, mais échoue sous Windows
(WinError 32 : le fichier est ouvert pour l'envoi). L'erreur étant avalée, la
pièce jointe restait en clair — ce test ne peut donc échouer que sous Windows,
d'où son exécution dans le job CI Windows.
"""

import os
import time
import uuid
from datetime import date

import pytest

CONTENU = b"%PDF-1.4 piece jointe confidentielle " + b"x" * 200_000


def _purge_cache_login():
    from flask import g

    if hasattr(g, "_login_user"):
        del g._login_user


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
        sess["last_activity"] = time.time()
    _purge_cache_login()


def _dossier_temporaire():
    import security.encryption as enc

    dossier = os.path.join(os.path.dirname(enc.__file__), "temp")
    os.makedirs(dossier, exist_ok=True)
    return dossier


@pytest.fixture
def commentaire_chiffre(app, tmp_path):
    """Un commentaire portant une pièce jointe réellement chiffrée."""
    from app import db
    from models import Courrier, CourrierComment, User
    from security import encrypt_uploaded_file

    clair = tmp_path / "note.pdf"
    clair.write_bytes(CONTENU)
    chemin_chiffre = encrypt_uploaded_file(str(clair))
    clair.unlink()

    with app.app_context():
        auteur = User.query.filter_by(username="user_test").first()
        courrier = Courrier(
            numero_accuse_reception=f"GEC-PJ-{uuid.uuid4().hex[:8]}",
            objet="Courrier avec pièce jointe chiffrée",
            type_courrier="ENTRANT",
            expediteur="Expéditeur test",
            date_redaction=date.today(),
            statut="RECU",
            utilisateur_id=auteur.id,
        )
        db.session.add(courrier)
        db.session.commit()
        commentaire = CourrierComment(
            courrier_id=courrier.id,
            user_id=auteur.id,
            commentaire="Pièce jointe chiffrée",
            fichier_nom="note.pdf",
            fichier_chemin=chemin_chiffre,
            fichier_type="application/pdf",
            fichier_encrypted=True,
        )
        db.session.add(commentaire)
        db.session.commit()
        return commentaire.id, auteur.id


def test_telechargement_ne_laisse_aucun_fichier_dechiffre(app, commentaire_chiffre):
    commentaire_id, auteur_id = commentaire_chiffre
    dossier = _dossier_temporaire()
    avant = set(os.listdir(dossier))

    client = app.test_client()
    _login(client, auteur_id)
    try:
        reponse = client.get(f"/download_comment_attachment/{commentaire_id}")
        assert reponse.status_code == 200
        # Lire le corps comme le fait un serveur WSGI, puis fermer la réponse.
        assert reponse.get_data() == CONTENU
        reponse.close()

        restants = set(os.listdir(dossier)) - avant
        assert restants == set(), (
            f"pièce(s) jointe(s) déchiffrée(s) restée(s) en clair : {sorted(restants)}"
        )
    finally:
        _purge_cache_login()


def test_fichier_orphelin_ancien_est_purge(app):
    """Un fichier déchiffré laissé par un arrêt brutal est effacé au démarrage."""
    from security.encryption import purger_fichiers_dechiffres_orphelins

    dossier = _dossier_temporaire()
    ancien = os.path.join(dossier, f"tmp_{uuid.uuid4().hex}_ancien.pdf")
    recent = os.path.join(dossier, f"tmp_{uuid.uuid4().hex}_recent.pdf")
    for chemin in (ancien, recent):
        with open(chemin, "wb") as f:
            f.write(CONTENU)
    il_y_a_une_heure = time.time() - 3600
    os.utime(ancien, (il_y_a_une_heure, il_y_a_une_heure))

    try:
        purger_fichiers_dechiffres_orphelins(age_minimum_minutes=10)
        assert not os.path.exists(ancien), "le fichier orphelin ancien n'a pas été purgé"
        # Un fichier récent peut être en cours d'envoi par un autre processus.
        assert os.path.exists(recent), "un fichier récent a été supprimé à tort"
    finally:
        for chemin in (ancien, recent):
            if os.path.exists(chemin):
                os.remove(chemin)
