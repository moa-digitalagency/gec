"""Point d'entrée WSGI pour Windows Server.

gunicorn (requirements.txt) ne fonctionne pas sur Windows : il importe `fcntl`,
absent de la bibliothèque standard Windows. Waitress est son équivalent de
production en Python pur, officiellement supporté sur Windows.

    python run_waitress.py

Variables d'environnement (toutes optionnelles) :
    GEC_HOST     interface d'écoute — défaut 127.0.0.1
                 À laisser en 127.0.0.1 quand IIS sert de proxy inverse :
                 l'application n'est alors jamais exposée directement.
    GEC_PORT     port d'écoute — défaut 5004
    GEC_THREADS  threads de traitement — défaut 8
"""

import os
import sys

# L'application construit des chemins relatifs ('static/uploads/...',
# 'security/temp', 'backups'). Lancée comme service Windows, le répertoire
# courant n'est pas celui du projet : on le force ici pour que ces chemins
# résolvent correctement, quel que soit le lanceur.
RACINE = os.path.dirname(os.path.abspath(__file__))
os.chdir(RACINE)
sys.path.insert(0, RACINE)

from waitress import serve  # noqa: E402
from app import app  # noqa: E402

if __name__ == "__main__":
    hote = os.environ.get("GEC_HOST", "127.0.0.1")
    port = int(os.environ.get("GEC_PORT", "5004"))
    threads = int(os.environ.get("GEC_THREADS", "8"))

    print(f"GEC — Waitress sur http://{hote}:{port} ({threads} threads)", flush=True)
    serve(app, host=hote, port=port, threads=threads)
