# Installing GEC Mines on PythonAnywhere

## Overview

This guide walks you through deploying the GEC Mines system on PythonAnywhere, a Python hosting platform specially designed for Flask and Django applications.

## Prerequisites

- **PythonAnywhere Account**: Free or paid account
- **Project Files**: GEC Mines source code
- **Database**: PostgreSQL or MySQL (depending on your plan)

## Step 1: Account Preparation

### 1.1 Account Creation
1. Go to [https://www.pythonanywhere.com](https://www.pythonanywhere.com)
2. Create an account (free or paid according to your needs)
3. Log in to your dashboard

### 1.2 Plan Verification
- **Free account**: Limited to 1 web app, SQLite only
- **Paid account**: Multiple applications, PostgreSQL/MySQL available

## Step 2: File Upload

### 2.1 Via Web Interface
1. Go to the **"Files"** tab
2. Navigate to your home directory (`/home/yourusername/`)
3. Create a `gec-mines` folder
4. Upload all project files

### 2.2 Via Git (Recommended)
```bash
# In the PythonAnywhere Bash console
cd ~
git clone https://github.com/your-repo/gec-mines.git
cd gec-mines
```

## Step 3: Virtual Environment Configuration

### 3.1 Environment Creation
```bash
# In the Bash console
cd ~/gec-mines
python3.11 -m venv venv
source venv/bin/activate
```

### 3.2 Dependencies Installation
```bash
# Update pip
pip install --upgrade pip

# Install required packages
pip install flask flask-sqlalchemy flask-login
pip install werkzeug reportlab
pip install psycopg2-binary  # For PostgreSQL
pip install gunicorn
pip install pillow  # For image/logo handling
```

### 3.3 Create requirements.txt file
```bash
pip freeze > requirements.txt
```

## Step 4: Database Configuration

### 4.1 For PostgreSQL (Paid Accounts)
1. Go to the **"Databases"** tab
2. Create a new PostgreSQL database
3. Note the connection information:
   - Host: `username-xxxx.postgres.pythonanywhere-services.com`
   - Database: `username$gec_mines`
   - Username: `username`
   - Password: `your-password`

### 4.2 For MySQL (Alternative)
```sql
-- Database creation
CREATE DATABASE username$gec_mines CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4.3 For SQLite (Free Account)
```bash
# Database will be created automatically
mkdir -p ~/gec-mines/instance
```

## Step 5: Environment Variables Configuration

### 5.1 Create .env file
```bash
cd ~/gec-mines
nano .env
```

### 5.2 .env file content
```bash
# For PostgreSQL
DATABASE_URL=postgresql://username:password@username-xxxx.postgres.pythonanywhere-services.com/username$gec_mines

# For MySQL
# DATABASE_URL=mysql://username:password@username.mysql.pythonanywhere-services.com/username$gec_mines

# For SQLite (free account)
# DATABASE_URL=sqlite:///instance/gec_mines.db

# Secret key for sessions
SESSION_SECRET=your-very-long-and-random-secret-key

# Production mode
FLASK_ENV=production
```

## Step 6: Database Initialization

### 6.1 Modify initialization script
```bash
cd ~/gec-mines
nano init_database.py
```

Add at the beginning of the file:
```python
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
```

### 6.2 Execute initialization
```bash
source venv/bin/activate
python init_database.py
```

## Step 7: Web Application Configuration

### 7.1 Create Web Application
1. Go to the **"Web"** tab
2. Click **"Add a new web app"**
3. Choose your domain (e.g., `username.pythonanywhere.com`)
4. Select **"Manual configuration"**
5. Choose **Python 3.11**

### 7.2 WSGI file configuration
```python
# Content of /var/www/username_pythonanywhere_com_wsgi.py

import sys
import os
from dotenv import load_dotenv

# Add project directory to path
path = '/home/username/gec-mines'
if path not in sys.path:
    sys.path.insert(0, path)

# Load environment variables
load_dotenv(os.path.join(path, '.env'))

# Import Flask application
from main import app as application

if __name__ == "__main__":
    application.run()
```

### 7.3 Static Files Configuration
1. In the **"Web"** tab, **"Static files"** section
2. Add:
   - URL: `/static/`
   - Directory: `/home/username/gec-mines/static/`
3. Add for uploads:
   - URL: `/uploads/`
   - Directory: `/home/username/gec-mines/uploads/`

### 7.4 Virtual Environment Configuration
1. In the **"Web"** tab, **"Virtualenv"** section
2. Enter: `/home/username/gec-mines/venv`

## Step 8: Security and Optimization

### 8.1 Create Necessary Directories
```bash
cd ~/gec-mines
mkdir -p uploads/{profiles,backups}
mkdir -p exports
mkdir -p logs
chmod 755 uploads exports logs
```

### 8.2 Logs Configuration
```bash
# Create log file
touch ~/gec-mines/logs/app.log
chmod 644 ~/gec-mines/logs/app.log
```

### 8.3 File Security
```bash
# Protect sensitive files
chmod 600 ~/gec-mines/.env
chmod 644 ~/gec-mines/*.py
```

## Step 9: Testing and Validation

### 9.1 Application Restart
1. In the **"Web"** tab
2. Click **"Reload username.pythonanywhere.com"**

### 9.2 Functionality Verification
1. Visit `https://username.pythonanywhere.com`
2. Verify the login page displays
3. Test login with admin credentials
4. Check all main functionalities

### 9.3 Logs Verification
```bash
# Check error logs
tail -f /var/log/username.pythonanywhere.com.error.log

# Check access logs
tail -f /var/log/username.pythonanywhere.com.access.log
```

## Step 10: Maintenance and Monitoring

### 10.1 Automatic Backups
```bash
#!/bin/bash
# Backup script to place in ~/backup_gec.sh

cd ~/gec-mines
source venv/bin/activate

# Database backup
if [[ $DATABASE_URL == postgresql* ]]; then
    pg_dump $DATABASE_URL > backups/db_backup_$(date +%Y%m%d_%H%M%S).sql
elif [[ $DATABASE_URL == mysql* ]]; then
    mysqldump --single-transaction --routines --triggers gec_mines > backups/db_backup_$(date +%Y%m%d_%H%M%S).sql
else
    cp instance/gec_mines.db backups/db_backup_$(date +%Y%m%d_%H%M%S).db
fi

# Upload files backup
tar -czf backups/uploads_backup_$(date +%Y%m%d_%H%M%S).tar.gz uploads/

# Clean old backups (keep 7 days)
find backups/ -name "*.sql" -mtime +7 -delete
find backups/ -name "*.tar.gz" -mtime +7 -delete
find backups/ -name "*.db" -mtime +7 -delete
```

### 10.2 Cron Tasks
```bash
# Add to crontab (command: crontab -e)
# Daily backup at 2 AM
0 2 * * * /home/username/backup_gec.sh

# Weekly log cleanup
0 3 * * 0 find /home/username/gec-mines/logs/ -name "*.log" -mtime +30 -delete
```

## Step 11: Advanced Optimizations

### 11.1 Cache Configuration
```python
# Add to main.py for static caching
from flask import Flask
from datetime import timedelta

app = Flask(__name__)

@app.after_request
def add_header(response):
    if request.endpoint == 'static':
        response.cache_control.max_age = 31536000  # 1 year
    return response
```

### 11.2 Gzip Compression
```python
# Install and configure Flask-Compress
# pip install Flask-Compress

from flask_compress import Compress

app = Flask(__name__)
Compress(app)
```

## Troubleshooting

### Common Issues

#### 1. "Internal Server Error"
```bash
# Check logs
tail -f /var/log/username.pythonanywhere.com.error.log
```

#### 2. Database unreachable
- Check connection information in `.env`
- Test connection from console

#### 3. Static files not served
- Check static folder configuration
- Check folder permissions

#### 4. File upload not working
```bash
# Check permissions
chmod 755 uploads/
chmod 644 uploads/*
```

### Useful Commands

```bash
# Restart application
touch /var/www/username_pythonanywhere_com_wsgi.py

# View Python processes
ps aux | grep python

# Test configuration
cd ~/gec-mines
source venv/bin/activate
python -c "from main import app; print('Configuration OK')"
```

## Additional Resources

- [PythonAnywhere Documentation](https://help.pythonanywhere.com/)
- [Flask Guide on PythonAnywhere](https://help.pythonanywhere.com/pages/Flask/)
- [Database Configuration](https://help.pythonanywhere.com/pages/Databases/)

## Support

For help:
1. Check error logs
2. Review PythonAnywhere documentation
3. Contact PythonAnywhere support if necessary

---

**Guide Version**: 1.0  
**Last Update**: July 2025  
**Compatibility**: PythonAnywhere, Python 3.11+, PostgreSQL/MySQL/SQLite