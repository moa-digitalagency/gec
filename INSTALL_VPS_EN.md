# VPS Installation Guide - GEC Mines
## Complete Installation on Virtual Private Server

---

## 📋 System Requirements

### VPS Server
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **RAM**: Minimum 2GB (recommended 4GB)
- **Storage**: Minimum 20GB SSD
- **CPU**: 2 vCores minimum
- **Root access** or sudo privileges

### Required Software
- Python 3.8+
- PostgreSQL 13+ (or MySQL 8.0+)
- Nginx
- Certbot (for SSL)
- Git

---

## 🔧 Step 1: Server Preparation

### 1.1 System Update
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
# or for CentOS 8+
sudo dnf update -y
```

### 1.2 Dependencies Installation
```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip python3-venv git nginx postgresql postgresql-contrib certbot python3-certbot-nginx ufw htop curl wget unzip

# CentOS/RHEL
sudo dnf install -y python3 python3-pip git nginx postgresql postgresql-server postgresql-contrib certbot python3-certbot-nginx firewalld htop curl wget unzip
```

### 1.3 Firewall Configuration
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

## 🗃️ Step 2: PostgreSQL Configuration

### 2.1 PostgreSQL Initialization
```bash
# Ubuntu/Debian (auto-initialized)
sudo systemctl enable postgresql
sudo systemctl start postgresql

# CentOS/RHEL
sudo postgresql-setup --initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### 2.2 Database Configuration
```bash
# Access PostgreSQL
sudo -u postgres psql

-- In PostgreSQL
CREATE DATABASE gec_mines;
CREATE USER gec_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE gec_mines TO gec_user;
ALTER USER gec_user CREATEDB;
\q
```

### 2.3 Authentication Configuration
```bash
# Edit pg_hba.conf
sudo nano /etc/postgresql/13/main/pg_hba.conf

# Add this line after local rules:
local   gec_mines   gec_user   md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

---

## 📥 Step 3: Application Installation

### 3.1 System User Creation
```bash
# Create dedicated user
sudo adduser gecmines
sudo usermod -aG sudo gecmines

# Switch to gecmines user
sudo su - gecmines
```

### 3.2 Clone and Configuration
```bash
# Clone project
git clone https://github.com/your-repo/gec-mines.git
cd gec-mines

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3 Environment Configuration
```bash
# Create .env file
nano .env
```

`.env` file content:
```bash
# Database
DATABASE_URL=postgresql://gec_user:secure_password@localhost/gec_mines

# Security
SESSION_SECRET=your_very_long_random_unique_secret

# Flask
FLASK_ENV=production
FLASK_DEBUG=False

# Paths
UPLOAD_FOLDER=/home/gecmines/gec-mines/uploads
EXPORT_FOLDER=/home/gecmines/gec-mines/exports

# Performance
SQLALCHEMY_ENGINE_OPTIONS='{"pool_size": 20, "pool_recycle": 3600}'
```

### 3.4 Database Initialization
```bash
# Activate virtual environment if not already done
source venv/bin/activate

# Initialize tables
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('✅ Database initialized')
"

# Create necessary folders
mkdir -p uploads exports backups logs
chmod 755 uploads exports backups logs
```

---

## 🚀 Step 4: Gunicorn Configuration

### 4.1 Gunicorn Installation
```bash
# In virtual environment
pip install gunicorn
```

### 4.2 Gunicorn Configuration
```bash
# Create configuration file
nano gunicorn.conf.py
```

`gunicorn.conf.py` content:
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

### 4.3 Systemd Service
```bash
# Return to root
exit

# Create systemd service
sudo nano /etc/systemd/system/gecmines.service
```

Service content:
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

### 4.4 Service Activation
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable gecmines
sudo systemctl start gecmines

# Check status
sudo systemctl status gecmines
```

---

## 🌐 Step 5: Nginx Configuration

### 5.1 Nginx Configuration
```bash
# Create site configuration
sudo nano /etc/nginx/sites-available/gecmines
```

Nginx configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # HTTPS redirect (will be configured later)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # Logs
    access_log /var/log/nginx/gecmines_access.log;
    error_log /var/log/nginx/gecmines_error.log;
    
    # SSL Configuration (will be added by Certbot)
    
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
    
    # Uploads (with authentication)
    location /uploads/ {
        alias /home/gecmines/gec-mines/uploads/;
        expires 1d;
    }
    
    # Backups (restricted access)
    location /backups/ {
        deny all;
    }
    
    # Flask application
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

### 5.2 Configuration Activation
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/gecmines /etc/nginx/sites-enabled/

# Disable default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## 🔒 Step 6: SSL Configuration (Let's Encrypt)

### 6.1 SSL Certificate Installation
```bash
# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Test automatic renewal
sudo certbot renew --dry-run
```

### 6.2 Automatic Renewal
```bash
# Add cron job for renewal
sudo crontab -e

# Add this line:
0 12 * * * /usr/bin/certbot renew --quiet
```

---

## 📊 Step 7: Monitoring and Logs

### 7.1 Logrotate Configuration
```bash
sudo nano /etc/logrotate.d/gecmines
```

Logrotate configuration:
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

### 7.2 Monitoring Script
```bash
# Create monitoring script
sudo nano /usr/local/bin/gecmines-monitor.sh
```

Monitoring script:
```bash
#!/bin/bash

