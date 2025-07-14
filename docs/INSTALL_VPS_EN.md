# VPS Installation - GEC Mines

## Overview

This guide details the complete installation of the GEC Mines system on a Virtual Private Server (VPS) Ubuntu/Debian with secure production configuration.

## Prerequisites

### Server
- **VPS Ubuntu 20.04+ or Debian 11+**
- **RAM**: 2 GB minimum (4 GB recommended)
- **Disk space**: 10 GB minimum (20 GB recommended)
- **Root access** or sudo
- **Stable internet** connection

### Required Services
- Python 3.11+
- PostgreSQL 14+
- Nginx
- Supervisor (for process management)
- Certbot (for SSL)

## Step 1: Server Preparation

### 1.1 System Update
```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install basic tools
sudo apt install -y curl wget git unzip vim htop
```

### 1.2 User Configuration
```bash
# Create dedicated user for the application
sudo adduser gecmines
sudo usermod -aG sudo gecmines

# Switch to gecmines user
su - gecmines
```

### 1.3 SSH Configuration (security)
```bash
# Generate SSH key if needed
ssh-keygen -t rsa -b 4096 -C "admin@gec-mines.cd"

# Secure SSH configuration (in /etc/ssh/sshd_config)
sudo vim /etc/ssh/sshd_config
```

Modify the following parameters:
```
Port 2222                    # Change default port
PermitRootLogin no          # Disable root login
PasswordAuthentication no   # Use SSH keys only
PubkeyAuthentication yes
```

Restart SSH service:
```bash
sudo systemctl restart ssh
```

## Step 2: Python and Dependencies Installation

### 2.1 Python 3.11 Installation
```bash
# Add deadsnakes repository for Python 3.11
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# Install Python 3.11 and tools
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
sudo apt install -y build-essential libpq-dev

# Create symbolic link
sudo ln -sf /usr/bin/python3.11 /usr/bin/python3
```

### 2.2 PostgreSQL Installation and Configuration
```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start and enable service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Configure PostgreSQL
sudo -u postgres psql
```

In PostgreSQL shell:
```sql
-- Create user and database
CREATE USER gecmines_user WITH PASSWORD 'secure_password_here';
CREATE DATABASE gecmines_db WITH OWNER gecmines_user ENCODING 'UTF8';
GRANT ALL PRIVILEGES ON DATABASE gecmines_db TO gecmines_user;

-- Production optimization
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
\q
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

## Step 3: Application Installation

### 3.1 Clone and Setup
```bash
# Navigate to home directory
cd /home/gecmines

# Clone project (or download archive)
git clone <repository-url> gec-mines
cd gec-mines

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### 3.2 Environment Variables Configuration
```bash
# Create configuration file
vim .env
```

Content of `.env` file:
```bash
# Database configuration
DATABASE_URL=postgresql://gecmines_user:secure_password_here@localhost:5432/gecmines_db

# Secret key (generate a strong key)
SESSION_SECRET=your_very_long_and_complex_secret_generated_with_openssl

# Production configuration
FLASK_ENV=production
FLASK_DEBUG=False

# Path configuration
UPLOAD_FOLDER=/home/gecmines/gec-mines/uploads
BACKUP_FOLDER=/home/gecmines/gec-mines/backups
```

### 3.3 Database Initialization
```bash
# Export environment variables
source .env

# Initialize database
python init_database.py

# Verify installation
python init_database.py --verify
```

### 3.4 Permissions Configuration
```bash
# Create and configure necessary folders
mkdir -p uploads exports backups logs
chmod 755 uploads exports backups
chmod 644 static/css/* static/js/*

# File ownership
sudo chown -R gecmines:gecmines /home/gecmines/gec-mines
```

## Step 4: Gunicorn Configuration

### 4.1 Gunicorn Configuration
```bash
# Create Gunicorn configuration file
vim gunicorn.conf.py
```

File content:
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

### 4.2 Gunicorn Test
```bash
# Startup test
source venv/bin/activate
gunicorn --config gunicorn.conf.py main:app
```

## Step 5: Supervisor Configuration

### 5.1 Supervisor Installation and Configuration
```bash
# Installation
sudo apt install -y supervisor

# Create configuration file
sudo vim /etc/supervisor/conf.d/gecmines.conf
```

