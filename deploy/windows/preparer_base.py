"""Crée l'utilisateur et la base PostgreSQL de GEC s'ils n'existent pas (idempotent).

Appelé par installer-gec.ps1. Les mots de passe sont lus dans l'environnement,
jamais sur la ligne de commande, pour ne pas apparaître dans la liste des processus.

Variables lues :
    GEC_PG_ADMIN_MDP   mot de passe du super-utilisateur PostgreSQL (postgres)
    GEC_PG_ADMIN       nom du super-utilisateur (défaut : postgres)
    GEC_PG_HOTE, GEC_PG_PORT
    GEC_DB_NOM, GEC_DB_UTILISATEUR, GEC_DB_MDP
"""

import os
import re
import sys

import psycopg2
from psycopg2 import sql

# Les instructions CREATE ROLE / CREATE DATABASE n'acceptent pas les noms en
# paramètres liés : ils sont composés avec sql.Identifier (échappement PostgreSQL)
# et, par précaution, restreints à un alphabet sans ambiguïté. Le mot de passe,
# lui, est toujours passé en paramètre lié.
NOM_VALIDE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


def main():
    env = os.environ
    try:
        connexion = psycopg2.connect(
            host=env.get("GEC_PG_HOTE", "localhost"),
            port=int(env.get("GEC_PG_PORT", "5432")),
            user=env.get("GEC_PG_ADMIN", "postgres"),
            password=env["GEC_PG_ADMIN_MDP"],
            dbname="postgres",
            connect_timeout=10,
        )
    except psycopg2.OperationalError as e:
        print(f"ERREUR : connexion à PostgreSQL impossible avec le compte "
              f"« {env.get('GEC_PG_ADMIN', 'postgres')} » : {e}".strip())
        return 2

    connexion.autocommit = True  # CREATE DATABASE refuse de s'exécuter dans une transaction
    utilisateur, base, mdp = env["GEC_DB_UTILISATEUR"], env["GEC_DB_NOM"], env["GEC_DB_MDP"]
    for libelle, nom in (("utilisateur", utilisateur), ("base", base)):
        if not NOM_VALIDE.match(nom):
            print(f"ERREUR : nom de {libelle} « {nom} » refusé — lettres, chiffres et "
                  f"soulignés uniquement, sans commencer par un chiffre.")
            return 2

    with connexion.cursor() as c:
        c.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (utilisateur,))
        if c.fetchone():
            c.execute(sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD %s").format(
                sql.Identifier(utilisateur)), (mdp,))
            print(f"Utilisateur « {utilisateur} » existant : mot de passe mis à jour.")
        else:
            c.execute(sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD %s").format(
                sql.Identifier(utilisateur)), (mdp,))
            print(f"Utilisateur « {utilisateur} » créé.")

        c.execute("SELECT 1 FROM pg_database WHERE datname = %s", (base,))
        if c.fetchone():
            print(f"Base « {base} » existante : conservée telle quelle.")
        else:
            c.execute(sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8' TEMPLATE template0").format(
                sql.Identifier(base), sql.Identifier(utilisateur)))
            print(f"Base « {base} » créée (UTF-8).")

    connexion.close()

    # Depuis PostgreSQL 15, le schéma public n'est plus ouvert en écriture à tous :
    # le propriétaire de la base doit en être propriétaire pour y créer les tables.
    connexion = psycopg2.connect(
        host=env.get("GEC_PG_HOTE", "localhost"), port=int(env.get("GEC_PG_PORT", "5432")),
        user=env.get("GEC_PG_ADMIN", "postgres"), password=env["GEC_PG_ADMIN_MDP"],
        dbname=base, connect_timeout=10,
    )
    connexion.autocommit = True
    with connexion.cursor() as c:
        c.execute(sql.SQL("ALTER SCHEMA public OWNER TO {}").format(sql.Identifier(utilisateur)))
    connexion.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
