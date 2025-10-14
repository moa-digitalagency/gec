# Overview

GEC (Gestion Électronique du Courrier) is a comprehensive Flask web application for digital mail management, specifically designed for government administrations and enterprises in the Democratic Republic of Congo. The system handles incoming and outgoing mail correspondence with advanced security features, role-based access control, and multi-language support.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Framework
- **Flask** as the main web framework with SQLAlchemy ORM for database operations
- **Flask-Login** for user session management and authentication
- **Werkzeug** for WSGI utilities and security features
- **Gunicorn** for production WSGI server deployment

## Database Architecture
- **SQLAlchemy** with declarative base for ORM mapping
- **PostgreSQL** as the primary database (with SQLite fallback for development)
- Database models include: User, Courrier (mail), Departement, Role, RolePermission, LogActivite, and other supporting entities
- Migration utilities for safe schema updates without data loss

## Security Implementation
- **AES-256 encryption** for sensitive data using the cryptography library
- **Bcrypt password hashing** with custom salts
- **Rate limiting** and IP blocking for brute force protection
- **SQL injection and XSS protection** with input sanitization
- **File upload validation** with checksum verification
- **Comprehensive security logging** and audit trails

## User Management & Authorization
- **Three-tier role system**: Super Admin, Admin, User
- **Role-Based Access Control (RBAC)** with granular permissions
- **Department management** with hierarchical organization
- **User profiles** with encrypted sensitive information

## Mail Management System
- **Dual mail tracking**: incoming and outgoing correspondence
- **Automatic numbering** with receipt acknowledgments
- **Configurable status workflow**: Pending, In Progress, Processed, Archived
- **File attachment system** with mandatory attachments
- **Advanced search capabilities** with multiple filter options
- **Mail forwarding and tracking** between users

## Notification System
- **In-app notifications** with real-time updates
- **Email notifications** via SendGrid integration
- **Configurable email templates** in multiple languages
- **Smart targeting**: creator + last recipient notifications

## Multi-language Support
- **Dynamic language detection** from JSON files in `/lang` directory
- **Currently supported**: French (primary), English, Spanish, German
- **Extensible system** for additional languages
- **Template-based translations** with fallback mechanisms

## Document Management
- **PDF generation** using ReportLab for reports and receipts
- **File upload handling** with security validation
- **Document archiving** with encrypted storage
- **Export capabilities** for Excel and PDF formats

## Performance & Monitoring
- **Caching layer** for frequently accessed data
- **Performance monitoring** with execution time tracking
- **Database query optimization** with connection pooling
- **Activity logging** for all user actions

# External Dependencies

## Core Dependencies
- **Flask ecosystem**: Flask, Flask-SQLAlchemy, Flask-Login, Werkzeug
- **Database**: psycopg2-binary for PostgreSQL connectivity
- **Security**: cryptography, bcrypt, pycryptodome for encryption operations

## Document Processing
- **ReportLab**: PDF generation for official documents and reports
- **Pillow**: Image processing and manipulation
- **OpenCV**: Advanced image processing capabilities
- **xlsxwriter**: Excel file generation for data exports

## Communication Services
- **SendGrid**: Email delivery service for notifications
- **email-validator**: Email address validation

## Data Processing
- **pandas**: Data analysis and manipulation for reporting
- **requests**: HTTP client for external API integration
- **PyYAML**: Configuration file parsing

## Development & Deployment
- **gunicorn**: Production WSGI server
- **Local vendor libraries**: Tailwind CSS, Font Awesome, DataTables for frontend

## File Storage
- Local file system with `/uploads` directory for document storage
- Configurable upload limits (16MB default)
- Support for multiple file formats: PDF, images (PNG, JPG, JPEG, TIFF, SVG)

# Environment Configuration

## Environment Variables Documentation

The system requires several environment variables for proper operation. Complete bilingual documentation (English/French) is available in `README-ENV.md`.

### Critical Variables
- **DATABASE_URL**: PostgreSQL connection string (provided by Replit)
- **SESSION_SECRET**: Flask session secret (provided by Replit)
- **GEC_MASTER_KEY**: Master encryption key for sensitive data (Base64 encoded, must be generated and persisted)
- **GEC_PASSWORD_SALT**: Salt for password hashing (Base64 encoded, must be generated and persisted)

### Optional Variables
- **ADMIN_PASSWORD**: Default super admin password (default: TempPassword123!)
- **SMTP_SERVER**, **SMTP_PORT**, **SMTP_EMAIL**, **SMTP_PASSWORD**, **SMTP_USE_TLS**: Email configuration

### Configuration Files
- **README-ENV.md**: Complete bilingual documentation of all environment variables (French/English)
- **README-ENV-EN.md**: English-only version of environment variables documentation
- **.env.example**: Template file for environment configuration
- **generate_keys.py**: Utility script to generate secure encryption keys
- **show_env_keys.py**: Utility script to display all environment variables with masked sensitive values

### Environment Variable Loading
- **Automatic .env file loading**: The application can now read environment variables from a `.env` file in addition to system environment variables
- **Priority order**: System environment variables (Replit Secrets) take precedence over `.env` file values
- **Backward compatibility**: Automatically generates keys if not found in either source
- **Use case**: `.env` file is useful for local development or non-Replit deployments

### Security Notes
- `GEC_MASTER_KEY` and `GEC_PASSWORD_SALT` are critical and must be generated once and kept secure
- Without these keys, encrypted data will be lost on application restart
- Use `python generate_keys.py` to generate secure keys
- Use `python show_env_keys.py` to view current environment configuration (with masked sensitive values)
- Use `python show_env_keys.py --export` to export full values for backup
- Never commit `.env` file to version control (already in `.gitignore`)

# Maintenance Tools

## Database Cleanup Script

The system includes a comprehensive database cleanup utility (`cleanup_database.py`) for system maintenance and fresh deployments.

### Features
- **Selective data deletion**: Removes all operational data while preserving system configuration
- **Super admin preservation**: Keeps the super admin user (sa.gec001) intact
- **Transaction safety**: All operations wrapped in database transactions with automatic rollback on error
- **Confirmation prompt**: Requires explicit user confirmation ("OUI") before execution
- **Statistics reporting**: Shows before/after database statistics

### Data Removed
- All mail records (courrier)
- All comments and forwards
- All notifications and activity logs
- All IP blocks and security logs
- All user accounts except super admin
- Department leadership assignments

### Data Preserved
- Super admin user account
- Department definitions
- Role and permission configurations
- Mail status definitions
- Outgoing mail type definitions
- System parameters and settings
- Email templates
- Language translations

### Usage
```bash
python cleanup_database.py
```

The script will:
1. Display current database statistics
2. Request confirmation (type "OUI")
3. Execute cleanup operations
4. Display final statistics and summary

This tool is ideal for:
- Preparing demo environments
- Resetting test instances
- Initial production deployment setup
- System maintenance after migration