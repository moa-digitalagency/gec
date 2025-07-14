# Installation sur VPS - GEC Mines

## Vue d'ensemble

Ce guide détaille l'installation complète du système GEC Mines sur un serveur privé virtuel (VPS) Ubuntu/Debian avec configuration de production sécurisée.

## Prérequis

### Serveur
- **VPS Ubuntu 20.04+ ou Debian 11+**
- **RAM** : 2 GB minimum (4 GB recommandé)
- **Espace disque** : 10 GB minimum (20 GB recommandé)
- **Accès root** ou sudo
- **Connexion internet** stable

### Services requis
- Python 3.11+
- PostgreSQL 14+
- Nginx
- Supervisor (pour la gestion des processus)
- Certbot (pour SSL)

## Étape 1 : Préparation du serveur

### 1.1 Mise à jour du système
```bash
# Mise à jour des paquets
sudo apt update && sudo apt upgrade -y

# Installation des outils de base
sudo apt install -y curl wget git unzip vim htop
```

### 1.2 Configuration utilisateur
```bash
# Créer un utilisateur dédié pour l'application
sudo adduser gecmines
sudo usermod -aG sudo gecmines

# Passer à l'utilisateur gecmines
su - gecmines
```

### 1.3 Configuration SSH (sécurité)
```bash
# Générer une clé SSH si nécessaire
ssh-keygen -t rsa -b 4096 -C "admin@gec-mines.cd"

# Configuration SSH sécurisée (dans /etc/ssh/sshd_config)
sudo vim /etc/ssh/sshd_config
```

Modifiez les paramètres suivants :
```
Port 2222                    # Changer le port par défaut
PermitRootLogin no          # Interdire la connexion root
PasswordAuthentication no   # Utiliser uniquement les clés SSH
PubkeyAuthentication yes
```

Redémarrez le service SSH :
```bash
sudo systemctl restart ssh
```

## Étape 2 : Installation de Python et dépendances

### 2.1 Installation de Python 3.11
```bash
# Ajouter le dépôt deadsnakes pour Python 3.11
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# Installer Python 3.11 et outils
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
sudo apt install -y build-essential libpq-dev

# Créer un lien symbolique
sudo ln -sf /usr/bin/python3.11 /usr/bin/python3
```

### 2.2 Installation et configuration de PostgreSQL
```bash
# Installation de PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Démarrage et activation du service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Configuration de PostgreSQL
sudo -u postgres psql
```

Dans le shell PostgreSQL :
```sql
-- Créer l'utilisateur et la base de données
CREATE USER gecmines_user WITH PASSWORD 'motdepasse_securise_ici';
CREATE DATABASE gecmines_db WITH OWNER gecmines_user ENCODING 'UTF8';
GRANT ALL PRIVILEGES ON DATABASE gecmines_db TO gecmines_user;

-- Optimisation pour la production
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
\q
```

Redémarrez PostgreSQL :
```bash
sudo systemctl restart postgresql
```

## Étape 3 : Installation de l'application

### 3.1 Clonage et préparation
```bash
# Se placer dans le répertoire home
cd /home/gecmines

# Cloner le projet (ou télécharger l'archive)
git clone <repository-url> gec-mines
cd gec-mines

# Créer l'environnement virtuel Python
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### 3.2 Configuration des variables d'environnement
```bash
# Créer le fichier de configuration
vim .env
```

Contenu du fichier `.env` :
```bash
# Configuration de la base de données
DATABASE_URL=postgresql://gecmines_user:motdepasse_securise_ici@localhost:5432/gecmines_db

# Clé secrète (générer une clé forte)
SESSION_SECRET=votre_cle_secrete_tres_longue_et_complexe_generer_avec_openssl

# Configuration de production
FLASK_ENV=production
FLASK_DEBUG=False

# Configuration des chemins
UPLOAD_FOLDER=/home/gecmines/gec-mines/uploads
BACKUP_FOLDER=/home/gecmines/gec-mines/backups
```

### 3.3 Initialisation de la base de données
```bash
# Exporter les variables d'environnement
source .env

