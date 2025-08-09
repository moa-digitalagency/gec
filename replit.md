# GEC Mines - Mail Management System

## Overview
This Flask-based web application manages mail correspondence for GEC (Secrétariat Général des Mines). It provides a comprehensive digital solution for registering, viewing, searching, and tracking mail documents with attached files. The system aims to streamline mail management, improve efficiency, and ensure secure, auditable record-keeping for businesses and government agencies. Key capabilities include robust user authentication, detailed mail tracking, configurable system parameters, and advanced administration features like multi-tier access control, activity logging, and backup/restore functionality.

## User Preferences
Preferred communication style: Simple, everyday language.
Design preferences: Clean, corporate design using Democratic Republic of Congo colors (blue, yellow, red, green) with Tailwind CSS.
Dashboard design: User confirmed perfect and should not be changed ("le design est parfait, le tableau de board j'adore ne change sauf").

## System Architecture

### Backend
- **Framework**: Flask (Python)
- **ORM**: SQLAlchemy with Flask-SQLAlchemy
- **Authentication**: Flask-Login
- **Database**: SQLite (default), PostgreSQL (configurable)
- **File Storage**: Local filesystem
- **PDF Generation**: ReportLab with enhanced text wrapping
- **Security**: Advanced security suite including AES-256 data encryption, bcrypt password hashing with custom salts, brute force protection, IP blocking, SQL injection prevention, XSS protection, comprehensive audit logging, file integrity verification, secure file deletion, CSRF protection, security headers, and ProxyFix middleware.
- **Core Models**: `User`, `Courrier`, `LogActivite`, `ParametresSysteme`, `CourrierModification`.
- **Key Features**: Authentication, dashboard, mail registration/viewing/searching/editing, file handling, system settings, activity logging, backup/restore, advanced administration (user management, role-based permissions, mail access control), sender management, change tracking.

### Frontend
- **Template Engine**: Jinja2
- **CSS Framework**: Tailwind CSS
- **Icons**: Font Awesome 6.0.0
- **Tables**: DataTables 1.13.6
- **JavaScript**: Vanilla JS, jQuery (for DataTables)
- **Design System**: Democratic Republic of Congo colors (RDC blue: #003087, yellow: #FFD700, red: #CE1126, green: #009639).
- **UI/UX**: Responsive design, universal hamburger menu, customizable system parameters (logo, software name, receipt format, PDF settings), consistent design across pages, secure logo display with aspect ratio preservation.

### Core Architectural Decisions
- **Modularity**: Separation of concerns with dedicated modules for models, views, and utilities.
- **Configurability**: Extensive system parameters stored in `ParametresSysteme` for dynamic customization (e.g., software name, logos, receipt format, PDF headers).
- **Role-Based Access Control**: Three-tier system (Super Admin, Admin, User) with granular permissions for features and mail access (`read_all_mail`, `read_department_mail`, `read_own_mail`).
- **Internationalization**: JSON-based translation files with language switching for multi-language support.
- **Robustness**: Comprehensive error handling, strategic database indexing, caching mechanisms, performance monitoring, and encrypted data storage with automatic migration capabilities.
- **Security**: Proactive security measures including rate limiting, input sanitization, security logging, and enhanced file upload validation.

## External Dependencies

### Frontend Libraries (via CDN/local)
- Tailwind CSS
- Font Awesome 6.0.0
- DataTables 1.13.6
- jQuery

### Python Packages
- Flask
- Flask-SQLAlchemy
- Flask-Login
- Werkzeug
- ReportLab
- SQLAlchemy
- python-dotenv (for environment configuration)
- psycopg2-binary (for PostgreSQL support)
- Pillow (PIL, for image processing)
- cryptography (for advanced encryption)
- bcrypt (for secure password hashing)
- pycryptodome (for additional crypto operations)

### Security Features Added (August 2025)
- **Data Encryption**: AES-256-CBC encryption for all sensitive data (emails, names, file contents)
- **Password Security**: Enhanced bcrypt hashing with custom salts and strength validation
- **Brute Force Protection**: Automatic IP blocking after failed login attempts
- **Attack Prevention**: SQL injection detection, XSS filtering, CSRF protection
- **File Security**: Automatic file encryption, integrity verification with checksums
- **Audit Logging**: Comprehensive security event logging and monitoring
- **Session Security**: Secure session token management with expiration
- **Security Headers**: Complete set of HTTP security headers
- **Input Sanitization**: Advanced input validation and sanitization
- **Secure File Handling**: Path traversal protection and secure file operations

### License System Features (August 2025)
- **Cumulative License System**: Licenses can be stacked to extend validity periods (e.g., multiple 1-month licenses = longer access)
- **Activation-Based Timing**: License validity starts only when activated, not when created in database
- **5000 Generated Licenses**: 1000 each of 1 day, 5 days, 1 month, 6 months, and 12 months
- **Database-Driven Validation**: Real-time verification against PostgreSQL database with single-use enforcement
- **Advanced Security**: Obfuscated and encrypted license files with compression and distraction files
- **Domain-based License Validation**: Automatic detection of domain/subdomain changes requiring license reactivation
- **12-Character License Keys**: Simple alphanumeric format (e.g., ABC123XYZ789) for easy distribution
- **Admin Interface**: Complete license management dashboard with statistics and testing capabilities
- **Secure File Storage**: Hidden and encrypted license files (.gec_lic_sys, .gec_cumul_lic, .gec_dom_cache)
- **Anti-Cracking Measures**: Multiple layers of obfuscation, fake files, and compressed encrypted storage