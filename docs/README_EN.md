# GEC Mines - Electronic Mail Management System

## Overview

GEC Mines is a comprehensive electronic mail management system developed for the General Secretariat of Mines of the Democratic Republic of Congo. The system efficiently manages incoming and outgoing mail with complete tracking, role-based permissions, and advanced export capabilities.

## Key Features

### 🏢 Administrative Management
- **Role System**: Super Admin, Admin, User with granular permissions
- **Department Management**: Hierarchical organization with department heads
- **Secure Authentication**: Login system with password hashing
- **User Profiles**: Profile photos and personalized information

### 📬 Mail Management
- **Mail Types**: Clear distinction between incoming and outgoing mail
- **Complete Registration**: 
  - Drafting date (optional)
  - Automatic registration date
  - Automatic receipt numbers
  - File attachments (PDF, images)
- **Status Tracking**: Customizable statuses with color codes
- **Advanced Search**: Multiple filters and text search

### 📊 Reports and Exports
- **Individual PDF Export**: Formatted receipt acknowledgment
- **List Exports**: PDF reports with applied filters
- **Printing**: Direct print functionality
- **Backup/Restore**: Complete backup system

### 🌍 Multilingual System
- **Supported Languages**: French (default) and English
- **Adaptable Interface**: Real-time language switching
- **User Preferences**: Language saved per user

### 🔐 Security and Permissions
- **Granular Access**:
  - `read_all_mail`: Access to all mail (Super Admin)
  - `read_department_mail`: Access to department mail (Admin)
  - `read_own_mail`: Access to personal mail (User)
- **Activity Logging**: Complete activity logs
- **Encryption**: Protected copyright and sensitive data

## Technologies Used

### Backend
- **Framework**: Flask (Python 3.11+)
- **Database**: PostgreSQL (production) / SQLite (development)
- **ORM**: SQLAlchemy with Flask-SQLAlchemy
- **Authentication**: Flask-Login
- **PDF**: ReportLab for document generation

### Frontend
- **CSS Framework**: Tailwind CSS
- **Icons**: Font Awesome 6.0.0
- **Tables**: DataTables 1.13.6
- **JavaScript**: Vanilla JS with jQuery

### Design
- **Theme**: DRC National Colors
  - DRC Blue: #003087
  - Yellow: #FFD700
  - Red: #CE1126
  - Green: #009639

## Quick Installation

### Prerequisites
- Python 3.11+
- PostgreSQL 12+ (recommended for production)
- Git

### Installation Steps

1. **Clone the project**
```bash
git clone <repository-url>
cd gec-mines
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
export DATABASE_URL="postgresql://user:password@localhost/gec_mines"
export SESSION_SECRET="your-secret-key-here"
```

4. **Initialize database**
```bash
python init_database.py
```

5. **Launch application**
```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

6. **Access application**
- URL: http://localhost:5000
- Default login: `admin` / `admin123`

## Detailed Installation Guides

- [cPanel Installation](./INSTALL_CPANEL_EN.md) - Complete guide for shared hosting
- [VPS Installation](./INSTALL_VPS_EN.md) - Guide for virtual private server
- [Database Configuration](./DATABASE_SETUP_EN.md) - SQL scripts and procedures

## Technical Documentation

- [Complete Documentation](./DOCUMENTATION_EN.md) - Detailed technical specifications
- [Development Guide](./DEVELOPMENT_GUIDE_EN.md) - For developers
- [API and Integrations](./API_REFERENCE_EN.md) - API documentation

## Support and Maintenance

### Automatic Backup
The system includes a complete backup/restore system accessible to Super Admins:
- Complete backup: database + files + configuration
- ZIP format with metadata
- Restoration with automatic security backup

### Logging
- User activity logs
- System logs for debugging
- Complete action traceability

### Maintenance
- Automatic temporary file cleanup
- Database optimization
- Performance monitoring

## System Configuration

### Customizable Parameters
- Software name and logo
- Receipt number format
- Organization information
- PDF configuration (title, subtitle, logo)
- Footer text

### Departments and Roles
- Custom department creation
- Department head assignment
- Role-based permission management
- Configurable approval workflows

## Security

### Implemented Best Practices
- Secure password hashing
- CSRF protection
- File upload validation
- Granular access control
- Complete audit logs

### Deployment Recommendations
- Use HTTPS in production
- Configure reverse proxy (nginx)
- Automated regular backups
- Error log monitoring

## Contributing

This project is developed for the General Secretariat of Mines of the DRC. For modifications or improvements, contact the development team.

## License

© 2025 GEC. Made with 💖 and ☕ By MOA-Digital Agency LLC

---

**Version**: 2.1.0  
**Last Updated**: July 2025  
**Compatibility**: Python 3.11+, PostgreSQL 12+, Modern Browsers