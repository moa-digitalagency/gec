# GEC Mines - Documentation Technique

## Architecture Système

### Stack Technologique
- **Backend**: Flask 2.3.3 (Python 3.8+)
- **Base de données**: PostgreSQL 14+ / SQLite 3
- **ORM**: SQLAlchemy 2.0.20 avec Flask-SQLAlchemy 3.0.5
- **Serveur WSGI**: Gunicorn 23.0.0
- **Authentification**: Flask-Login 0.6.2
- **Chiffrement**: AES-256-CBC (cryptography 41.0.3)
- **Hachage**: bcrypt 4.0.1 avec salage personnalisé
- **PDF**: ReportLab 4.0.4
- **Images**: Pillow 10.0.0

### Architecture de Sécurité

#### Chiffrement des Données
```python
- Algorithme: AES-256-CBC
- Clé maître: Variable GEC_MASTER_KEY (256 bits)
- Sel: Variable GEC_PASSWORD_SALT
- IV: Généré aléatoirement pour chaque chiffrement
```

#### Protection contre les Attaques
- **SQL Injection**: Requêtes paramétrées via SQLAlchemy
- **XSS**: Échappement automatique Jinja2 + sanitisation
- **CSRF**: Tokens de session sécurisés
- **Brute Force**: Limitation de taux + blocage IP
- **Path Traversal**: Validation des chemins de fichiers

### Structure de la Base de Données

#### Tables Principales
```sql
-- Table Courrier
CREATE TABLE courrier (
    id INTEGER PRIMARY KEY,
    numero_accuse_reception VARCHAR(50) UNIQUE NOT NULL,
    numero_reference VARCHAR(50),
    objet TEXT NOT NULL,
    type_courrier VARCHAR(20) NOT NULL,
    expediteur VARCHAR(200),
    destinataire VARCHAR(200),
    date_redaction DATE,
    date_enregistrement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    statut VARCHAR(50),
    fichier_nom VARCHAR(255),
    fichier_chemin VARCHAR(500),
    utilisateur_id INTEGER REFERENCES user(id),
    secretaire_general_copie BOOLEAN,
    type_courrier_sortant_id INTEGER,
    autres_informations TEXT,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_search (numero_accuse_reception, objet, expediteur, destinataire)
);

-- Table User
CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256),
    nom_complet VARCHAR(200),
    role VARCHAR(50),
    departement_id INTEGER,
    actif BOOLEAN DEFAULT TRUE,
    INDEX idx_email (email)
);
```

### Optimisations Performance

#### Indexation
- Index composé sur les champs de recherche
- Index sur les clés étrangères
- Index sur les champs de tri fréquents

#### Cache
```python
# Cache des requêtes fréquentes
@cache.memoize(timeout=300)
def get_statuts_actifs():
    return StatutCourrier.query.filter_by(actif=True).all()
```

#### Pagination
- Limite par défaut: 25 éléments par page
- Chargement paresseux des relations

## Installation et Déploiement

### Prérequis Système
```bash
# Ubuntu/Debian
apt-get update
apt-get install -y python3.8 python3-pip postgresql-14 nginx

# CentOS/RHEL
yum install -y python38 python38-pip postgresql14-server nginx
```

### Installation Locale

#### 1. Clonage et Configuration
```bash
git clone [REPOSITORY_URL]
cd gec-mines

# Environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Dépendances
pip install -r requirements.txt
```

#### 2. Variables d'Environnement
```bash
# Créer .env
cat > .env << EOF
DATABASE_URL=postgresql://user:password@localhost:5432/gecmines
SESSION_SECRET=$(openssl rand -hex 32)
GEC_MASTER_KEY=$(openssl rand -base64 32)
GEC_PASSWORD_SALT=$(openssl rand -base64 32)
FLASK_ENV=production
EOF
```

#### 3. Initialisation Base de Données
```python
# init_db.py
from app import app, db
with app.app_context():
    db.create_all()
    # Créer admin par défaut
    from models import User
    admin = User(
        username='admin',
        email='admin@gecmines.cd',
        role='super_admin'
    )
    admin.set_password('Admin@2025')
    db.session.add(admin)
    db.session.commit()
```

### Déploiement Production

#### Configuration Nginx
```nginx
server {
    listen 80;
    server_name gecmines.example.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /uploads {
        alias /var/www/gecmines/uploads;
        expires 30d;
    }
    
    client_max_body_size 16M;
}
```

#### Service Systemd
```ini
# /etc/systemd/system/gecmines.service
[Unit]
Description=GEC Mines Application
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/gecmines
Environment="PATH=/var/www/gecmines/venv/bin"
ExecStart=/var/www/gecmines/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    --log-file /var/log/gecmines/gunicorn.log \
    main:app
Restart=always

[Install]
WantedBy=multi-user.target
```

