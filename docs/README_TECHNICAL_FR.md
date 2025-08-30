# GEC - Documentation Technique

## Architecture Système

### Stack Technologique
- **Backend**: Flask 3.1.1 (Python 3.11+)
- **Base de données**: PostgreSQL 14+ / SQLite 3
- **ORM**: SQLAlchemy 2.0.41 avec Flask-SQLAlchemy 3.1.1
- **Serveur WSGI**: Gunicorn 23.0.0
- **Authentification**: Flask-Login 0.6.3
- **Chiffrement**: AES-256-CBC (cryptography 45.0.6)
- **Hachage**: bcrypt 4.3.0 avec salage personnalisé
- **PDF**: ReportLab 4.4.2
- **Images**: Pillow 11.3.0
- **Email**: SendGrid 6.12.4 avec templates multi-langues

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

## Configuration Déploiement et Domaines

### Configuration Domaine Personnalisé

#### Déploiement Replit avec Domaine Personnalisé

Pour remplacer l'adresse IP locale par un domaine personnalisé sur Replit :

1. **Déploiement Initial**
   ```bash
   # L'application se lance sur 0.0.0.0:5000
   gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
   ```

2. **Configuration Domaine via Replit**
   - Onglet `Deployments` → `Settings`
   - "Link a domain" ou "Manually connect from another registrar"
   - Entrer le domaine (ex: `gec.votreentreprise.com`)

3. **Configuration DNS**
   ```dns
   # Enregistrements à ajouter chez votre registraire :
   Type: A     | Nom: @     | Valeur: [IP fournie par Replit]
   Type: A     | Nom: www   | Valeur: [IP fournie par Replit]
   Type: TXT   | Nom: @     | Valeur: [Token fourni par Replit]
   ```

4. **Vérification SSL/TLS**
   ```bash
   # Replit fournit automatiquement :
   ✅ Certificat SSL/TLS Let's Encrypt
   ✅ Redirection HTTP → HTTPS
   ✅ Protection WHOIS
   ```

#### Déploiement Serveur Local avec Domaine

Pour un déploiement sur serveur privé avec domaine personnalisé :

1. **Configuration Nginx**
   ```nginx
   # /etc/nginx/sites-available/gec
   server {
       listen 80;
       server_name gec.votredomaine.com www.gec.votredomaine.com;
       
       # Redirection HTTPS
       return 301 https://$server_name$request_uri;
   }
   
   server {
       listen 443 ssl;
       server_name gec.votredomaine.com www.gec.votredomaine.com;
       
       ssl_certificate /path/to/ssl/certificate.crt;
       ssl_certificate_key /path/to/ssl/private.key;
       
       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

2. **Configuration Systemd Service**
   ```ini
   # /etc/systemd/system/gec.service
   [Unit]
   Description=GEC Courrier Application
   After=network.target
   
   [Service]
   Type=exec
   User=gec
   WorkingDirectory=/opt/gec
   Environment=PATH=/opt/gec/.venv/bin
   ExecStart=/opt/gec/.venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 main:app
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

3. **Configuration Variables d'Environnement**
   ```bash
   # /opt/gec/.env
   DATABASE_URL=postgresql://gec_user:password@localhost/gec_prod
   SESSION_SECRET=production-secret-key-very-long
   GEC_MASTER_KEY=production-encryption-key-32-chars
   GEC_PASSWORD_SALT=production-salt
   FLASK_ENV=production
   ```

#### Configuration DNS pour Production

```dns
# Configuration DNS complète
Type: A      | Nom: @              | Valeur: [IP serveur]     | TTL: 3600
Type: A      | Nom: www            | Valeur: [IP serveur]     | TTL: 3600
Type: CNAME  | Nom: gec            | Valeur: votredomaine.com | TTL: 3600
Type: MX     | Nom: @              | Valeur: mail.domain.com  | TTL: 3600
Type: TXT    | Nom: @              | Valeur: "v=spf1 include:_spf.domain.com ~all"
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
apt-get install -y python3.11 python3.11-venv python3.11-dev git postgresql-client

# CentOS/RHEL/Fedora
dnf install -y python3.11 python3.11-devel git postgresql

# macOS
brew install python@3.11 git

# Windows
winget install --id Python.Python.3.11 -e
winget install --id Git.Git -e
```