LOG_FILE="/var/log/gecmines-monitor.log"
SERVICE_NAME="gecmines"

# Check if service is active
if ! systemctl is-active --quiet $SERVICE_NAME; then
    echo "$(date): Service $SERVICE_NAME stopped, restarting..." >> $LOG_FILE
    systemctl restart $SERVICE_NAME
fi

# Check disk usage
DISK_USAGE=$(df /home/gecmines/gec-mines | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 85 ]; then
    echo "$(date): Disk space alert: $DISK_USAGE%" >> $LOG_FILE
fi

# Clean old exports (older than 7 days)
find /home/gecmines/gec-mines/exports -name "*.pdf" -mtime +7 -delete

# Clean old backups (older than 30 days)
find /home/gecmines/gec-mines/backups -name "*.zip" -mtime +30 -delete
```

### 7.3 Automated Tasks
```bash
# Script permissions
sudo chmod +x /usr/local/bin/gecmines-monitor.sh

# Add to cron (gecmines user)
sudo su - gecmines
crontab -e

# Add these lines:
*/5 * * * * /usr/local/bin/gecmines-monitor.sh
0 1 * * 0 cd /home/gecmines/gec-mines && /home/gecmines/gec-mines/venv/bin/python -c "from views import create_system_backup; create_system_backup()"
```

---

## 🔐 Step 8: Advanced Security

### 8.1 Fail2ban Configuration
```bash
# Installation
sudo apt install fail2ban -y

# Nginx configuration
sudo nano /etc/fail2ban/jail.local
```

Fail2ban configuration:
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

### 8.2 User Configuration
```bash
# Disable root SSH login
sudo nano /etc/ssh/sshd_config

# Modify these lines:
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes

# Restart SSH
sudo systemctl restart ssh
```

### 8.3 Automated Backup
```bash
# Backup script
sudo nano /usr/local/bin/gecmines-backup.sh
```

Backup script:
```bash
#!/bin/bash

BACKUP_DIR="/home/gecmines/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_BACKUP="$BACKUP_DIR/db_backup_$DATE.sql"
FILES_BACKUP="$BACKUP_DIR/files_backup_$DATE.tar.gz"

# Database backup
pg_dump postgresql://gec_user:secure_password@localhost/gec_mines > $DB_BACKUP

# Files backup
tar -czf $FILES_BACKUP -C /home/gecmines/gec-mines uploads/ static/ lang/ templates/

# Clean old backups (older than 30 days)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "$(date): Backup completed" >> /var/log/gecmines-backup.log
```

---

## ✅ Step 9: Testing and Validation

### 9.1 System Tests
```bash
# Check services
sudo systemctl status gecmines nginx postgresql

# Check logs
sudo journalctl -u gecmines -f

# Simple load test
curl -I https://your-domain.com
```

### 9.2 Functional Tests
1. **Web access**: `https://your-domain.com`
2. **Admin login**: admin / admin123
3. **File upload** test
4. **PDF export** test
5. **System backup** test

### 9.3 Performance
```bash
# Install monitoring tools
sudo apt install htop iotop netstat-nat

# Resource monitoring
htop
sudo iotop
sudo netstat -tulpn | grep 5000
```

---

## 🚨 Troubleshooting

### Common Issues

**Service won't start**
```bash
sudo journalctl -u gecmines -n 50
```

**Database error**
```bash
sudo -u postgres psql -c "\l"
sudo systemctl status postgresql
```

**Nginx error**
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/gecmines_error.log
```

**Slow performance**
```bash
# Increase Gunicorn workers
nano /home/gecmines/gec-mines/gunicorn.conf.py
# workers = number_of_cpu * 2 + 1
```

---

## 📈 Optimizations

### Database Performance
```sql
-- Connect as PostgreSQL admin
sudo -u postgres psql gec_mines

-- Optimized indexes
CREATE INDEX IF NOT EXISTS idx_courrier_date ON courrier(date_enregistrement);
CREATE INDEX IF NOT EXISTS idx_courrier_user ON courrier(utilisateur_id);
CREATE INDEX IF NOT EXISTS idx_courrier_statut ON courrier(statut);
CREATE INDEX IF NOT EXISTS idx_logs_user ON logactivite(utilisateur_id);

-- PostgreSQL configuration
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
```

### Nginx Cache
```nginx
# Add to Nginx configuration
location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header Vary Accept-Encoding;
    access_log off;
}
```

---

## ✅ Final Checklist

- [ ] System updated and secured
- [ ] PostgreSQL configured and operational
- [ ] Application installed and tested
- [ ] Gunicorn configured as service
- [ ] Nginx configured with SSL
- [ ] Monitoring and logs in place
- [ ] Automated backups configured
- [ ] Performance tests validated
- [ ] Enhanced security (fail2ban, firewall)
- [ ] Admin documentation updated

---

**🎉 VPS installation complete! Your GEC Mines system is in production.**

**Important URLs:**
- Application: `https://your-domain.com`
- System logs: `/var/log/gecmines-monitor.log`
- Application logs: `/home/gecmines/gec-mines/logs/`

For maintenance and support, consult DOCUMENTATION.md