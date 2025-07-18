# Installing GEC Mines on PythonAnywhere

## 🚀 Quick Setup Guide

Deploy GEC Mines on PythonAnywhere in 30 minutes with this simplified guide.

## Prerequisites

- PythonAnywhere account (free works for testing)
- GEC Mines source code
- 30 minutes of your time

## ⚡ Quick Installation

### Step 1: Create Account
1. Go to [pythonanywhere.com](https://www.pythonanywhere.com)
2. Create a free account
3. Log in to the dashboard

### Step 2: Upload Files
1. Click **"Files"** in the menu
2. Create a `gec-mines` folder in your home directory
3. Upload all GEC Mines project files to this folder

### Step 3: Install Dependencies
1. Open a **Bash** console (Console tab)
2. Run these commands:
```bash
cd ~/gec-mines
python3.11 -m venv venv
source venv/bin/activate
pip install flask flask-sqlalchemy flask-login werkzeug reportlab pillow
```

### Step 4: Database Setup (SQLite for Free)
```bash
# In the console
mkdir -p ~/gec-mines/instance
echo "DATABASE_URL=sqlite:///instance/gec_mines.db" > ~/gec-mines/.env
echo "SESSION_SECRET=your-random-secret-key-here" >> ~/gec-mines/.env
```

### Step 5: Initialize Database
```bash
cd ~/gec-mines
source venv/bin/activate
python init_database.py
```

### Step 6: Create Web App
1. Go to **"Web"** tab
2. Click **"Add a new web app"**
3. Choose your free domain
4. Select **"Manual configuration"**
5. Choose **Python 3.11**

### Step 7: Configure WSGI
1. Click on the WSGI file link (e.g., `/var/www/username_pythonanywhere_com_wsgi.py`)
2. Replace all content with:
```python
import sys
import os

# Your username here
username = "YOUR_USERNAME"
path = f'/home/{username}/gec-mines'

if path not in sys.path:
    sys.path.insert(0, path)

# Environment variables
os.environ['DATABASE_URL'] = f'sqlite:///{path}/instance/gec_mines.db'
os.environ['SESSION_SECRET'] = 'production-secret-key'

from main import app as application
```

### Step 8: Final Configuration
**In the Web tab, set:**
- **Virtualenv**: `/home/YOUR_USERNAME/gec-mines/venv`
- **Static files**: 
  - URL `/static/` → Directory `/home/YOUR_USERNAME/gec-mines/static/`
  - URL `/uploads/` → Directory `/home/YOUR_USERNAME/gec-mines/uploads/`

### Step 9: Test Your App
1. Click **"Reload"** in the Web tab
2. Visit your site: `https://YOUR_USERNAME.pythonanywhere.com`
3. Login with: `admin` / `admin123`

## ✅ App Ready!

Your GEC Mines is now online. Change the admin password after first login.

## 🔧 Quick Troubleshooting

**Error 500?** Check the error logs in PythonAnywhere's "Error log" tab.

**Blank page?** Verify virtualenv and static files are configured correctly.

**Empty database?** Run `python init_database.py` again in the console.

## 📞 Support

- [PythonAnywhere Documentation](https://help.pythonanywhere.com/)
- [Flask Help](https://help.pythonanywhere.com/pages/Flask/)

---

**Guide Version**: Simplified 1.0 | **Setup Time**: ~30 minutes