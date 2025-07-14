# Guide d'Installation VPS - GEC Mines
## Installation Complète sur Serveur Privé Virtuel

---

## 📋 Prérequis Système

### Serveur VPS
- **OS** : Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **RAM** : Minimum 2GB (recommandé 4GB)
- **Stockage** : Minimum 20GB SSD
- **CPU** : 2 vCores minimum
- **Accès root** ou sudo

### Logiciels requis
- Python 3.8+
- PostgreSQL 13+ (ou MySQL 8.0+)
- Nginx
- Certbot (pour SSL)
- Git

---

## 🔧 Étape 1 : Préparation du serveur

### 1.1 Mise à jour système
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
# ou pour CentOS 8+
sudo dnf update -y
```

### 1.2 Installation des dépendances
```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip python3-venv git nginx postgresql postgresql-contrib certbot python3-certbot-nginx ufw htop curl wget unzip

# CentOS/RHEL
sudo dnf install -y python3 python3-pip git nginx postgresql postgresql-server postgresql-contrib certbot python3-certbot-nginx firewalld htop curl wget unzip
```

### 1.3 Configuration firewall
```bash
# Ubuntu (UFW)
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable

# CentOS (firewalld)
sudo systemctl enable firewalld
sudo systemctl start firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## 🗃️ Étape 2 : Configuration PostgreSQL

### 2.1 Initialisation PostgreSQL
```bash
# Ubuntu/Debian (auto-initialisé)
sudo systemctl enable postgresql
sudo systemctl start postgresql

# CentOS/RHEL
sudo postgresql-setup --initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### 2.2 Configuration base de données
```bash
# Accès PostgreSQL
sudo -u postgres psql

-- Dans PostgreSQL
CREATE DATABASE gec_mines;
CREATE USER gec_user WITH ENCRYPTED PASSWORD 'mot_de_passe_securise';
GRANT ALL PRIVILEGES ON DATABASE gec_mines TO gec_user;
ALTER USER gec_user CREATEDB;
\q
```

### 2.3 Configuration authentification
```bash
# Éditer pg_hba.conf
sudo nano /etc/postgresql/13/main/pg_hba.conf

# Ajouter cette ligne après les règles locales :
local   gec_mines   gec_user   md5

# Redémarrer PostgreSQL
sudo systemctl restart postgresql
```

---

## 📥 Étape 3 : Installation de l'application

### 3.1 Création utilisateur système
```bash
# Créer utilisateur dédié
sudo adduser gecmines
sudo usermod -aG sudo gecmines

# Passer à l'utilisateur gecmines
sudo su - gecmines
```

### 3.2 Clonage et configuration
```bash
# Cloner le projet
git clone https://github.com/votre-repo/gec-mines.git
cd gec-mines

# Créer environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer dépendances
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3 Configuration environnement
```bash
# Créer fichier .env
nano .env
```

Contenu du fichier `.env` :
```bash
# Base de données
DATABASE_URL=postgresql://gec_user:mot_de_passe_securise@localhost/gec_mines

# Sécurité
SESSION_SECRET=votre_secret_tres_long_et_aleatoire_unique

# Flask
FLASK_ENV=production
FLASK_DEBUG=False

# Chemins
UPLOAD_FOLDER=/home/gecmines/gec-mines/uploads
EXPORT_FOLDER=/home/gecmines/gec-mines/exports

# Performance
SQLALCHEMY_ENGINE_OPTIONS='{"pool_size": 20, "pool_recycle": 3600}'
```

### 3.4 Initialisation base de données
```bash
# Activer environnement virtuel si pas déjà fait
source venv/bin/activate

# Initialiser les tables
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('✅ Base de données initialisée')
"

# Créer dossiers nécessaires
mkdir -p uploads exports backups logs
chmod 755 uploads exports backups logs
```

---

## 🚀 Étape 4 : Configuration Gunicorn

### 4.1 Installation Gunicorn
```bash
# Dans l'environnement virtuel
pip install gunicorn
```

### 4.2 Configuration Gunicorn
```bash
# Créer fichier de configuration
nano gunicorn.conf.py
```

Contenu `gunicorn.conf.py` :
```python
bind = "127.0.0.1:5000"
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
accesslog = "/home/gecmines/gec-mines/logs/access.log"
errorlog = "/home/gecmines/gec-mines/logs/error.log"
loglevel = "info"
```