### Installation Multi-Plateforme

#### 🚀 Installation Automatique One-Click

**Scripts d'installation disponibles :**
- **Windows** : `install-windows.ps1` ou `install-windows.bat`
- **macOS** : `install-macos.sh`
- **Linux** : `install-linux.sh`

```bash
# Exemple pour Linux/macOS
chmod +x install-linux.sh
./install-linux.sh

# Exemple pour Windows (PowerShell)
.\install-windows.ps1
```

#### 🔧 Installation Manuelle

**1. Clonage et Configuration**
```bash
# Cloner le projet
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# Créer l'environnement virtuel
python3.11 -m venv .venv  # Linux/macOS
python -m venv .venv      # Windows

# Activer l'environnement
source .venv/bin/activate    # Linux/macOS
.venv\Scripts\Activate.ps1   # Windows PowerShell
.venv\Scripts\activate.bat   # Windows CMD

# Installer les dépendances
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt
```

#### 2. Variables d'Environnement
```bash
# Créer .env
cat > .env << EOF
DATABASE_URL=postgresql://user:password@localhost:5432/geccourrier
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
        email='admin@geccourrier.cd',
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
    server_name geccourrier.example.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /uploads {
        alias /var/www/geccourrier/uploads;
        expires 30d;
    }
    
    client_max_body_size 16M;
}
```

#### Service Systemd
```ini
# /etc/systemd/system/geccourrier.service
[Unit]
Description=GEC Courrier Application
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/geccourrier
Environment="PATH=/var/www/geccourrier/venv/bin"
ExecStart=/var/www/geccourrier/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    --log-file /var/log/geccourrier/gunicorn.log \
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
certbot --nginx -d geccourrier.example.com

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

project_home = '/home/username/geccourrier'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ['DATABASE_URL'] = 'mysql://username:password@username.mysql.pythonanywhere-services.com/username$geccourrier'
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
cat > /etc/logrotate.d/geccourrier << EOF
/var/log/geccourrier/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload geccourrier
    endscript
}
EOF
```

#### Sauvegarde Automatique
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/geccourrier"

# Sauvegarde DB
pg_dump $DATABASE_URL > $BACKUP_DIR/db_$DATE.sql

# Sauvegarde fichiers
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /var/www/geccourrier/uploads

# Nettoyer anciennes sauvegardes (>30 jours)
find $BACKUP_DIR -type f -mtime +30 -delete

# Cron
0 2 * * * /opt/geccourrier/backup.sh
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

email=admin@geccourrier.cd&password=Admin@2025
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
chmod 755 /var/www/geccourrier/uploads
chown -R www-data:www-data /var/www/geccourrier/uploads

# Espace disque
df -h /var/www/geccourrier/uploads
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
ab -n 1000 -c 10 https://geccourrier.example.com/

# Locust
locust -f loadtest.py --host=https://geccourrier.example.com
```

## Support Technique

### Contacts MOA Digital Agency
- **Email**: moa@myoneart.com
- **Email alternatif**: moa.myoneart@gmail.com
- **Téléphone**: +212 699 14 000 1
- **Téléphone RDC**: +243 86 049 33 45
- **Site web**: [myoneart.com](https://myoneart.com)

### Développeur Principal
**AIsance KALONJI wa KALONJI**
- Architecte logiciel senior
- Spécialiste sécurité et chiffrement
- Expert solutions gouvernementales

### Versions
- **Version actuelle**: 1.0.0 (Août 2025)
- **Python minimum**: 3.8
- **PostgreSQL minimum**: 12
- **Navigateurs supportés**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

---
**© 2025 MOA Digital Agency LLC** | Documentation Technique

**Conception et Développement**: AIsance KALONJI wa KALONJI

*Développé avec 💖 et ☕ par MOA Digital Agency LLC*