# Initialiser la base de données
python init_database.py

# Vérifier l'installation
python init_database.py --verify
```

### 3.4 Configuration des permissions
```bash
# Créer et configurer les dossiers nécessaires
mkdir -p uploads exports backups logs
chmod 755 uploads exports backups
chmod 644 static/css/* static/js/*

# Propriétaire des fichiers
sudo chown -R gecmines:gecmines /home/gecmines/gec-mines
```

## Étape 4 : Configuration de Gunicorn

### 4.1 Configuration Gunicorn
```bash
# Créer le fichier de configuration Gunicorn
vim gunicorn.conf.py
```

Contenu du fichier :
```python
# gunicorn.conf.py
bind = "127.0.0.1:5000"
workers = 3
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
user = "gecmines"
group = "gecmines"
tmp_upload_dir = None
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}
access_log = "/home/gecmines/gec-mines/logs/access.log"
error_log = "/home/gecmines/gec-mines/logs/error.log"
log_level = "info"
capture_output = True
preload_app = True
```

### 4.2 Test de Gunicorn
```bash
# Test de démarrage
source venv/bin/activate
gunicorn --config gunicorn.conf.py main:app
```

## Étape 5 : Configuration de Supervisor

### 5.1 Installation et configuration de Supervisor
```bash
# Installation
sudo apt install -y supervisor

# Créer le fichier de configuration
sudo vim /etc/supervisor/conf.d/gecmines.conf
```

Contenu du fichier de configuration :
```ini
[program:gecmines]
command=/home/gecmines/gec-mines/venv/bin/gunicorn --config gunicorn.conf.py main:app
directory=/home/gecmines/gec-mines
user=gecmines
group=gecmines
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/home/gecmines/gec-mines/logs/supervisor.err.log
stdout_logfile=/home/gecmines/gec-mines/logs/supervisor.out.log
environment=DATABASE_URL="postgresql://gecmines_user:motdepasse_securise_ici@localhost:5432/gecmines_db",SESSION_SECRET="votre_cle_secrete"
```

### 5.2 Démarrage de Supervisor
```bash
# Recharger la configuration
sudo supervisorctl reread
sudo supervisorctl update

# Démarrer l'application
sudo supervisorctl start gecmines

# Vérifier le statut
sudo supervisorctl status gecmines
```

## Étape 6 : Configuration de Nginx

### 6.1 Installation de Nginx
```bash
# Installation
sudo apt install -y nginx

# Créer la configuration du site
sudo vim /etc/nginx/sites-available/gecmines
```

### 6.2 Configuration Nginx
```nginx
server {
    listen 80;
    server_name votre-domaine.com www.votre-domaine.com;
    
    # Redirection HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name votre-domaine.com www.votre-domaine.com;
    
    # Certificats SSL (à configurer avec Certbot)
    ssl_certificate /etc/letsencrypt/live/votre-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.com/privkey.pem;
    
    # Configuration SSL sécurisée
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Headers de sécurité
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
    
    # Configuration des logs
    access_log /var/log/nginx/gecmines_access.log;
    error_log /var/log/nginx/gecmines_error.log;
    
    # Taille maximale des uploads
    client_max_body_size 16M;
    
    # Fichiers statiques
    location /static {
        alias /home/gecmines/gec-mines/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Fichiers téléchargés (protégés)
    location /uploads {
        internal;
        alias /home/gecmines/gec-mines/uploads;
    }
    
    # Application principale
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Protection des fichiers sensibles
    location ~ /\. {
        deny all;
    }
    
    location ~ \.py$ {
        deny all;
    }
}
```

### 6.3 Activation du site
```bash
# Activer le site
sudo ln -s /etc/nginx/sites-available/gecmines /etc/nginx/sites-enabled/

# Tester la configuration
sudo nginx -t

# Redémarrer Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## Étape 7 : Configuration SSL avec Certbot

### 7.1 Installation de Certbot
```bash
# Installation
sudo apt install -y certbot python3-certbot-nginx

# Obtenir le certificat SSL
sudo certbot --nginx -d votre-domaine.com -d www.votre-domaine.com
```

### 7.2 Renouvellement automatique
```bash
# Tester le renouvellement
sudo certbot renew --dry-run

# Le renouvellement automatique est configuré via cron
# Vérifier : sudo crontab -l
```

## Étape 8 : Configuration du pare-feu

### 8.1 Configuration UFW
```bash
# Activer UFW
sudo ufw enable

# Règles de base
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Autoriser SSH (port personnalisé)
sudo ufw allow 2222/tcp

# Autoriser HTTP et HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Autoriser PostgreSQL localement seulement
sudo ufw allow from 127.0.0.1 to any port 5432

# Vérifier les règles
sudo ufw status verbose
```

## Étape 9 : Monitoring et maintenance

### 9.1 Configuration des logs
```bash
# Logrotate pour les logs de l'application
sudo vim /etc/logrotate.d/gecmines
```

Contenu :
```
/home/gecmines/gec-mines/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 0644 gecmines gecmines
    postrotate
        sudo supervisorctl restart gecmines
    endscript
}
```

### 9.2 Scripts de maintenance
```bash
# Créer un script de sauvegarde automatique
vim /home/gecmines/backup.sh
```

Contenu du script :
```bash
#!/bin/bash
cd /home/gecmines/gec-mines
source venv/bin/activate
source .env

# Sauvegarde de la base de données
pg_dump $DATABASE_URL > "backups/db_backup_$(date +%Y%m%d_%H%M%S).sql"

# Nettoyer les anciennes sauvegardes (garder 30 jours)
find backups/ -name "db_backup_*.sql" -mtime +30 -delete

# Sauvegarde complète via l'application (hebdomadaire)
if [ $(date +%u) -eq 7 ]; then
    python -c "from views import create_system_backup; create_system_backup()"
fi
```

Rendre exécutable et programmer :
```bash
chmod +x /home/gecmines/backup.sh

# Ajouter au crontab
crontab -e
```

Ajouter :
```
# Sauvegarde quotidienne à 2h du matin
0 2 * * * /home/gecmines/backup.sh

# Redémarrage hebdomadaire à 3h du matin le dimanche
0 3 * * 0 sudo supervisorctl restart gecmines
```

## Étape 10 : Test et vérification

### 10.1 Tests de fonctionnement
```bash
# Vérifier les services
sudo systemctl status postgresql
sudo systemctl status nginx
sudo supervisorctl status gecmines

# Tester l'accès web
curl -I https://votre-domaine.com

# Vérifier les logs
tail -f /home/gecmines/gec-mines/logs/error.log
```

### 10.2 Tests de l'application
1. Accéder à `https://votre-domaine.com`
2. Se connecter avec `admin` / `admin123`
3. Tester l'enregistrement d'un courrier
4. Tester l'upload de fichier
5. Tester l'export PDF
6. Vérifier la fonction de sauvegarde

## Sécurité post-installation

### Hardening du serveur
1. **Mettre à jour régulièrement** : `sudo apt update && sudo apt upgrade`
2. **Configurer fail2ban** pour la protection SSH
3. **Installer des outils de monitoring** (htop, netstat, ss)
4. **Configurer les alertes** pour l'espace disque et la charge
5. **Auditer régulièrement** les logs de sécurité

### Surveillance
- Configurer des alertes de monitoring
- Vérifier les logs d'accès Nginx
- Surveiller l'utilisation des ressources
- Auditer les connexions SSH

---

**Important** : Changez TOUS les mots de passe par défaut et configurez une stratégie de sauvegarde robuste avant la mise en production.

**Support** : Consultez la documentation complète dans `docs/` pour le dépannage et la maintenance avancée.