#### SSL/TLS avec Let's Encrypt
```bash
# Installation Certbot
apt-get install certbot python3-certbot-nginx

# Génération certificat
certbot --nginx -d gecmines.example.com

# Renouvellement automatique
crontab -e
0 0 * * * /usr/bin/certbot renew --quiet
```

### Déploiement Cloud

#### PythonAnywhere
```python
# /var/www/username_pythonanywhere_com_wsgi.py
import sys
import os

project_home = '/home/username/gecmines'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ['DATABASE_URL'] = 'mysql://username:password@username.mysql.pythonanywhere-services.com/username$gecmines'
os.environ['SESSION_SECRET'] = 'your-secret-key'
os.environ['GEC_MASTER_KEY'] = 'your-master-key'
os.environ['GEC_PASSWORD_SALT'] = 'your-salt'

from main import app as application
```

#### Heroku
```yaml
# Procfile
web: gunicorn main:app

# runtime.txt
python-3.8.16

# Configuration
heroku config:set DATABASE_URL=postgres://...
heroku config:set SESSION_SECRET=...
heroku config:set GEC_MASTER_KEY=...
```

#### Docker
```dockerfile
FROM python:3.8-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=main.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "main:app"]
```

### Monitoring et Maintenance

#### Logs
```bash
# Rotation des logs
cat > /etc/logrotate.d/gecmines << EOF
/var/log/gecmines/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload gecmines
    endscript
}
EOF
```

#### Sauvegarde Automatique
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/gecmines"

# Sauvegarde DB
pg_dump $DATABASE_URL > $BACKUP_DIR/db_$DATE.sql

# Sauvegarde fichiers
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /var/www/gecmines/uploads

# Nettoyer anciennes sauvegardes (>30 jours)
find $BACKUP_DIR -type f -mtime +30 -delete

# Cron
0 2 * * * /opt/gecmines/backup.sh
```

#### Monitoring Santé
```python
# health_check.py
@app.route('/health')
def health_check():
    try:
        # Vérifier DB
        db.session.execute('SELECT 1')
        
        # Vérifier espace disque
        import shutil
        disk = shutil.disk_usage('/')
        if disk.percent > 90:
            return jsonify({'status': 'warning', 'disk': disk.percent}), 200
            
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
```

## API Endpoints

### Authentification
```http
POST /login
Content-Type: application/x-www-form-urlencoded

email=admin@gecmines.cd&password=Admin@2025
```

### Courriers
```http
# Liste avec filtres
GET /view_mail?search=urgent&type_courrier=ENTRANT&sg_copie=oui

# Détail
GET /mail/{id}

# Export PDF
GET /export_pdf/{id}

# Téléchargement fichier
GET /download_file/{id}
```

### Administration
```http
# Paramètres système
GET/POST /settings

# Gestion utilisateurs
GET/POST /admin/users

# Logs activité
GET /admin/logs
```

## Troubleshooting

### Erreurs Fréquentes

#### Database Connection Error
```bash
# Vérifier PostgreSQL
systemctl status postgresql
psql -U postgres -c "SELECT 1"

# Vérifier DATABASE_URL
python -c "import os; print(os.environ.get('DATABASE_URL'))"
```

#### File Upload Failed
```bash
# Permissions
chmod 755 /var/www/gecmines/uploads
chown -R www-data:www-data /var/www/gecmines/uploads

# Espace disque
df -h /var/www/gecmines/uploads
```

#### Session Expired
```python
# Augmenter durée session
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
```

## Tests

### Tests Unitaires
```python
# test_models.py
import unittest
from app import app, db
from models import User, Courrier

class TestModels(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()
    
    def test_user_password(self):
        user = User(username='test', email='test@test.com')
        user.set_password('Test123!')
        self.assertTrue(user.check_password('Test123!'))
        self.assertFalse(user.check_password('wrong'))
```

### Tests de Charge
```bash
# Apache Bench
ab -n 1000 -c 10 https://gecmines.example.com/

# Locust
locust -f loadtest.py --host=https://gecmines.example.com
```

## Support Technique

### Contacts
- Email: support@gecmines.cd
- Documentation: https://docs.gecmines.cd
- Issues: https://github.com/gecmines/issues

### Versions
- **Version actuelle**: 1.0.0 (Août 2025)
- **Python minimum**: 3.8
- **PostgreSQL minimum**: 12
- **Navigateurs supportés**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

---
© 2025 GEC Mines - Secrétariat Général des Mines | Documentation Technique