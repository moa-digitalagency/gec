"""Crée le fichier .env de GEC, ou vérifie et complète un .env existant.

Appelé par installer-gec.ps1. Toutes les valeurs arrivent par l'environnement,
jamais par la ligne de commande (qui est visible dans la liste des processus).

Un .env existant n'est jamais régénéré : GEC_MASTER_KEY chiffre les données en
base, la remplacer les rendrait illisibles définitivement. Seuls les réglages
d'exposition (hôte, port, HTTPS, proxy) sont mis à jour.

Variables lues :
    GEC_ENV_CHEMIN
    GEC_PG_HOTE, GEC_PG_PORT, GEC_DB_NOM, GEC_DB_UTILISATEUR, GEC_DB_MDP
    GEC_ADMIN_MDP                       (création uniquement)
    GEC_HOST, GEC_PORT, GEC_HTTPS, GEC_DERRIERE_PROXY
"""

import base64
import os
import secrets
import sys
from urllib.parse import quote

REGLAGES_EXPOSITION = ("GEC_HOST", "GEC_PORT", "GEC_HTTPS", "GEC_DERRIERE_PROXY")


def _lire(chemin):
    valeurs = {}
    with open(chemin, encoding="utf-8-sig") as f:
        for ligne in f:
            ligne = ligne.strip()
            if ligne and not ligne.startswith("#") and "=" in ligne:
                cle, valeur = ligne.split("=", 1)
                valeurs[cle.strip()] = valeur.strip()
    return valeurs


def _ecrire(chemin, texte):
    # UTF-8 sans BOM, fins de ligne Windows : lisible par le Bloc-notes comme par GEC.
    with open(chemin, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(texte)


def _verifier_cle(valeurs):
    cle = valeurs.get("GEC_MASTER_KEY", "")
    try:
        return len(base64.b64decode(cle, validate=True)) == 32
    except Exception:
        return False


def _mettre_a_jour_exposition(chemin, env):
    lignes = open(chemin, encoding="utf-8-sig").read().splitlines()
    vus = set()
    for i, ligne in enumerate(lignes):
        cle = ligne.split("=", 1)[0].strip() if "=" in ligne else ""
        if cle in REGLAGES_EXPOSITION:
            lignes[i] = f"{cle}={env[cle]}"
            vus.add(cle)
    manquants = [c for c in REGLAGES_EXPOSITION if c not in vus]
    if manquants:
        lignes += ["", "# Exposition (installer-gec.ps1)"] + [f"{c}={env[c]}" for c in manquants]
    _ecrire(chemin, "\n".join(lignes) + "\n")


def main():
    env = os.environ
    chemin = env["GEC_ENV_CHEMIN"]

    if os.path.exists(chemin):
        valeurs = _lire(chemin)
        problemes = [c for c in ("DATABASE_URL", "SESSION_SECRET") if not valeurs.get(c)]
        if not _verifier_cle(valeurs):
            problemes.append("GEC_MASTER_KEY (doit être 32 octets en base64)")
        if problemes:
            print("ERREUR : .env existant incomplet ou invalide : " + ", ".join(problemes))
            print("Corrigez-le à la main : il n'est jamais régénéré, pour ne pas perdre "
                  "la clé qui chiffre les données.")
            return 2
        _mettre_a_jour_exposition(chemin, env)
        print(".env existant conservé (secrets inchangés), réglages d'exposition mis à jour.")
        return 0

    url = "postgresql://{u}:{m}@{h}:{p}/{b}".format(
        u=quote(env["GEC_DB_UTILISATEUR"], safe=""),
        m=quote(env["GEC_DB_MDP"], safe=""),
        h=env.get("GEC_PG_HOTE", "localhost"),
        p=env.get("GEC_PG_PORT", "5432"),
        b=quote(env["GEC_DB_NOM"], safe=""),
    )
    texte = f"""# GEC — configuration de production (créée par installer-gec.ps1)
# NE PAS PERDRE CE FICHIER : GEC_MASTER_KEY chiffre les données en base.
# Sans elle, les courriers et pièces jointes chiffrés sont illisibles définitivement.
# En garder une copie hors du serveur.

FLASK_ENV=production
DATABASE_URL={url}
SESSION_SECRET={secrets.token_hex(32)}
GEC_MASTER_KEY={base64.b64encode(secrets.token_bytes(32)).decode()}
GEC_PASSWORD_SALT={base64.b64encode(secrets.token_bytes(16)).decode()}

# Mot de passe du compte super admin « sa.gec001 », lu au premier démarrage uniquement.
ADMIN_PASSWORD={env["GEC_ADMIN_MDP"]}

# Exposition (installer-gec.ps1)
GEC_HOST={env["GEC_HOST"]}
GEC_PORT={env["GEC_PORT"]}
GEC_HTTPS={env["GEC_HTTPS"]}
GEC_DERRIERE_PROXY={env["GEC_DERRIERE_PROXY"]}
"""
    _ecrire(chemin, texte)
    print(".env créé avec des secrets neufs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