Configuration file content:
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
environment=DATABASE_URL="postgresql://gecmines_user:secure_password_here@localhost:5432/gecmines_db",SESSION_SECRET="your_secret_key"
```

### 5.2 Supervisor Startup
```bash
# Reload configuration
sudo supervisorctl reread
sudo supervisorctl update

# Start application
sudo supervisorctl start gecmines

# Check status
sudo supervisorctl status gecmines
```

## Step 6: Nginx Configuration

### 6.1 Nginx Installation
```bash
# Installation
sudo apt install -y nginx

# Create site configuration
sudo vim /etc/nginx/sites-available/gecmines
```

### 6.2 Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # HTTPS redirection
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # SSL certificates (to be configured with Certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Secure SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
    
    # Log configuration
    access_log /var/log/nginx/gecmines_access.log;
    error_log /var/log/nginx/gecmines_error.log;
    
    # Maximum upload size
    client_max_body_size 16M;
    
    # Static files
    location /static {
        alias /home/gecmines/gec-mines/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Upload files (protected)
    location /uploads {
        internal;
        alias /home/gecmines/gec-mines/uploads;
    }
    
    # Main application
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
    
    # Sensitive files protection
    location ~ /\. {
        deny all;
    }
    
    location ~ \.py$ {
        deny all;
    }
}
```

### 6.3 Site Activation
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/gecmines /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## Step 7: SSL Configuration with Certbot

### 7.1 Certbot Installation
```bash
# Installation
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### 7.2 Automatic Renewal
```bash
# Test renewal
sudo certbot renew --dry-run

# Automatic renewal is configured via cron
# Check: sudo crontab -l
```

## Step 8: Firewall Configuration

### 8.1 UFW Configuration
```bash
# Enable UFW
sudo ufw enable

# Basic rules
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (custom port)
sudo ufw allow 2222/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow PostgreSQL locally only
sudo ufw allow from 127.0.0.1 to any port 5432

# Check rules
sudo ufw status verbose
```

## Step 9: Monitoring and Maintenance

### 9.1 Log Configuration
```bash
# Logrotate for application logs
sudo vim /etc/logrotate.d/gecmines
```

Content:
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

### 9.2 Maintenance Scripts
```bash
# Create automatic backup script
vim /home/gecmines/backup.sh
```

Script content:
```bash
#!/bin/bash
cd /home/gecmines/gec-mines
source venv/bin/activate
source .env

# Database backup
pg_dump $DATABASE_URL > "backups/db_backup_$(date +%Y%m%d_%H%M%S).sql"

# Clean old backups (keep 30 days)
find backups/ -name "db_backup_*.sql" -mtime +30 -delete

# Complete backup via application (weekly)
if [ $(date +%u) -eq 7 ]; then
    python -c "from views import create_system_backup; create_system_backup()"
fi
```

Make executable and schedule:
```bash
chmod +x /home/gecmines/backup.sh

# Add to crontab
crontab -e
```

Add:
```
# Daily backup at 2 AM
0 2 * * * /home/gecmines/backup.sh

# Weekly restart at 3 AM on Sunday
0 3 * * 0 sudo supervisorctl restart gecmines
```

## Step 10: Testing and Verification

### 10.1 Functionality Tests
```bash
# Check services
sudo systemctl status postgresql
sudo systemctl status nginx
sudo supervisorctl status gecmines

# Test web access
curl -I https://your-domain.com

# Check logs
tail -f /home/gecmines/gec-mines/logs/error.log
```

### 10.2 Application Tests
1. Access `https://your-domain.com`
2. Log in with `admin` / `admin123`
3. Test mail registration
4. Test file upload
5. Test PDF export
6. Verify backup function

## Post-installation Security

### Server Hardening
1. **Regular updates**: `sudo apt update && sudo apt upgrade`
2. **Configure fail2ban** for SSH protection
3. **Install monitoring tools** (htop, netstat, ss)
4. **Configure alerts** for disk space and load
5. **Regular security audits** of security logs

### Monitoring
- Configure monitoring alerts
- Check Nginx access logs
- Monitor resource usage
- Audit SSH connections

---

**Important**: Change ALL default passwords and configure a robust backup strategy before production deployment.

**Support**: Consult complete documentation in `docs/` for troubleshooting and advanced maintenance.