"""Génère les mots de passe de l'installation rapide de GEC.

Sortie JSON : {"admin": ..., "base": ..., "postgres": ...}.

Les mots de passe respectent la politique de GEC (security/auth.py,
validate_password_strength) : au moins 12 caractères, majuscule, minuscule,
chiffre, caractère spécial, sans suite ni répétition ni mot courant.

Alphabet choisi pour être recopiable sans ambiguïté (ni 0/O, ni 1/l/I) et sûr
partout où ces mots de passe transitent : fichier .env, URL de connexion encodée,
fichier d'options de l'installateur PostgreSQL, paramètres PowerShell.
"""

import json
import re
import secrets
import sys

MAJUSCULES = "ABCDEFGHJKLMNPQRSTUVWXYZ"
MINUSCULES = "abcdefghijkmnopqrstuvwxyz"
CHIFFRES = "23456789"
SPECIAUX = "-_!@"
ALPHABET = MAJUSCULES + MINUSCULES + CHIFFRES + SPECIAUX
LONGUEUR = 20

# Mêmes motifs refusés que validate_password_strength (appliqués en minuscules).
MOTIFS_PREVISIBLES = (
    r"(012|123|234|345|456|567|678|789)",
    r"(abc|bcd|cde|def|efg|fgh|ghi)",
    r"(password|admin|user|login)",
    r"(\w)\1{2,}",
)


def _acceptable(mot):
    return (
        any(c in MAJUSCULES for c in mot)
        and any(c in MINUSCULES for c in mot)
        and any(c in CHIFFRES for c in mot)
        and any(c in SPECIAUX for c in mot)
        and mot[0] not in SPECIAUX  # jamais en tête : lisibilité, et « - » ressemble à une option
        and not any(re.search(m, mot.lower()) for m in MOTIFS_PREVISIBLES)
    )


def generer(longueur=LONGUEUR):
    while True:
        mot = "".join(secrets.choice(ALPHABET) for _ in range(longueur))
        if _acceptable(mot):
            return mot


def main():
    print(json.dumps({"admin": generer(), "base": generer(), "postgres": generer()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
