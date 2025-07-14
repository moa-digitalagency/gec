# cPanel Installation Guide - GEC Mines
## Step-by-Step Installation on Shared Hosting

---

## 📋 Prerequisites

### cPanel Hosting Requirements
- **PHP 8.0+** with extensions: PDO, SQLite, OpenSSL, Zip, cURL
- **Database**: MySQL/MariaDB or PostgreSQL
- **Disk Space**: Minimum 500MB (recommended 1GB)
- **PHP Memory**: Minimum 256MB (recommended 512MB)
- **SSH Access** (optional but recommended)

### Required Files
- Complete GEC Mines project archive
- Database credentials provided by hosting provider

---

## 🚀 Step 1: File Preparation

### 1.1 Download and Extract
```bash
# Create temporary folder on your computer
mkdir gec-mines-install
cd gec-mines-install

# Extract project archive
unzip gec-mines-complete.zip
```

### 1.2 Database Configuration
1. **Login to cPanel**
2. **Go to "MySQL Databases"**
3. **Create new database**:
   - Name: `your_prefix_gec_mines`
   - Note the full generated name

4. **Create database user**:
   - Username: `your_prefix_gec`
   - Password: Generate secure password
   - Write down these credentials!

5. **Assign user to database**:
   - Grant ALL privileges

---

## 🔧 Step 2: File Upload

### 2.1 Via cPanel File Manager
1. **Open File Manager**
2. **Navigate to `public_html`** (or your chosen subfolder)
3. **Upload** `gec-mines-complete.zip` archive
4. **Right-click → Extract** the archive
5. **Move all files** from extracted folder to `public_html`

### 2.2 Via FTP (alternative)
```bash
# FTP settings (provided by your host)
ftp://your-domain.com
Username: your_ftp_user
Password: your_ftp_password

# Upload all files to public_html/
```

---

## ⚙️ Step 3: Configuration

### 3.1 Environment Variables
Create `.env` file in root directory:

```bash
# Database
DATABASE_URL=mysql://your_db_user:password@localhost/your_db_name

# Security
SESSION_SECRET=your_very_long_random_secret_key_here

# Configuration
FLASK_ENV=production
FLASK_DEBUG=False
UPLOAD_FOLDER=uploads
EXPORT_FOLDER=exports
```

### 3.2 .htaccess File
Create `.htaccess` file in `public_html`:

```apache
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ index.php [QSA,L]

# PHP Configuration
php_value memory_limit 512M
php_value max_execution_time 300
php_value upload_max_filesize 16M
php_value post_max_size 32M

# Security
<Files ".env">
    Order allow,deny
    Deny from all
</Files>

<Files "*.py">
    Order allow,deny
    Deny from all
</Files>
```

### 3.3 PHP Entry Point
Create `index.php` file in `public_html`:

```php
<?php
// Entry point for Python Flask on cPanel
$command = "cd " . __DIR__ . " && python3 main.py 2>&1";
$output = shell_exec($command);

if ($output === null) {
    // Fallback for restrictive hosting
    header('Content-Type: text/html');
    echo '<html><body>';
    echo '<h1>GEC Mines - Mail Management System</h1>';
    echo '<p>Configuration in progress...</p>';
    echo '<p>Contact your administrator if this page persists.</p>';
    echo '</body></html>';
} else {
    echo $output;
}
?>
```

---

## 🗃️ Step 4: Database Initialization

### 4.1 Via cPanel Terminal (if available)
```bash
cd public_html
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database initialized successfully!')
"
```

### 4.2 Via phpMyAdmin (alternative)
1. **Login to phpMyAdmin**
2. **Select your database**
3. **Import SQL file**: `database_schema.sql`
4. **Execute initialization queries**

---

## 🔐 Step 5: Security Configuration

### 5.1 Folder Permissions
```bash
# Via File Manager or SSH
chmod 755 public_html/
chmod 755 uploads/
chmod 755 exports/
chmod 755 static/
chmod 644 *.py
chmod 600 .env
```

### 5.2 Sensitive Folder Protection
Create `.htaccess` files in:

**uploads/.htaccess**:
```apache
Options -Indexes
<Files "*.py">
    Order allow,deny
    Deny from all
</Files>
```

**backups/.htaccess**:
```apache
Order allow,deny
Deny from all
```

---

## 🎯 Step 6: Testing and Validation

### 6.1 Initial Access
1. **Visit your site**: `https://your-domain.com`
2. **Login page** should display
3. **Login with**:
   - Username: `admin`
   - Password: `admin123`

### 6.2 Functional Tests
- ✅ **Administrator login**
- ✅ **Register test mail**
- ✅ **File upload**
- ✅ **PDF export**
- ✅ **Search function**
- ✅ **System settings**

### 6.3 SSL Configuration (recommended)
1. **Enable SSL** in cPanel
2. **Force HTTPS** via .htaccess:
```apache
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
```

---

## 🔧 Step 7: Optimizations

### 7.1 Performance
Add to `.htaccess`:
```apache
# Compression
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/html text/css text/javascript application/javascript
</IfModule>

# Browser Cache
<IfModule mod_expires.c>
    ExpiresActive on
    ExpiresByType text/css "access plus 1 month"
    ExpiresByType application/javascript "access plus 1 month"
    ExpiresByType image/png "access plus 1 month"
    ExpiresByType image/jpg "access plus 1 month"
    ExpiresByType image/jpeg "access plus 1 month"
</IfModule>
```

### 7.2 Error Logs
Create `logs/` folder with 755 permissions:
```bash
mkdir logs
chmod 755 logs
```

### 7.3 CRON Jobs (optional)
In cPanel → CRON Jobs, add:
```bash
# Temporary file cleanup (daily)
0 2 * * * cd /home/username/public_html && python3 -c "import os, time; [os.remove(f'exports/{f}') for f in os.listdir('exports') if f.endswith('.pdf') and os.path.getmtime(f'exports/{f}') < time.time() - 604800]"
```

---

## 🚨 Troubleshooting

### Common Issues

**"Internal Server Error"**
- Check file permissions
- Review cPanel error logs
- Verify .htaccess configuration

**"Database inaccessible"**
- Validate DATABASE_URL in .env
- Check MySQL user privileges
- Test connection via phpMyAdmin

**"Python module not found"**
- Verify Python 3.8+ is installed
- Contact host for Python activation
- Use PHP alternative if necessary

**"File upload fails"**
- Check upload_max_filesize in PHP
- Increase post_max_size
- Verify uploads/ folder permissions

### Technical Support
- **Documentation**: Consult DOCUMENTATION.md
- **Logs**: Enable debug mode temporarily
- **Hosting**: Contact support for server issues

---

## ✅ Final Checklist

- [ ] Database created and configured
- [ ] Files uploaded and permissions set
- [ ] Environment variables configured
- [ ] Login tests successful
- [ ] Upload and export functional
- [ ] SSL activated
- [ ] Admin password changed
- [ ] Initial backup created

---

**🎉 Congratulations! Your GEC Mines system is operational on cPanel.**

For technical assistance, consult the complete documentation or contact your system administrator.