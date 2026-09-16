"""Réglages d'exposition : HTTP simple d'intranet, et proxy (ou non) devant GEC.

Deux défauts constatés sur un déploiement servi en HTTP simple, sans proxy :

- le cookie de session est marqué Secure en production : un navigateur ne le
  renvoie jamais en HTTP, et personne ne peut se connecter (« Session de sécurité
  expirée ») ;
- l'adresse du client est lue dans X-Real-IP / X-Forwarded-For, que le client
  fournit lui-même quand aucun proxy ne les réécrit : il peut changer d'adresse à
  chaque essai et contourner la limitation des tentatives de connexion.
"""

import json
import os
import subprocess
import sys

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _config_au_demarrage(tmp_path, **env):
    """Importe l'application dans un processus neuf (la config est lue à l'import)."""
    code = (
        "import json, sys; from app import app; "
        "from werkzeug.middleware.proxy_fix import ProxyFix; "
        "print('RESULTAT=' + json.dumps({"
        "'cookie_secure': app.config['SESSION_COOKIE_SECURE'], "
        "'proxy_fix': isinstance(app.wsgi_app, ProxyFix)}))"
    )
    environnement = {
        k: v for k, v in os.environ.items()
        if k not in ("GEC_HTTPS", "GEC_DERRIERE_PROXY", "FLASK_ENV", "DATABASE_URL")
    }
    environnement.update({
        "FLASK_ENV": "development",
        "DATABASE_URL": f"sqlite:///{tmp_path / 'config.db'}",
        "SESSION_SECRET": "test",
        "PYTHONUTF8": "1",
    })
    environnement.update(env)
    sortie = subprocess.run(
        [sys.executable, "-c", code], cwd=RACINE, env=environnement,
        capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    lignes = [l for l in sortie.stdout.splitlines() if l.startswith("RESULTAT=")]
    assert lignes, f"import de l'application en échec :\n{sortie.stderr[-2000:]}"
    return json.loads(lignes[-1][len("RESULTAT="):])


def test_production_https_par_defaut(tmp_path):
    # En production PostgreSQL est exigé : on vérifie le comportement du cookie via
    # la même fonction que app.py, sans ouvrir de base.
    from app import cookie_session_securise

    assert cookie_session_securise({"FLASK_ENV": "production"}) is True
    assert cookie_session_securise({"FLASK_ENV": "production", "GEC_HTTPS": "1"}) is True


def test_intranet_http_autorise_la_connexion(tmp_path):
    from app import cookie_session_securise

    assert cookie_session_securise({"FLASK_ENV": "production", "GEC_HTTPS": "0"}) is False
    assert cookie_session_securise({"FLASK_ENV": "development"}) is False


def test_proxyfix_actif_par_defaut(tmp_path):
    config = _config_au_demarrage(tmp_path)
    assert config["proxy_fix"] is True


def test_proxyfix_retire_sans_proxy(tmp_path):
    config = _config_au_demarrage(tmp_path, GEC_DERRIERE_PROXY="0")
    assert config["proxy_fix"] is False


@pytest.mark.parametrize("entete", ["HTTP_X_REAL_IP", "HTTP_X_FORWARDED_FOR"])
def test_adresse_client_non_falsifiable_sans_proxy(app, monkeypatch, entete):
    from security.auth import get_client_ip

    monkeypatch.setenv("GEC_DERRIERE_PROXY", "0")
    with app.test_request_context(
        "/", environ_base={"REMOTE_ADDR": "127.0.0.1", entete: "203.0.113.66"}
    ):
        assert get_client_ip() == "127.0.0.1"


def test_adresse_client_du_proxy_conservee_par_defaut(app, monkeypatch):
    """Derrière nginx (VPS) : comportement inchangé."""
    from security.auth import get_client_ip

    monkeypatch.delenv("GEC_DERRIERE_PROXY", raising=False)
    with app.test_request_context(
        "/", environ_base={"REMOTE_ADDR": "127.0.0.1", "HTTP_X_REAL_IP": "203.0.113.66"}
    ):
        assert get_client_ip() == "203.0.113.66"
