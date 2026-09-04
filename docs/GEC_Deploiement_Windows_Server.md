# GEC — Déploiement en production sur Windows Server

*Mise à jour : Septembre 2026*

Cette procédure couvre Windows Server 2016, 2019 et 2022. Elle complète
`GEC_Installation_Deploiement.md`, qui décrit le déploiement Linux (nginx + gunicorn + PM2).

---

## Ce qui change par rapport au déploiement Linux

| Rôle | Linux (VPS) | Windows Server |
|------|-------------|----------------|
| Serveur WSGI | gunicorn | **Waitress** — gunicorn importe `fcntl`, absent de Windows |
| Gestionnaire de service | PM2 | **NSSM** (service Windows natif) |
| Proxy inverse | nginx | **IIS** + ARR + URL Rewrite |
| Certificat TLS | Let's Encrypt (certbot) | win-acme, ou certificat interne de l'organisation |
| Activation du venv | `source .venv/bin/activate` | `.\.venv\Scripts\Activate.ps1` |

---

## Prérequis à installer sur le serveur

| Logiciel | Version | Remarque |
|----------|---------|----------|
| Python | 3.11 ou 3.12 | Cocher **« Add python.exe to PATH »** à l'installation |
| PostgreSQL | 14+ | Installer aussi les *Command Line Tools* (`pg_dump`, `psql`) |
| Git pour Windows | à jour | Requis par la fonction de mise à jour intégrée |
| NSSM | 2.24+ | https://nssm.cc — pour exécuter GEC comme service |
| IIS | rôle Windows | + modules **ARR 3.0** et **URL Rewrite 2.1** |

---

## 1. Récupérer le code

```powershell
# Emplacement conseillé : hors des profils utilisateur
New-Item -ItemType Directory -Force -Path C:\inetpub\gec
cd C:\inetpub\gec
git clone https://github.com/moa-digitalagency/gec.git .
```

## 2. Environnement virtuel et dépendances

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> **L'erreur `.venv/bin/activate n'est pas reconnu`** vient du chemin : `bin/` est
> la convention Linux/macOS. Sur Windows, les exécutables du venv sont dans
> `Scripts\`. Si PowerShell refuse d'exécuter le script :
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

`requirements.txt` sélectionne automatiquement le bon serveur WSGI :
gunicorn sur Linux, Waitress sur Windows (marqueurs `sys_platform`).

## 3. Base de données

```powershell
# Depuis un shell psql (adapter le mot de passe)
psql -U postgres -c "CREATE DATABASE gec_db;"
psql -U postgres -c "CREATE USER gec_user WITH PASSWORD 'MotDePasseFort';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE gec_db TO gec_user;"
```

Les tables et les colonnes sont créées automatiquement au premier démarrage
(`db.create_all()` puis `utils/migrations.py`). Aucune migration manuelle n'est requise.

## 4. Fichier `.env`

À créer à la racine `C:\inetpub\gec\.env`. Générer les deux secrets **sur le serveur**,
puis les conserver hors du dépôt :

```powershell
# Clé maîtresse de chiffrement (32 octets en base64) et sel de mots de passe
python -c "import base64,os;print('GEC_MASTER_KEY=' + base64.b64encode(os.urandom(32)).decode())"
python -c "import base64,os;print('GEC_PASSWORD_SALT=' + base64.b64encode(os.urandom(16)).decode())"
python -c "import secrets;print('SESSION_SECRET=' + secrets.token_hex(32))"
```

Contenu attendu :

```
FLASK_ENV=production
DATABASE_URL=postgresql://gec_user:MotDePasseFort@localhost:5432/gec_db
SESSION_SECRET=<valeur générée>
GEC_MASTER_KEY=<valeur générée>
GEC_PASSWORD_SALT=<valeur générée>
ADMIN_PASSWORD=<mot de passe du compte initial>
```

> `GEC_MASTER_KEY` et `GEC_PASSWORD_SALT` doivent être du **base64 valide**, sinon
> l'application refuse de démarrer (fail-fast volontaire). Une fois des données
> chiffrées en base, ces valeurs ne doivent plus jamais changer : les sauvegarder
> avec le même soin que la base elle-même.

## 5. Premier démarrage en avant-plan

```powershell
.\.venv\Scripts\Activate.ps1
python run_waitress.py
```

Attendu : `GEC — Waitress sur http://127.0.0.1:5004 (8 threads)`.
Vérifier depuis le serveur :

