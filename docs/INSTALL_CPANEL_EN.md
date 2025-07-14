# cPanel Installation - GEC Mines

## Overview

This guide details the complete installation of the GEC Mines system on shared hosting using cPanel, commonly used by web hosting providers.

## Prerequisites

### Hosting
- **cPanel** with full access
- **Python 3.11+** available
- **PostgreSQL** or **MySQL 8.0+** 
- **SSH** (optional but recommended)
- **Disk space**: 500 MB minimum
- **RAM**: 512 MB minimum

### Required Skills
- Basic cPanel usage
- Command line basics (optional)
- Environment variable configuration

## Step 1: Hosting Preparation

### 1.1 Prerequisites Verification
1. Log into your cPanel
2. Check Python version in **"Select Python App"** or **"Python Selector"**
3. Ensure PostgreSQL is available in **"PostgreSQL Databases"**

### 1.2 Database Creation
1. Access **"PostgreSQL Databases"** in cPanel
2. Create a new database:
   - Name: `gec_mines`
   - User: `gec_user`
   - Strong password
3. Note the connection information

## Step 2: Download and Installation

### 2.1 File Download
1. Download the GEC Mines package from the official repository
2. Use cPanel **"File Manager"**:
   - Navigate to `public_html` or `www` folder
   - Create a `gec-mines` folder
   - Upload and extract the archive

### 2.2 Recommended Structure
```
public_html/
└── gec-mines/
    ├── main.py
    ├── app.py
    ├── models.py
    ├── views.py
    ├── utils.py
    ├── requirements.txt
    ├── init_database.py
    ├── static/
    ├── templates/
    ├── uploads/
    ├── exports/
    ├── backups/
    ├── lang/
    └── docs/
```

## Step 3: Python Configuration

### 3.1 Python Application Creation
1. In cPanel, access **"Python App"**
2. Click **"Create Application"**
3. Configure:
   - **Python version**: 3.11 or higher
   - **Application root**: `/public_html/gec-mines`
   - **Application URL**: `gec-mines` or custom domain
   - **Startup file**: `main.py`

### 3.2 Dependencies Installation
1. Click **"Open terminal"** in the Python application
2. Execute:
```bash
pip install -r requirements.txt
```

Or use the cPanel interface to install:
- Flask
- Flask-SQLAlchemy
- Flask-Login
- psycopg2-binary
- reportlab
- werkzeug

## Step 4: Environment Variables Configuration

### 4.1 Configuration via cPanel
1. In Python application, **"Environment variables"** section
2. Add:
```
DATABASE_URL=postgresql://gec_user:PASSWORD@localhost:5432/gec_mines
SESSION_SECRET=your_unique_and_complex_secret_key
FLASK_ENV=production
```

### 4.2 .env File (alternative)
Create a `.env` file in the root directory:
```bash
DATABASE_URL=postgresql://gec_user:YOUR_PASSWORD@localhost:5432/gec_mines
SESSION_SECRET=your_very_long_and_complex_secret_key_here
FLASK_ENV=production
FLASK_DEBUG=False
```

## Step 5: Database Initialization

### 5.1 Via Terminal (recommended)
1. Open the Python application terminal
2. Execute:
```bash
python init_database.py
```

### 5.2 Via File Manager (alternative)
1. Use **"phpPgAdmin"** or equivalent
2. Manually import SQL files:
   - `docs/init_database.sql`
   - `docs/init_data.sql`

## Step 6: Folder Configuration

### 6.1 Folder Permissions
Configure permissions via File Manager:
```
uploads/     → 755 (rwxr-xr-x)
exports/     → 755 (rwxr-xr-x)
backups/     → 755 (rwxr-xr-x)
static/      → 755 (rwxr-xr-x)
lang/        → 644 (rw-r--r--)
```

### 6.2 Folder Security
Create `.htaccess` files to protect sensitive folders:

**uploads/.htaccess**:
```apache
<Files ~ "\.(jpg|jpeg|png|gif|pdf|doc|docx)$">
    Order allow,deny
    Allow from all
</Files>
<Files ~ "\.php$">
    Order allow,deny
    Deny from all
</Files>
```

**backups/.htaccess**:
```apache
Order allow,deny
Deny from all
```

## Step 7: Web Server Configuration

### 7.1 Custom Domain (optional)
1. In cPanel, **"Subdomains"**
2. Create a subdomain: `gec.yourdomain.com`
3. Point to `/public_html/gec-mines`

### 7.2 HTTPS Redirection
Create an `.htaccess` file in the root directory:
```apache
RewriteEngine On

# HTTPS redirection
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

# Sensitive files protection
<Files ~ "^\.">
    Order allow,deny
    Deny from all
</Files>

<Files ~ "\.py$">
    Order allow,deny
    Deny from all
</Files>

# Python application configuration
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ passenger_wsgi.py/$1 [QSA,L]
```

## Step 8: Testing and Verification

### 8.1 Application Testing
1. Restart the Python application in cPanel
2. Access your URL: `https://yourdomain.com/gec-mines`
3. Log in with:
   - Username: `admin`
   - Password: `admin123`

### 8.2 Post-installation Checks
- [ ] User interface displays correctly
- [ ] Administrator login functional
- [ ] Test mail registration
- [ ] Test file upload
- [ ] PDF export functional
- [ ] Backup system accessible

## Step 9: Production Configuration

### 9.1 Security
1. **Change administrator password**
2. **Configure SSL/TLS** via cPanel
3. **Limit IP access** if necessary
4. **Configure automatic backups**

### 9.2 Optimization
1. **Static cache**: enable CSS/JS resource caching
2. **Compression**: enable gzip in cPanel
3. **Monitoring**: configure error logs

### 9.3 Maintenance
Configure a cron job for maintenance:
```bash
# Daily cleanup at 2 AM
0 2 * * * cd /home/username/public_html/gec-mines && python -c "import os; os.system('find uploads/ -name \"*.tmp\" -mtime +1 -delete')"

# Weekly backup
0 3 * * 0 cd /home/username/public_html/gec-mines && python -c "from views import create_system_backup; create_system_backup()"
```

## Step 10: Troubleshooting

### 10.1 Common Issues

**Application won't start**:
- Check Python logs in cPanel
- Verify all modules are installed
- Check environment variables

**Database inaccessible**:
- Verify connection information
- Test connection via phpPgAdmin
- Check user permissions

**Permission errors**:
- Adjust folder permissions (755)
- Check file ownership
- Review .htaccess rules

### 10.2 Logs and Debugging
1. **Python logs**: `/tmp/` or application logs folder
2. **Apache logs**: cPanel → "Error Logs"
3. **Application logs**: Check activity logs in GEC

### 10.3 Technical Support
- Contact your hosting provider's support for configuration issues
- Check your hosting provider's Python documentation
- Consult cPanel community forums

## Maintenance and Updates

### Regular Backup
1. Use GEC's integrated backup function
2. Regularly download backups via File Manager
3. Backup database via phpPgAdmin

### Updates
1. Backup before any update
2. Download new version
3. Replace files (keep uploads/ and backups/)
4. Run migration scripts if necessary

---

**Support**: For technical assistance, consult the complete documentation in the `docs/` folder or contact the development team.

**Security**: ALWAYS change default passwords and enable HTTPS in production.