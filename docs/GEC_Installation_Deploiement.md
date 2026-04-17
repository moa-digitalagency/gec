# GEC — Installation et Déploiement

*Mise à jour : Avril 2026*

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

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Fichier `.env`

Créer `/var/websites/gec/.env` (ne jamais committer) :

```env
FLASK_ENV=production
DATABASE_URL=postgresql://gec_user:motdepasse@localhost:5432/gec_db
SESSION_SECRET=<générer avec : python3 -c "import secrets; print(secrets.token_hex(32))">
GEC_MASTER_KEY=<générer avec : python3 -c "import secrets; print(secrets.token_hex(32))">
TRUSTED_PROXIES=127.0.0.1,::1
```

Variables optionnelles :

```env
RESEND_API_KEY=re_xxxxxxxxxxxx
DEFAULT_ADMIN_PASSWORD=MotDePasseAdmin123!
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
| `GEC_MASTER_KEY` | Recommandé | Clé maître AES pour chiffrement des champs sensibles |
| `TRUSTED_PROXIES` | Recommandé | IPs proxy de confiance (défaut: `127.0.0.1,::1`) |
| `RESEND_API_KEY` | Non | Clé API Resend pour envoi d'emails |
| `DEFAULT_ADMIN_PASSWORD` | Non | Mot de passe super admin initial (défaut généré) |

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

Créé automatiquement par `init_db.py` si absent :

| Champ | Valeur par défaut |
|-------|------------------|
| Username | `admin` |
| Mot de passe | Valeur de `DEFAULT_ADMIN_PASSWORD` ou généré aléatoirement |
| Rôle | `super_admin` |

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
