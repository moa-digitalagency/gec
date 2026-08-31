"""Tests du système de migration automatique (utils/migrations.py).

Reproduit la dérive de schéma constatée en production : une table créée par une
version antérieure du code, à laquelle une colonne a ensuite été ajoutée au
modèle sans entrée correspondante dans les migrations automatiques.
`db.create_all()` ne rattrape jamais ce cas (il ne crée que les tables absentes).
"""
import pytest
from sqlalchemy import inspect, text


def _columns(db, table):
    return {c["name"] for c in inspect(db.engine).get_columns(table)}


def test_aucune_colonne_de_modele_absente_du_schema(app):
    """Aucun modèle ne doit déclarer une colonne absente du schéma réel."""
    from app import db

    with app.app_context():
        insp = inspect(db.engine)
        tables = set(insp.get_table_names())
        manquantes = []
        for nom, table in db.metadata.tables.items():
            if nom not in tables:
                manquantes.append((nom, "TABLE ENTIÈRE"))
                continue
            reelles = {c["name"] for c in insp.get_columns(nom)}
            manquantes += [(nom, c.name) for c in table.columns if c.name not in reelles]

        assert manquantes == [], f"Colonnes de modèle absentes du schéma : {manquantes}"


def test_migration_restaure_fichier_encrypted_sur_table_legacy(app):
    """Une table courrier_attachment héritée (sans fichier_encrypted) est rattrapée.

    C'est exactement l'état de la base de démo : la table avait été créée avant
    l'ajout de la colonne au modèle, provoquant une erreur 500 sur /mail/<id>.
    """
    from app import db
    from models import CourrierAttachment
    from utils.migrations import run_automatic_migrations

    with app.app_context():
        db.session.remove()
        db.session.execute(text("ALTER TABLE courrier_attachment DROP COLUMN fichier_encrypted"))
        db.session.commit()
        assert "fichier_encrypted" not in _columns(db, "courrier_attachment")

        # Sans la colonne, toute lecture des pièces jointes casse (l'erreur 500 vue en prod)
        db.session.remove()
        with pytest.raises(Exception):
            CourrierAttachment.query.all()
        db.session.rollback()

        # Le démarrage de l'application doit rattraper la colonne
        run_automatic_migrations(app, db)

        assert "fichier_encrypted" in _columns(db, "courrier_attachment")
        db.session.remove()
        assert CourrierAttachment.query.all() == []
