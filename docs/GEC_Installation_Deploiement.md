# GEC — Installation et Déploiement (Linux)

*Mise à jour : septembre 2026*

> **Serveur Windows ?** Cette procédure concerne Linux (nginx, gunicorn, PM2).
> Pour Windows Server 2016, 2019 ou 2022, suivre
> **[GEC_Deploiement_Windows_Server.md](GEC_Deploiement_Windows_Server.md)** :
> installation en une commande PowerShell.

---

## Prérequis

| Logiciel | Version minimale |
|----------|-----------------|
| Python | 3.11+ |
| PostgreSQL | 14+ |
| Nginx | 1.18+ |
| gunicorn | 23+ |

---

## 1. Déploiement VPS (production)

### Cloner le dépôt

```bash
cd /var/websites
git clone https://github.com/moa-digitalagency/gec.git gec
cd gec
```

### Créer l'environnement virtuel

À exécuter **avec l'utilisateur qui fera tourner l'application, jamais avec `sudo`** :

```bash
python3 -m venv venv
venv/bin/python -m pip install --upgrade pip
venv/bin/python -m pip install -r requirements.txt
```

Python 3.11 à 3.14 sont supportés. Un venv créé avec `sudo` appartient à root :
toute installation ultérieure échoue alors avec `Permission denied` (voir
[Dépannage de l'installation](#7-dépannage-de-linstallation)).

### Fichier `.env`

Créer `/var/websites/gec/.env` (ne jamais committer) :

```env
FLASK_ENV=production
DATABASE_URL=postgresql://gec_user:motdepasse@localhost:5432/gec_db
SESSION_SECRET=<générer avec : python3 -c "import secrets; print(secrets.token_hex(32))">
GEC_MASTER_KEY=<clé de 32 octets en base64, voir ci-dessous>
GEC_PASSWORD_SALT=<16 octets en base64, voir ci-dessous>
ADMIN_PASSWORD=<mot de passe du compte super admin initial>
TRUSTED_PROXIES=127.0.0.1,::1
```

Générer les secrets **une seule fois** et les conserver précieusement :

```bash
python3 -c "import secrets; print('SESSION_SECRET=' + secrets.token_hex(32))"
python3 -c "import base64, secrets; print('GEC_MASTER_KEY=' + base64.b64encode(secrets.token_bytes(32)).decode())"
python3 -c "import base64, secrets; print('GEC_PASSWORD_SALT=' + base64.b64encode(secrets.token_bytes(16)).decode())"
```

`GEC_MASTER_KEY` doit décoder en **exactement 32 octets** : une valeur hexadécimale
(`secrets.token_hex(32)`) décode en 48 octets et l'application refuse de démarrer.
Une fois des données chiffrées en base, cette clé ne doit plus jamais changer.

Variables optionnelles :

```env
RESEND_API_KEY=re_xxxxxxxxxxxx
FIRST_ADMIN_USERNAME=sa.gec001
FIRST_ADMIN_EMAIL=admin@gec.cd
```

### Créer la base de données PostgreSQL

```bash
sudo -u postgres psql
```

```sql
CREATE USER gec_user WITH PASSWORD 'motdepasse';
CREATE DATABASE gec_db OWNER gec_user;
GRANT ALL PRIVILEGES ON DATABASE gec_db TO gec_user;
\q
```

### Initialiser la base de données

```bash
source venv/bin/activate
python init_db.py
```

Ce script est **idempotent** — sûr à relancer sur une DB existante. Il :
1. Crée toutes les tables (`db.create_all()`)
2. Applique les migrations automatiques (colonnes manquantes, nouvelles tables)
3. Insère les données par défaut (statuts, rôles, permissions, templates email)
4. Crée le compte super admin (si absent)

### Script de démarrage PM2

Créer `/var/websites/gec/start-gec.sh` :

```bash
#!/bin/bash
cd /var/websites/gec
set -a; [ -f .env ] && source .env; set +a
source venv/bin/activate
exec gunicorn --bind 0.0.0.0:5004 \
  --workers 3 \
  --timeout 120 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  main:app
```

```bash
chmod +x start-gec.sh
mkdir -p logs
pm2 start start-gec.sh --name gec
pm2 save
```

### Configuration Nginx

`/etc/nginx/sites-available/gec.conf` :

```nginx
server {
    listen 80;
    server_name votre-domaine.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name votre-domaine.com;

    ssl_certificate /etc/letsencrypt/live/votre-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.com/privkey.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5004;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/websites/gec/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /uploads/ {
        internal;
        alias /var/websites/gec/uploads/;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/gec.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot certonly -d votre-domaine.com --nginx
sudo systemctl reload nginx
```

---

## 2. Mise à jour en production

```bash
# Workflow obligatoire — ne JAMAIS modifier les fichiers directement sur le VPS
# 1. Modifier en local → 2. commit + push → 3. pull VPS

ssh -i ~/.ssh/vps1_access root@168.231.86.201
cd /var/websites/gec
git pull origin main
source venv/bin/activate
pip install -r requirements.txt   # si nouvelles dépendances
python init_db.py                  # si nouvelles migrations
pm2 restart gec
pm2 logs gec --lines 20           # vérifier démarrage
```

---

## 3. Variables d'environnement — référence complète

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `FLASK_ENV` | Oui | `production` en prod, `development` en local |
| `DATABASE_URL` | Oui (prod) | URL PostgreSQL complète |
| `SESSION_SECRET` | Oui (prod) | Clé secrète Flask — minimum 32 chars hex |
| `GEC_MASTER_KEY` | Oui (prod) | Clé maître AES, 32 octets en base64. Absente : clé temporaire perdue au redémarrage, données chiffrées illisibles |
| `GEC_PASSWORD_SALT` | Recommandé | 16 octets en base64. Absente : message CRITICAL à chaque démarrage |
| `ADMIN_PASSWORD` | Oui (1er démarrage) | Mot de passe du super admin créé au premier démarrage (défaut : `TempPassword123!`) |
| `FIRST_ADMIN_USERNAME` | Non | Identifiant du super admin initial (défaut : `sa.gec001`) |
| `TRUSTED_PROXIES` | Recommandé | IPs proxy de confiance (défaut: `127.0.0.1,::1`) |
| `GEC_HTTPS` | Non | `0` si le site est servi en HTTP simple (intranet sans certificat) : sans cela, le cookie de session est réservé à HTTPS et aucune connexion n'est possible. Défaut : `1` |
| `GEC_DERRIERE_PROXY` | Non | `0` si GEC est exposé directement, sans nginx ni IIS : les en-têtes `X-Real-IP` / `X-Forwarded-For` sont alors ignorés, car fournis par le client lui-même. Défaut : `1` |
| `RESEND_API_KEY` | Non | Clé API Resend pour envoi d'emails |

---

## 4. Migrations automatiques

Le système de migration est dans `utils/migrations.py`. Il est appelé automatiquement par `init_db.py` et au démarrage de l'application.

Chaque migration est **idempotente** : elle vérifie si la colonne/table existe avant de l'ajouter. Aucune donnée n'est perdue.

Migrations actuelles couvertes :
- Colonnes chiffrement utilisateurs (`email_encrypted`, `nom_complet_encrypted`, etc.)
- Colonnes chiffrement courriers (`objet_encrypted`, `expediteur_encrypted`, etc.)
- Tables : `courrier_attachment`, `tag`, `courrier_tag`, `courrier_signature`
- Colonnes 2FA TOTP (`totp_secret`, `totp_enabled`, `totp_pending_secret`)
- Colonnes rappels/échéances (`due_date`, `reminder_sent_at`)
- Colonnes paramètres système (`resend_api_key`, `email_provider`, `whatsapp_number`, etc.)
- Index GIN full-text PostgreSQL (`idx_courrier_fts`)

---

## 5. Compte super admin par défaut

Créé automatiquement au premier démarrage de l'application (et par `init_db.py`) s'il n'existe pas :

| Champ | Valeur |
|-------|--------|
| Identifiant | `FIRST_ADMIN_USERNAME`, par défaut `sa.gec001` |
| Mot de passe | `ADMIN_PASSWORD`, par défaut `TempPassword123!` |
| Rôle | `super_admin` |

Définir `ADMIN_PASSWORD` **avant le premier démarrage** : il n'est lu qu'à la création
du compte, le modifier ensuite dans `.env` ne change plus rien.

**Changer le mot de passe immédiatement après la première connexion.**

Le super admin peut gérer les utilisateurs, la configuration système et la sécurité.
**Il ne peut PAS accéder aux courriers** (règle inviolable — voir `docs/GEC_Securite.md`).

---

## 6. Dépendances complètes

Voir `requirements.txt`. Dépendances clés :

| Package | Usage |
|---------|-------|
| Flask 3.1 + extensions | Framework web |
| SQLAlchemy 2.0 + psycopg2-binary | ORM + connecteur PostgreSQL |
| cryptography + pycryptodome | Chiffrement AES-256 des données sensibles |
| gunicorn | Serveur WSGI production |
| reportlab + Pillow | Génération PDF |
| pandas + xlsxwriter | Export Excel |
| resend | Envoi d'emails via API |
| pyotp + qrcode | 2FA TOTP |
| PyYAML | Fichiers de configuration YAML |
| pyzipper | Archives ZIP chiffrées (sauvegardes) |

---

## 7. Dépannage de l'installation

### `Permission denied: '.../venv/lib/python3.x/site-packages/...'`

Le venv (ou une partie) a été créé ou modifié avec `sudo` et appartient à root.
Ne pas contourner avec `sudo pip` : cela aggrave le problème. Rendre le dossier à
l'utilisateur, puis réinstaller :

```bash
deactivate 2>/dev/null
sudo chown -R "$USER":"$USER" ~/gec
venv/bin/python -m pip install -r requirements.txt
```

Si le venv reste incohérent, le recréer (aucune donnée n'y est stockée) :
`rm -rf venv && python3 -m venv venv`, puis reprendre l'installation.

### `sudo: python: command not found`

Sous `sudo`, le venv n'est plus actif et Ubuntu ne fournit que `python3`. Il n'y a
de toute façon aucune raison d'utiliser `sudo` pour installer les dépendances :
appeler directement l'interpréteur du venv, `venv/bin/python -m pip ...`.

### `No matching distribution found for psycopg2-binary` (ou pandas, PyYAML)

Version de Python plus récente que les dépendances épinglées. Les versions actuelles
de `requirements.txt` fournissent des binaires pour Python 3.11 à 3.14 ; mettre le
dépôt à jour (`git pull`) avant d'installer.

### `Worker failed to boot` au premier démarrage

Corrigé : plusieurs workers gunicorn initialisaient la base vide en même temps
(`UniqueViolation` sur `pg_class`). L'initialisation est désormais sérialisée par un
verrou PostgreSQL. Mettre le dépôt à jour si l'erreur apparaît sur une version ancienne.

### `GEC_MASTER_KEY invalide : ... doit être 32 bytes`

La clé n'est pas du base64 de 32 octets. La régénérer avec la commande de la section
« Fichier `.env` » **tant qu'aucune donnée n'est chiffrée en base**.