### 4.3 Service systemd
```bash
# Retourner en root
exit

# Créer service systemd
sudo nano /etc/systemd/system/gecmines.service
```

Contenu du service :
```ini
[Unit]
Description=GEC Mines Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=gecmines
Group=gecmines
RuntimeDirectory=gecmines
WorkingDirectory=/home/gecmines/gec-mines
Environment=PATH=/home/gecmines/gec-mines/venv/bin
ExecStart=/home/gecmines/gec-mines/venv/bin/gunicorn -c gunicorn.conf.py main:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 4.4 Activation du service
```bash
# Recharger systemd
sudo systemctl daemon-reload

# Activer et démarrer le service
sudo systemctl enable gecmines
sudo systemctl start gecmines

# Vérifier le statut
sudo systemctl status gecmines
```

---

## 🌐 Étape 5 : Configuration Nginx

### 5.1 Configuration Nginx
```bash
# Créer configuration site
sudo nano /etc/nginx/sites-available/gecmines
```

Configuration Nginx :
```nginx
server {
    listen 80;
    server_name votre-domaine.com www.votre-domaine.com;
    
    # Redirection HTTPS (sera configuré plus tard)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name votre-domaine.com www.votre-domaine.com;
    
    # Logs
    access_log /var/log/nginx/gecmines_access.log;
    error_log /var/log/nginx/gecmines_error.log;
    
    # SSL Configuration (sera ajoutée par Certbot)
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Static files
    location /static/ {
        alias /home/gecmines/gec-mines/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Uploads (avec authentification)
    location /uploads/ {
        alias /home/gecmines/gec-mines/uploads/;
        expires 1d;
    }
    
    # Backups (accès restreint)
    location /backups/ {
        deny all;
    }
    
    # Application Flask
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Upload size
        client_max_body_size 32M;
    }
}
```

### 5.2 Activation configuration
```bash
# Activer le site
sudo ln -s /etc/nginx/sites-available/gecmines /etc/nginx/sites-enabled/

# Désactiver site par défaut
sudo rm /etc/nginx/sites-enabled/default

# Tester configuration
sudo nginx -t

# Redémarrer Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## 🔒 Étape 6 : Configuration SSL (Let's Encrypt)

### 6.1 Installation certificat SSL
```bash
# Obtenir certificat SSL
sudo certbot --nginx -d votre-domaine.com -d www.votre-domaine.com

# Test renouvellement automatique
sudo certbot renew --dry-run
```

### 6.2 Renouvellement automatique
```bash
# Ajouter tâche cron pour renouvellement
sudo crontab -e

# Ajouter cette ligne :
0 12 * * * /usr/bin/certbot renew --quiet
```

---

## 📊 Étape 7 : Monitoring et logs

### 7.1 Configuration logrotate
```bash
sudo nano /etc/logrotate.d/gecmines
```

Configuration logrotate :
```bash
/home/gecmines/gec-mines/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 gecmines gecmines
    postrotate
        systemctl reload gecmines
    endscript
}
```

### 7.2 Script de monitoring
```bash
# Créer script de monitoring
sudo nano /usr/local/bin/gecmines-monitor.sh
```

Script de monitoring :
```bash
#!/bin/bash

LOG_FILE="/var/log/gecmines-monitor.log"
SERVICE_NAME="gecmines"

# Vérifier si le service est actif
if ! systemctl is-active --quiet $SERVICE_NAME; then
    echo "$(date): Service $SERVICE_NAME arrêté, redémarrage..." >> $LOG_FILE
    systemctl restart $SERVICE_NAME
fi

# Vérifier l'espace disque
DISK_USAGE=$(df /home/gecmines/gec-mines | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 85 ]; then
    echo "$(date): Alerte espace disque: $DISK_USAGE%" >> $LOG_FILE
fi

# Nettoyer les anciens exports (plus de 7 jours)
find /home/gecmines/gec-mines/exports -name "*.pdf" -mtime +7 -delete

# Nettoyer les anciennes sauvegardes (plus de 30 jours)
find /home/gecmines/gec-mines/backups -name "*.zip" -mtime +30 -delete
```

### 7.3 Tâches automatisées
```bash
# Permissions script
sudo chmod +x /usr/local/bin/gecmines-monitor.sh

# Ajouter à cron (utilisateur gecmines)
sudo su - gecmines
crontab -e

# Ajouter ces lignes :
*/5 * * * * /usr/local/bin/gecmines-monitor.sh
0 1 * * 0 cd /home/gecmines/gec-mines && /home/gecmines/gec-mines/venv/bin/python -c "from views import create_system_backup; create_system_backup()"
```

