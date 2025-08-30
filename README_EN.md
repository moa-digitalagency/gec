# GEC - Electronic Mail Management System

**[Version Française](README.md)**

## Overview

GEC (Gestion Électronique du Courrier) is a comprehensive Flask web application for digital mail correspondence management. Specifically developed for government administrations and enterprises, it provides a secure and auditable solution for registering, tracking, and managing mail documents with file attachments.

## Main Features

### 🔐 Authentication and Security
- **Secure user authentication** with Flask-Login
- **AES-256 encryption** for all sensitive data
- **bcrypt hashing** with custom salts for passwords
- **Attack protection**: brute force, SQL injection, XSS
- **Automatic IP blocking** after failed login attempts
- **File integrity verification** with checksums
- **Secure file deletion**
- **Complete security and audit logging**

### 👥 User and Role Management
- **Three-tier role system**: Super Admin, Admin, User
- **Configurable granular permissions**
- **Role-based access control** (RBAC)
- **Department management** and assignments
- **User profiles** with contact information

### 📧 Mail Management
- **Incoming and outgoing mail registration**
- **Mandatory file attachments** for all mail types
- **Automatic numbering** with receipt acknowledgments
- **Configurable statuses**: Pending, In Progress, Processed, Archived
- **Advanced search** with multiple filters
- **Customizable outgoing mail types**
- **Sender/recipient management**

### 💬 Comments and Annotations System
- **Comments, annotations, and instructions** on mail items
- **In-app notifications** and email notifications
- **Smart targeting**: creator + last person who received the mail
- **Complete interaction history**

### 🔄 Transmission and Tracking
- **Mail transmission** between users
- **Automatic transmission notifications**
- **Transmission history** with dates and messages
- **Automatic read marking**
- **Real-time status tracking**

### 🔔 Notifications
- **Real-time in-app notifications**
- **Configurable email notifications**
- **Customizable email templates**
- **SendGrid and SMTP integration**
- **Targeted notifications** based on permissions

### 📊 Dashboards and Reports
- **Analytics dashboard** with real-time statistics
- **Interactive charts** (Chart.js)
- **PDF and Excel export** of reports
- **Performance metrics** and KPIs
- **Department and user statistics**

### 📄 Document Generation
- **PDF export** with professional layout
- **Automatic registration receipts**
- **Formatted mail lists**
- **Customizable headers and footers**
- **Dynamic logos and signatures**

### ⚙️ System Configuration
- **Fully configurable system parameters**
- **Customizable logos** (header and signature)
- **Dynamic organizational nomenclature**
- **Customizable numbering formats**
- **Email configuration** (SMTP/SendGrid)
- **Status and mail type management**

### 🌍 Multi-language
- **French and English support**
- **JSON translation files**
- **Real-time language switching**
- **Fully localized interface**

### 🔒 Backup and Migration
- **Automatic backup system**
- **Automatic database migration**
- **Automatic detection and addition** of new columns
- **Existing data preservation**
- **Rollback system** with checkpoints

## Technologies Used

### Backend
- **Flask** (Python web framework)
- **SQLAlchemy** with Flask-SQLAlchemy (ORM)
- **PostgreSQL** (Primary database)
- **ReportLab** (PDF generation)
- **bcrypt + cryptography** (Security)
- **SendGrid** (Email service)

### Frontend
- **Jinja2** (Template engine)
- **Tailwind CSS** (CSS framework)
- **Font Awesome** (Icons)
- **DataTables** (Interactive tables)
- **Chart.js** (Charts)
- **jQuery** (JavaScript interactions)

### Security
- **AES-256-CBC** for data encryption
- **bcrypt** for password hashing
- **CSRF protection** and security headers
- **Input validation and sanitization**
- **Complete audit logging**

## Design and UX

