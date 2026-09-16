"""Maintient GEC en marche sous Windows Server.

Lancé au démarrage du serveur par la tâche planifiée « GEC » (voir
installer-gec.ps1). Il démarre Waitress et le relance s'il s'arrête :

- au redémarrage du serveur, GEC peut démarrer avant PostgreSQL, échouer à se
  connecter et s'arrêter — sans relance, il resterait arrêté ;
- la relance est faite ici, avec un délai croissant en cas d'échecs répétés,
  plutôt que confiée aux réglages de relance du Planificateur de tâches.

Sous Windows, arrêter un processus n'arrête pas ses enfants. Waitress est donc
placé dans un « objet job » fermé avec le superviseur : arrêter la tâche
arrête aussi Waitress, qui libère son port.
"""

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
JOURNAL = RACINE / "logs" / "gec.log"
TAILLE_MAX_JOURNAL = 20 * 1024 * 1024
JOURNAUX_CONSERVES = 5
DUREE_DEMARRAGE_SAIN = 60   # secondes : en deçà, l'arrêt compte comme un échec rapide
PAUSE_MAX = 120


def _job_qui_tue_ses_processus():
    """Objet job Windows : ses processus meurent quand le superviseur disparaît."""
    import ctypes
    from ctypes import wintypes

    class LimitesDeBase(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class CompteursES(ctypes.Structure):
        _fields_ = [(nom, ctypes.c_uint64) for nom in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class LimitesEtendues(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", LimitesDeBase),
            ("IoInfo", CompteursES),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]

    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    infos = LimitesEtendues()
    infos.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(infos), ctypes.sizeof(infos)):
        raise ctypes.WinError(ctypes.get_last_error())

    def rattacher(processus):
        if not kernel32.AssignProcessToJobObject(job, int(processus._handle)):
            raise ctypes.WinError(ctypes.get_last_error())

    return rattacher


def _noter(message):
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(JOURNAL, "a", encoding="utf-8") as journal:
        journal.write(f"[{horodatage}] [superviseur] {message}\n")


def _faire_tourner_les_journaux():
    if not JOURNAL.exists() or JOURNAL.stat().st_size < TAILLE_MAX_JOURNAL:
        return
    for rang in range(JOURNAUX_CONSERVES - 1, 0, -1):
        ancien = JOURNAL.with_name(f"{JOURNAL.name}.{rang}")
        if ancien.exists():
            ancien.replace(JOURNAL.with_name(f"{JOURNAL.name}.{rang + 1}"))
    JOURNAL.replace(JOURNAL.with_name(f"{JOURNAL.name}.1"))


def main():
    os.chdir(RACINE)
    rattacher = _job_qui_tue_ses_processus() if os.name == "nt" else None
    commande = [sys.executable, "-X", "utf8", str(RACINE / "run_waitress.py")]
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    echecs_rapides = 0

    while True:
        _faire_tourner_les_journaux()
        _noter("démarrage de GEC")
        debut = time.monotonic()
        with open(JOURNAL, "ab") as journal:
            processus = subprocess.Popen(
                commande, cwd=RACINE, stdout=journal, stderr=subprocess.STDOUT, **options)
            if rattacher:
                rattacher(processus)
            code = processus.wait()

        duree = time.monotonic() - debut
        echecs_rapides = echecs_rapides + 1 if duree < DUREE_DEMARRAGE_SAIN else 0
        pause = min(5 * 2 ** min(echecs_rapides, 5), PAUSE_MAX)
        _noter(f"GEC s'est arrêté (code {code}) après {duree:.0f} s — "
               f"redémarrage dans {pause} s")
        time.sleep(pause)


if __name__ == "__main__":
    main()
