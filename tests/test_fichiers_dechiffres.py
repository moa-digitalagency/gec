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
def courrier_chiffre(app):
    """Un courrier dont le fichier principal, une pièce jointe et un commentaire
    portent chacun un fichier réellement chiffré, rangé dans uploads/ comme en
    production (les routes refusent tout chemin hors de ce dossier)."""
    import shutil

    from app import db
    from models import Courrier, CourrierAttachment, CourrierComment, User
    from security import encrypt_uploaded_file

    dossier = os.path.join("uploads", f"test_dechiffres_{uuid.uuid4().hex[:8]}")
    os.makedirs(dossier)

    def fichier_chiffre(nom):
        clair = os.path.join(dossier, nom)
        with open(clair, "wb") as f:
            f.write(CONTENU)
        chemin = encrypt_uploaded_file(clair)
        os.remove(clair)
        return chemin

    with app.app_context():
        auteur = User.query.filter_by(username="user_test").first()
        courrier = Courrier(
            numero_accuse_reception=f"GEC-PJ-{uuid.uuid4().hex[:8]}",
            objet="Courrier avec pièces jointes chiffrées",
            type_courrier="ENTRANT",
            expediteur="Expéditeur test",
            date_redaction=date.today(),
            statut="RECU",
            utilisateur_id=auteur.id,
            fichier_nom="principal.pdf",
            fichier_chemin=fichier_chiffre("principal.pdf"),
            fichier_type="application/pdf",
            fichier_encrypted=True,
        )
        db.session.add(courrier)
        db.session.commit()
        piece = CourrierAttachment(
            courrier_id=courrier.id,
            fichier_nom="annexe.pdf",
            fichier_chemin=fichier_chiffre("annexe.pdf"),
            fichier_type="application/pdf",
            fichier_taille=len(CONTENU),
            fichier_encrypted=True,
            uploaded_by_id=auteur.id,
        )
        commentaire = CourrierComment(
            courrier_id=courrier.id,
            user_id=auteur.id,
            commentaire="Pièce jointe chiffrée",
            fichier_nom="note.pdf",
            fichier_chemin=fichier_chiffre("note.pdf"),
            fichier_type="application/pdf",
            fichier_encrypted=True,
        )
        db.session.add_all([piece, commentaire])
        db.session.commit()
        ids = {"courrier": courrier.id, "piece": piece.id,
               "commentaire": commentaire.id, "auteur": auteur.id}

    yield ids

    # La base de test est partagée par toute la session : on retire ce qu'on a créé,
    # y compris ce que les routes ont journalisé (activité, signatures…), en suivant
    # toutes les clés étrangères qui pointent vers ce courrier.
    with app.app_context():
        db.session.rollback()
        for table in reversed(db.metadata.sorted_tables):
            for colonne in table.columns:
                if any(fk.column.table.name == "courrier" for fk in colonne.foreign_keys):
                    db.session.execute(table.delete().where(colonne == ids["courrier"]))
        db.session.execute(Courrier.__table__.delete().where(Courrier.id == ids["courrier"]))
        db.session.commit()
    shutil.rmtree(dossier, ignore_errors=True)


ROUTES = {
    "fichier principal": "/download_file/{courrier}",
    "visualisation": "/view_file/{courrier}",
    "pièce jointe": "/download_attachment/{piece}",
    "pièce jointe de commentaire": "/download_comment_attachment/{commentaire}",
}


@pytest.mark.parametrize("route", list(ROUTES), ids=list(ROUTES))
def test_telechargement_ne_laisse_aucun_fichier_dechiffre(app, courrier_chiffre, route):
    dossier = _dossier_temporaire()
    avant = set(os.listdir(dossier))

    client = app.test_client()
    _login(client, courrier_chiffre["auteur"])
    try:
        reponse = client.get(ROUTES[route].format(**courrier_chiffre))
        assert reponse.status_code == 200, f"{route} : HTTP {reponse.status_code}"
        # Lire le corps comme le fait un serveur WSGI, puis fermer la réponse.
        assert reponse.get_data() == CONTENU, f"{route} : contenu déchiffré incorrect"
        reponse.close()

        restants = set(os.listdir(dossier)) - avant
        assert restants == set(), (
            f"{route} : pièce(s) jointe(s) déchiffrée(s) restée(s) en clair : {sorted(restants)}"
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
