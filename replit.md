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