---

## 🔐 Étape 8 : Sécurisation avancée

### 8.1 Configuration fail2ban
```bash
# Installation
sudo apt install fail2ban -y

# Configuration pour Nginx
sudo nano /etc/fail2ban/jail.local
```

Configuration fail2ban :
```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/gecmines_error.log

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/gecmines_error.log
maxretry = 10
```

### 8.2 Configuration utilisateur
```bash
# Désactiver connexion root SSH
sudo nano /etc/ssh/sshd_config

# Modifier ces lignes :
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes

# Redémarrer SSH
sudo systemctl restart ssh
```

### 8.3 Sauvegarde automatisée
```bash
# Script de sauvegarde
sudo nano /usr/local/bin/gecmines-backup.sh
```

Script de sauvegarde :
```bash
#!/bin/bash

BACKUP_DIR="/home/gecmines/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_BACKUP="$BACKUP_DIR/db_backup_$DATE.sql"
FILES_BACKUP="$BACKUP_DIR/files_backup_$DATE.tar.gz"

# Sauvegarde base de données
pg_dump postgresql://gec_user:mot_de_passe_securise@localhost/gec_mines > $DB_BACKUP

# Sauvegarde fichiers
tar -czf $FILES_BACKUP -C /home/gecmines/gec-mines uploads/ static/ lang/ templates/

# Nettoyage anciennes sauvegardes (plus de 30 jours)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "$(date): Sauvegarde terminée" >> /var/log/gecmines-backup.log
```

---

## ✅ Étape 9 : Tests et validation

### 9.1 Tests système
```bash
# Vérifier les services
sudo systemctl status gecmines nginx postgresql

# Vérifier les logs
sudo journalctl -u gecmines -f

# Test de charge simple
curl -I https://votre-domaine.com
```

### 9.2 Tests fonctionnels
1. **Accès web** : `https://votre-domaine.com`
2. **Connexion admin** : admin / admin123
3. **Upload fichier** test
4. **Export PDF** test
5. **Sauvegarde système** test

### 9.3 Performance
```bash
# Installation outils monitoring
sudo apt install htop iotop netstat-nat

# Monitoring ressources
htop
sudo iotop
sudo netstat -tulpn | grep 5000
```

---

## 🚨 Dépannage

### Problèmes courants

**Service ne démarre pas**
```bash
sudo journalctl -u gecmines -n 50
```

**Erreur base de données**
```bash
sudo -u postgres psql -c "\l"
sudo systemctl status postgresql
```

**Erreur Nginx**
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/gecmines_error.log
```

**Performance lente**
```bash
# Augmenter workers Gunicorn
nano /home/gecmines/gec-mines/gunicorn.conf.py
# workers = nombre_de_cpu * 2 + 1
```

---

## 📈 Optimisations

### Performance base de données
```sql
-- Connexion PostgreSQL admin
sudo -u postgres psql gec_mines

-- Index optimisés
CREATE INDEX IF NOT EXISTS idx_courrier_date ON courrier(date_enregistrement);
CREATE INDEX IF NOT EXISTS idx_courrier_user ON courrier(utilisateur_id);
CREATE INDEX IF NOT EXISTS idx_courrier_statut ON courrier(statut);
CREATE INDEX IF NOT EXISTS idx_logs_user ON logactivite(utilisateur_id);

-- Configuration PostgreSQL
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
```

### Cache Nginx
```nginx
# Ajouter à la configuration Nginx
location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header Vary Accept-Encoding;
    access_log off;
}
```

---

## ✅ Checklist finale

- [ ] Système mis à jour et sécurisé
- [ ] PostgreSQL configuré et opérationnel
- [ ] Application installée et testée
- [ ] Gunicorn configuré comme service
- [ ] Nginx configuré avec SSL
- [ ] Monitoring et logs en place
- [ ] Sauvegardes automatisées
- [ ] Tests de performance validés
- [ ] Sécurité renforcée (fail2ban, firewall)
- [ ] Documentation admin mise à jour

---

**🎉 Installation VPS terminée ! Votre système GEC Mines est en production.**

**URLs importantes :**
- Application : `https://votre-domaine.com`
- Logs système : `/var/log/gecmines-monitor.log`
- Logs application : `/home/gecmines/gec-mines/logs/`

Pour maintenance et support, consultez DOCUMENTATION.md