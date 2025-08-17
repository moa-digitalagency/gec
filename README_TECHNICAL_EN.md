# GEC Mines - Technical Documentation

## System Architecture

### Technology Stack
- **Backend**: Flask 2.3.3 (Python 3.8+)
- **Database**: PostgreSQL 14+ / SQLite 3
- **ORM**: SQLAlchemy 2.0.20 with Flask-SQLAlchemy 3.0.5
- **WSGI Server**: Gunicorn 23.0.0
- **Authentication**: Flask-Login 0.6.2
- **Encryption**: AES-256-CBC (cryptography 41.0.3)
- **Hashing**: bcrypt 4.0.1 with custom salt
- **PDF**: ReportLab 4.0.4
- **Images**: Pillow 10.0.0

### Security Architecture

#### Data Encryption
```python
- Algorithm: AES-256-CBC
- Master Key: GEC_MASTER_KEY variable (256 bits)
- Salt: GEC_PASSWORD_SALT variable
- IV: Randomly generated for each encryption
```

#### Attack Protection
- **SQL Injection**: Parameterized queries via SQLAlchemy
- **XSS**: Automatic Jinja2 escaping + sanitization
- **CSRF**: Secure session tokens
- **Brute Force**: Rate limiting + IP blocking
- **Path Traversal**: File path validation

### Database Structure

#### Main Tables
```sql
-- Courrier Table
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

-- User Table
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

### Performance Optimizations

#### Indexing
- Composite index on search fields
- Indexes on foreign keys
- Indexes on frequently sorted fields

#### Caching
```python
# Cache frequent queries
@cache.memoize(timeout=300)
def get_active_statuses():
    return StatutCourrier.query.filter_by(actif=True).all()
```

#### Pagination
- Default limit: 25 items per page
- Lazy loading of relationships

## Installation and Deployment

### System Requirements
```bash
# Ubuntu/Debian
apt-get update
apt-get install -y python3.8 python3-pip postgresql-14 nginx

# CentOS/RHEL
yum install -y python38 python38-pip postgresql14-server nginx
```

### Local Installation

#### 1. Clone and Configure
```bash
git clone [REPOSITORY_URL]
cd gec-mines

# Virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Dependencies
pip install -r requirements.txt
```

#### 2. Environment Variables
```bash
# Create .env
cat > .env << EOF
DATABASE_URL=postgresql://user:password@localhost:5432/gecmines
SESSION_SECRET=$(openssl rand -hex 32)
GEC_MASTER_KEY=$(openssl rand -base64 32)
GEC_PASSWORD_SALT=$(openssl rand -base64 32)
FLASK_ENV=production
EOF
```

#### 3. Database Initialization
```python
# init_db.py
from app import app, db
with app.app_context():
    db.create_all()
    # Create default admin
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

### Production Deployment

#### Nginx Configuration
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

#### Systemd Service
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

#### SSL/TLS with Let's Encrypt
```bash
# Install Certbot
apt-get install certbot python3-certbot-nginx

# Generate certificate
certbot --nginx -d gecmines.example.com

# Automatic renewal
crontab -e
0 0 * * * /usr/bin/certbot renew --quiet
```

### Cloud Deployment

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

### Monitoring and Maintenance

#### Logs
```bash
# Log rotation
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

#### Automatic Backup
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/gecmines"

# Database backup
pg_dump $DATABASE_URL > $BACKUP_DIR/db_$DATE.sql

# Files backup
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /var/www/gecmines/uploads

# Clean old backups (>30 days)
find $BACKUP_DIR -type f -mtime +30 -delete

# Cron
0 2 * * * /opt/gecmines/backup.sh
```

#### Health Monitoring
```python
# health_check.py
@app.route('/health')
def health_check():
    try:
        # Check DB
        db.session.execute('SELECT 1')
        
        # Check disk space
        import shutil
        disk = shutil.disk_usage('/')
        if disk.percent > 90:
            return jsonify({'status': 'warning', 'disk': disk.percent}), 200
            
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
```

## API Endpoints

### Authentication
```http
POST /login
Content-Type: application/x-www-form-urlencoded

email=admin@gecmines.cd&password=Admin@2025
```

### Mail Management
```http
# List with filters
GET /view_mail?search=urgent&type_courrier=ENTRANT&sg_copie=oui

# Detail
GET /mail/{id}

# PDF Export
GET /export_pdf/{id}

# File Download
GET /download_file/{id}
```

### Administration
```http
# System settings
GET/POST /settings

# User management
GET/POST /admin/users

# Activity logs
GET /admin/logs
```

## Troubleshooting

### Common Errors

#### Database Connection Error
```bash
# Check PostgreSQL
systemctl status postgresql
psql -U postgres -c "SELECT 1"

# Check DATABASE_URL
python -c "import os; print(os.environ.get('DATABASE_URL'))"
```

#### File Upload Failed
```bash
# Permissions
chmod 755 /var/www/gecmines/uploads
chown -R www-data:www-data /var/www/gecmines/uploads

# Disk space
df -h /var/www/gecmines/uploads
```

#### Session Expired
```python
# Increase session duration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
```

## Testing

### Unit Tests
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

### Load Testing
```bash
# Apache Bench
ab -n 1000 -c 10 https://gecmines.example.com/

# Locust
locust -f loadtest.py --host=https://gecmines.example.com
```

## Technical Support

### Contacts
- Email: support@gecmines.cd
- Documentation: https://docs.gecmines.cd
- Issues: https://github.com/gecmines/issues

### Versions
- **Current version**: 1.0.0 (August 2025)
- **Minimum Python**: 3.8
- **Minimum PostgreSQL**: 12
- **Supported browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

---
© 2025 GEC Mines - General Secretariat of Mines | Technical Documentation