```powershell
curl.exe -s -o NUL -w "%{http_code}`n" http://127.0.0.1:5004/login   # doit afficher 200
```

Puis arrêter avec Ctrl+C avant de passer en service.

## 6. Exécuter GEC comme service Windows (NSSM)

```powershell
nssm install GEC "C:\inetpub\gec\.venv\Scripts\python.exe" "C:\inetpub\gec\run_waitress.py"
nssm set GEC AppDirectory C:\inetpub\gec
nssm set GEC DisplayName "GEC - Gestion Electronique du Courrier"
nssm set GEC Start SERVICE_AUTO_START
nssm set GEC AppStdout C:\inetpub\gec\logs\service-out.log
nssm set GEC AppStderr C:\inetpub\gec\logs\service-err.log
nssm set GEC AppRotateFiles 1
nssm start GEC
```

`AppDirectory` n'est pas optionnel : l'application construit des chemins relatifs
(`static\uploads\`, `security\temp`, `backups`). Sans lui, les fichiers atterrissent
dans `C:\Windows\System32`.

Le compte du service doit avoir le **droit d'écriture** sur `static\uploads`,
`security\temp`, `backups` et `logs`, et `pg_dump.exe` doit être dans son `PATH`
(sinon la sauvegarde intégrée échoue silencieusement).

## 7. IIS en proxy inverse

Créer un site IIS pointant sur un dossier vide (IIS ne sert aucun fichier ici, il
relaie tout vers Waitress), puis :

1. **IIS Manager → serveur → Application Request Routing Cache → Server Proxy Settings** →
   cocher *Enable proxy*.
2. Déposer le `web.config` fourni à la racine du site.

Le `web.config` livré (`deploy/windows/web.config`) relaie tout vers `127.0.0.1:5004`
et transmet les en-têtes `X-Forwarded-For` / `X-Forwarded-Proto`, nécessaires pour
que la journalisation d'audit enregistre la vraie adresse IP des utilisateurs et non
`127.0.0.1`.

### HTTPS

- **Serveur exposé sur Internet** : win-acme (`wacs.exe`) génère et renouvelle un
  certificat Let's Encrypt directement dans IIS.
- **Serveur en intranet** : utiliser le certificat de l'autorité interne de
  l'organisation ; Let's Encrypt ne peut pas valider un nom non public.

Dans les deux cas, ajouter une règle de redirection HTTP → HTTPS et n'ouvrir le
port 5004 sur aucune interface externe : Waitress n'écoute que sur `127.0.0.1`.

## 8. Mises à jour

```powershell
cd C:\inetpub\gec
git pull origin main
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
nssm restart GEC
```

Les migrations de schéma s'appliquent au redémarrage.

---

## Points de vigilance propres à Windows

### Pièces jointes déchiffrées — à traiter avant une mise en production

GEC déchiffre une pièce jointe dans `security\temp\` pour la servir, puis supprime
le fichier temporaire. Sous Windows, un fichier encore ouvert **ne peut pas être
supprimé** (`WinError 32`) : la suppression échoue, et l'exception est absorbée
silencieusement par le code. Les pièces jointes déchiffrées s'accumulent donc **en
clair** dans `security\temp\`, ce qui annule la protection du chiffrement au repos.

Sous Linux le problème n'existe pas : POSIX autorise la suppression d'un fichier ouvert.

Tant que le correctif n'est pas appliqué, prévoir une tâche planifiée de purge :

```powershell
$purge = {
  Get-ChildItem C:\inetpub\gec\security\temp -File -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddMinutes(-15) } |
    Remove-Item -Force -ErrorAction SilentlyContinue
}
```
à planifier toutes les 15 minutes. **C'est un palliatif, pas une solution** :
les fichiers restent en clair sur le disque entre deux purges.

### Antivirus

Exclure `static\uploads\` et `security\temp\` de l'analyse en temps réel : un
antivirus qui verrouille un fichier pendant son écriture provoque des échecs
d'upload intermittents, difficiles à diagnostiquer.

### Fuseau horaire et encodage

- Les horodatages d'audit sont en UTC ; régler le fuseau du serveur ne les modifie pas.
- PowerShell 5.1 écrit en UTF-16 par défaut : créer le `.env` avec un éditeur en
  **UTF-8 sans BOM**, sinon la première variable est lue avec un préfixe invisible.
