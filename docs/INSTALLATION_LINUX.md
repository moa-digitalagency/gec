# Installation GEC Mines - Linux (Ubuntu/Debian/CentOS/RHEL)

## Méthode Automatique (Recommandée)

### Installation One-Click
```bash
curl -fsSL https://raw.githubusercontent.com/moa-digitalagency/gec/main/install-gec-linux.sh | bash
```

## Installation Manuelle

### Ubuntu/Debian

#### Étape 1: Mise à jour du système
```bash
sudo apt update && sudo apt upgrade -y
```

#### Étape 2: Installation des dépendances système
```bash
sudo apt install -y python3.11 python3.11-venv python3-pip git wget curl build-essential libpq-dev
```

#### Étape 3: Téléchargement du code source
```bash
git clone https://github.com/moa-digitalagency/gec.git
cd gec
```

#### Étape 4: Configuration de l'environnement
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -r project-dependencies.txt
```

### CentOS/RHEL/Fedora

#### Étape 1: Installation des dépendances
```bash
# CentOS/RHEL 8+
sudo dnf install -y python3.11 python3-pip git gcc postgresql-devel

# CentOS/RHEL 7
sudo yum install -y python3 python3-pip git gcc postgresql-devel

# Fedora
sudo dnf install -y python3.11 python3-pip git gcc postgresql-devel
```

#### Étape 2: Suite de l'installation
```bash
git clone https://github.com/moa-digitalagency/gec.git
cd gec
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -r project-dependencies.txt
```

## Configuration Production

### Base de Données PostgreSQL

#### Installation PostgreSQL
```bash
# Ubuntu/Debian
sudo apt install -y postgresql postgresql-contrib

# CentOS/RHEL
sudo dnf install -y postgresql-server postgresql-contrib
sudo postgresql-setup initdb
```

#### Configuration de la base de données
```bash
sudo -u postgres psql
```
```sql
CREATE DATABASE gecmines;
CREATE USER gecmines WITH PASSWORD 'motdepasse_securise';
GRANT ALL PRIVILEGES ON DATABASE gecmines TO gecmines;
\q
```

### Configuration Systemd
Créez le fichier `/etc/systemd/system/gecmines.service`:
```ini
[Unit]
Description=GEC Mines - Système de Gestion du Courrier
After=network.target postgresql.service

[Service]
Type=simple
User=gecmines
Group=gecmines
WorkingDirectory=/opt/gecmines
Environment=PATH=/opt/gecmines/.venv/bin
ExecStart=/opt/gecmines/.venv/bin/python main.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Installation système
```bash
# Créer l'utilisateur système
sudo useradd -r -s /bin/false gecmines

# Copier l'application
sudo cp -r gec /opt/gecmines
sudo chown -R gecmines:gecmines /opt/gecmines

# Activer et démarrer le service
sudo systemctl enable gecmines
sudo systemctl start gecmines
```

### Configuration Nginx (Reverse Proxy)

#### Installation Nginx
```bash
# Ubuntu/Debian
sudo apt install -y nginx

# CentOS/RHEL
sudo dnf install -y nginx
```

#### Configuration Nginx
Créez `/etc/nginx/sites-available/gecmines`:
```nginx
server {
    listen 80;
    server_name votre-domaine.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    location /static/ {
        alias /opt/gecmines/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
# Activer le site
sudo ln -s /etc/nginx/sites-available/gecmines /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Configuration SSL avec Let's Encrypt
```bash
# Installer Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtenir le certificat SSL
sudo certbot --nginx -d votre-domaine.com
```

## Configuration Variables d'Environnement

### Fichier .env production
```bash
sudo tee /opt/gecmines/.env << EOF
DATABASE_URL=postgresql://gecmines:motdepasse_securise@localhost/gecmines
SESSION_SECRET=$(openssl rand -hex 32)
GEC_MASTER_KEY=$(openssl rand -hex 32)
GEC_PASSWORD_SALT=$(openssl rand -hex 16)

# Configuration SMTP
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_EMAIL=noreply@votre-domaine.com
SMTP_PASSWORD=votre-mot-de-passe-app
EOF

sudo chown gecmines:gecmines /opt/gecmines/.env
sudo chmod 600 /opt/gecmines/.env
```

## Sauvegarde Automatique

### Script de sauvegarde
Créez `/opt/gecmines/backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/opt/gecmines/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="gecmines_backup_$DATE.tar.gz"

mkdir -p $BACKUP_DIR

# Sauvegarde base de données
sudo -u postgres pg_dump gecmines > $BACKUP_DIR/db_$DATE.sql

# Sauvegarde fichiers
tar -czf $BACKUP_DIR/$BACKUP_FILE \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    /opt/gecmines

# Nettoyer les sauvegardes anciennes (> 30 jours)
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Sauvegarde créée: $BACKUP_FILE"
```

### Tâche cron pour sauvegarde automatique
```bash
# Ajouter au crontab
sudo crontab -e

# Sauvegarde quotidienne à 2h du matin
0 2 * * * /opt/gecmines/backup.sh
```

## Surveillance et Monitoring

### Monitoring avec systemctl
```bash
# Statut du service
sudo systemctl status gecmines

# Logs du service
sudo journalctl -u gecmines -f

# Redémarrage automatique
sudo systemctl restart gecmines
```

### Monitoring des ressources
```bash
# CPU et mémoire
sudo htop -p $(pgrep -f "python.*main.py")

# Espace disque
sudo du -sh /opt/gecmines/
sudo df -h
```

## Pare-feu et Sécurité

### Configuration UFW (Ubuntu)
```bash
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### Configuration Firewalld (CentOS/RHEL)
```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## Dépannage Linux

### Problème de permissions
```bash
sudo chown -R gecmines:gecmines /opt/gecmines
sudo chmod -R 755 /opt/gecmines
sudo chmod 600 /opt/gecmines/.env
```

### Erreur de dépendances Python
```bash
# Réinstaller les dépendances
source /opt/gecmines/.venv/bin/activate
pip install --force-reinstall -r project-dependencies.txt
```

### Problème PostgreSQL
```bash
# Redémarrer PostgreSQL
sudo systemctl restart postgresql

# Vérifier les connexions
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity WHERE datname='gecmines';"
```

## Support Technique
- **Développé par**: MOA Digital Agency LLC
- **Auteur**: AIsance KALONJI wa KALONJI
- **Contact**: moa@myoneart.com
- **Téléphone**: +212 699 14 000 1 / +243 86 049 33 45
- **Site Web**: myoneart.com