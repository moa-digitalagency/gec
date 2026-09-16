"""Les fichiers texte doivent être lus et écrits en UTF-8 sur toutes les plateformes.

Sans `encoding=`, Python utilise l'encodage régional du système : UTF-8 sous
Linux, mais cp1252 sous Windows Server. Les accents y deviennent du charabia
(« Secrétaire » lu « SecrÃ©taire ») et les caractères absents de cp1252 font
planter l'écriture — une sauvegarde faite sous Linux restaurée sous Windows
corrompt donc la configuration sans la moindre erreur.
"""

import ast
import os
import subprocess

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fichiers_python_du_projet():
    sortie = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=RACINE, capture_output=True, text=True,
        encoding="utf-8", check=True,
    ).stdout
    return [f for f in sortie.split() if not f.startswith("tests/")]


def _mode(appel):
    if len(appel.args) >= 2 and isinstance(appel.args[1], ast.Constant):
        return appel.args[1].value
    for kw in appel.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return "r"


def _ouvertures_texte_sans_encodage(chemin):
    arbre = ast.parse(open(os.path.join(RACINE, chemin), encoding="utf-8").read())
    fautes = []
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Call):
            continue
        f = noeud.func
        est_open = isinstance(f, ast.Name) and f.id == "open"
        est_io_open = (
            isinstance(f, ast.Attribute) and f.attr == "open"
            and isinstance(f.value, ast.Name) and f.value.id == "io"
        )
        est_texte_pathlib = isinstance(f, ast.Attribute) and f.attr in ("read_text", "write_text")
        a_encodage = any(kw.arg == "encoding" for kw in noeud.keywords)
        if (est_open or est_io_open) and "b" not in str(_mode(noeud)) and not a_encodage:
            fautes.append(f"{chemin}:{noeud.lineno}")
        elif est_texte_pathlib and not a_encodage:
            fautes.append(f"{chemin}:{noeud.lineno}")
    return fautes


def test_aucun_fichier_texte_ouvert_sans_encodage():
    fautes = []
    for chemin in _fichiers_python_du_projet():
        fautes += _ouvertures_texte_sans_encodage(chemin)
    assert fautes == [], (
        "fichiers texte ouverts sans encoding= (cp1252 sous Windows) :\n  "
        + "\n  ".join(fautes)
    )


def test_env_utf8_avec_bom_et_accents(tmp_path, monkeypatch):
    """Le Bloc-notes de Windows Server 2016 enregistre en UTF-8 avec BOM."""
    from security.encryption import load_env_from_file

    for cle in ("GEC_TEST_PREMIERE", "GEC_TEST_ACCENTS"):
        monkeypatch.delenv(cle, raising=False)
    fichier = tmp_path / ".env"
    fichier.write_bytes(
        "GEC_TEST_PREMIERE=ouverte\nGEC_TEST_ACCENTS=Secrétaire Général — Kinshasa\n"
        .encode("utf-8-sig")
    )

    load_env_from_file(str(fichier))
    try:
        assert os.environ.get("GEC_TEST_PREMIERE") == "ouverte", (
            "la première variable n'est pas reconnue (BOM collé au nom)"
        )
        assert os.environ.get("GEC_TEST_ACCENTS") == "Secrétaire Général — Kinshasa"
    finally:
        for cle in ("GEC_TEST_PREMIERE", "GEC_TEST_ACCENTS", "﻿GEC_TEST_PREMIERE",
                    "ï»¿GEC_TEST_PREMIERE"):
            os.environ.pop(cle, None)
