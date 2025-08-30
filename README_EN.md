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
- Python 3.8+
- PostgreSQL
- Web server (recommended: Gunicorn)

### Environment Variables
```
DATABASE_URL=postgresql://user:password@host:port/database
SESSION_SECRET=your_secret_key
SENDGRID_API_KEY=your_sendgrid_key (optional)
GEC_MASTER_KEY=your_encryption_key
GEC_PASSWORD_SALT=your_password_salt
```

### Quick Start
```bash
# Install dependencies
pip install -r project-dependencies.txt

# Database configuration
# (Tables are created automatically)

# Start the application
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

## New Features (August 2025)

### Dynamic Nomenclature
- **Configurable leadership titles** (e.g., Secretary General, Director)
- **Automatic adaptation** in all templates and exports
- **Configuration interface** in system parameters

### Advanced Notifications
- **Smart targeting** for comments/annotations/instructions
- **Multi-recipient notifications**: creator + last recipient
- **Specialized email templates** by action type
- **Permission-based notification system**

### PDF Improvements
- **"En Copie" text** instead of "SG Copie" for more flexibility
- **Automatic adaptation** to configured nomenclature
- **Optimized layout** for all organization types

### Migration System
- **Automatic database column migration**
- **Smart detection** of schema changes
- **Existing data preservation**
- **Detailed information messages**

## Support and Contribution

This system is developed to meet the specific needs of administrations and can be adapted according to organizational requirements.

For more technical information, consult the source code or contact the development team.

---

**GEC - Mail Management System**  
*Digital solution for modern administration*