"""Les mots de passe générés par l'installation rapide respectent la politique de GEC."""

import importlib.util
import json
import os
import subprocess
import sys
from urllib.parse import quote, unquote

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.join(RACINE, "deploy", "windows", "mots_de_passe.py")


def _charger():
    spec = importlib.util.spec_from_file_location("mots_de_passe", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mots_de_passe_acceptes_par_la_politique_de_gec():
    from security.auth import validate_password_strength

    generateur = _charger()
    refus = []
    for _ in range(300):
        mot = generateur.generer()
        valide, message = validate_password_strength(mot)
        if not valide:
            refus.append((mot, message))
    assert refus == [], f"mots de passe refusés par GEC : {refus[:3]}"


def test_mots_de_passe_distincts_et_sans_caractere_problematique():
    sortie = subprocess.run(
        [sys.executable, MODULE], capture_output=True, text=True, encoding="utf-8", check=True
    ).stdout
    mots = json.loads(sortie)
    assert set(mots) == {"admin", "base", "postgres"}
    assert len(set(mots.values())) == 3
    for mot in mots.values():
        assert len(mot) == 20
        # Rien qui casse un .env, une URL, un fichier d'options ou une ligne PowerShell.
        assert not set(mot) & set(" \"'`$%^&|<>;=#\\/:,")
        assert unquote(quote(mot, safe="")) == mot