- **DRC colors**: Blue (#003087), Yellow (#FFD700), Red (#CE1126), Green (#009639)
- **Responsive adaptive design**
- **Intuitive and ergonomic interface**
- **Universal hamburger menu**
- **Aspect ratio preservation** for logos
- **Consistent corporate theme**

## Installation and Deployment

### Prerequisites
- Python 3.11+ (recommended)
- Git
- PostgreSQL (optional, SQLite by default)

### 🪟 Windows Installation (10/11)

```powershell
# Install Python 3.11
winget install --id Python.Python.3.11 -e

# Install Git
winget install --id Git.Git -e

# Clone the project
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# Configure PowerShell for scripts
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force

# Create virtual environment
python -m venv .venv
# If error, try: py -3.11 -m venv .venv

# Activate environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

# Launch application
python .\main.py
```

### 🖥️ Windows Server Installation (2008/2012/2016/2019/2022)

```cmd
REM Download Python from python.org if winget unavailable
REM Or use chocolatey: choco install python git

REM Clone the project
git clone https://github.com/moa-digitalagency/gec.git
cd gec

REM Create virtual environment
python -m venv .venv

REM Activate environment
.venv\Scripts\activate.bat

REM Install dependencies
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

REM Launch application
python main.py
```

### 🍎 macOS Installation (10.15+)

```bash
# Install Homebrew if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11 and Git
brew install python@3.11 git

# Clone the project
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# Create virtual environment
python3.11 -m venv .venv

# Activate environment
source .venv/bin/activate

# Install dependencies
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

# Launch application
python main.py
```

### 🐧 Linux Installation

#### Ubuntu/Debian
```bash
# Update system
sudo apt update

# Install Python 3.11 and dependencies
sudo apt install python3.11 python3.11-venv python3.11-dev git postgresql-client -y

# Clone the project
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# Create virtual environment
python3.11 -m venv .venv

# Activate environment
source .venv/bin/activate

# Install dependencies
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

# Launch application
python main.py
```

#### CentOS/RHEL/Fedora
```bash
# For Fedora/CentOS Stream
sudo dnf install python3.11 python3.11-devel git postgresql -y

# For RHEL/CentOS 7-8 (older versions)
sudo yum install python3.11 python3.11-devel git postgresql -y

# Clone the project
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# Create virtual environment
python3.11 -m venv .venv

# Activate environment
source .venv/bin/activate

# Install dependencies
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

# Launch application
python main.py
```

#### Arch Linux
```bash
# Install dependencies
sudo pacman -S python git postgresql

# Clone the project
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# Create virtual environment
python -m venv .venv

# Activate environment
source .venv/bin/activate

# Install dependencies
python -m pip install -U pip wheel
python -m pip install -r project-dependencies.txt

# Launch application
python main.py
```

### Environment Variables

Create a `.env` file in the project folder:

```bash
DATABASE_URL=postgresql://user:password@host:port/database
SESSION_SECRET=your_secret_key_here
SENDGRID_API_KEY=your_sendgrid_key (optional)
GEC_MASTER_KEY=your_encryption_key_32_chars
GEC_PASSWORD_SALT=your_password_salt
```

### Production Deployment

#### With Gunicorn (Linux/macOS)
```bash
# Install Gunicorn
pip install gunicorn

# Launch in production
gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
```

#### With Waitress (Windows)
```powershell
# Install Waitress
pip install waitress

# Launch in production
waitress-serve --host=0.0.0.0 --port=5000 main:app
```

### 🔧 Troubleshooting

**Python not found error (Windows)**:
- Restart your terminal after installation
- Use `py` instead of `python`
- Check PATH in environment variables

**PowerShell permissions error**:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
```

**Pip outdated error**:
```bash
python -m pip install --upgrade pip
```

**Port 5000 in use**:
```bash
# Change port in main.py or use
python main.py --port 8080
```

## Support and Contribution

This system is developed to meet the specific needs of administrations and can be adapted according to organizational requirements.

### 👨‍💻 Developer and Designer
**AIsance KALONJI wa KALONJI**

### 🏢 Copyright and License
**© 2025 MOA Digital Agency LLC** - All rights reserved

### 📞 Contact Information

**MOA Digital Agency**
- **📧 Email**: moa@myoneart.com
- **📧 Alternative Email**: moa.myoneart@gmail.com
- **📱 Phone Morocco**: +212 699 14 000 1
- **📱 Phone DRC**: +243 86 049 33 45
- **🌐 Website**: [myoneart.com](https://myoneart.com)

### 🤝 Technical Support

For technical assistance, custom modifications, or deployment questions:

1. **Email Support**: Contact us at moa@myoneart.com
2. **Documentation**: Refer to this README for installation instructions
3. **Customization**: MOA Digital Agency offers custom adaptation services

### 💼 About MOA Digital Agency

MOA Digital Agency LLC is a development agency specialized in creating custom digital solutions for businesses and government institutions. We excel in developing robust, secure, and scalable web applications.

**Areas of Expertise**:
- Enterprise web applications
- Administrative management systems
- Advanced security solutions
- Data integration and migration

---

**GEC - Mail Management System**  
*Digital solution for modern administration*