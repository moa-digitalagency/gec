# GEC - Mail Management System

## Overview
This Flask-based web application manages mail correspondence for GEC (Secrétariat Général). It provides a comprehensive digital solution for registering, viewing, searching, and tracking mail documents with attached files. The system aims to streamline mail management, improve efficiency, and ensure secure, auditable record-keeping for businesses and government agencies. Key capabilities include robust user authentication, detailed mail tracking, configurable system parameters, and advanced administration features like multi-tier access control, activity logging, and backup/restore functionality.

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

### Security Features (August 2025)
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

### Recent Updates (August 30, 2025)
- **ENHANCED**: Email notification system now role-agnostic - uses permissions instead of fixed roles
- **IMPROVED**: All users with appropriate permissions can receive notifications using their profile email
- **EXTENDED**: System compatible with current and future custom roles
- **FLEXIBLE**: Notification eligibility based on permissions like 'receive_new_mail_notifications', 'manage_mail', 'read_all_mail'
- **MAINTAINED**: Backward compatibility with existing admin/super_admin roles
- **CRITICAL FIX**: Added automatic migration system to prevent "column does not exist" errors during updates
- **SENDGRID INTEGRATION**: Added SendGrid API key configuration directly in system parameters with encrypted storage
- **MIGRATION SYSTEM**: Created automatic column detection and addition system to preserve existing data during updates
- **STABILITY**: Future updates will no longer require reinstallation or cause data loss
- **PDF ENHANCEMENT**: Unified footer system with two-line layout displaying system info, generation details, and page numbers
- **DOCUMENTATION**: Added comprehensive domain configuration procedures for Replit deployments and local servers
- **DEPLOYMENT**: Complete custom domain setup instructions for production environments

### Status (August 18, 2025)
- Application ready for production deployment
- Database optimized with full indexing
- Security suite fully operational
- **COMPLETED**: Enhanced search with full metadata indexing (including autres_informations, statut, fichier_nom)
- **COMPLETED**: SG en copie filter added to search interface - only shows for ENTRANT mail type
- **COMPLETED**: Mandatory file attachments for all mail types
- **COMPLETED**: Outgoing mail enhancements (Date d'Émission mandatory, autres informations field)
- **COMPLETED**: Removed "Fichier" column from mail consultation view
- **FIXED**: All upload/export PDF links optimized for external deployment
- **CLEANED**: Removed all test and temporary files for production
- **DOCUMENTED**: Complete documentation in docs/ folder (4 files: Technical/Commercial in FR/EN)
- **ORGANIZED**: All documentation moved to docs/ folder with clean structure
- **ADDED**: Analytics Dashboard with real-time statistics, interactive charts (Chart.js), PDF/Excel export
- **ADDED**: Multi-language support (French/English) with JSON translation files
- **CREATED**: project-dependencies.txt file listing all Python dependencies
- **FIXED**: Date formatting now displays in French throughout the application (e.g., "18 août 2025")
- **UPDATED**: All templates now use format_date() function for consistent French date display
- **CLEANED**: Removed test files and old exports to optimize project structure
- **PERMISSIONS**: Added role-based permissions for system updates (manage_updates, manage_backup)
- **CLEANED 18/08**: Removed __pycache__, test PDFs from exports, and .DS_Store files
- **UNIFIED**: Single project-dependencies.txt file with all Python dependencies and exact versions
- **FIXED 18/08**: Removed duplicate "Numéro d'Accusé de Réception" field in manual mode
- **FIXED 18/08**: Corrected log_activity calls in update functions - added missing user_id parameter
- **ENHANCED 18/08**: Intelligent offline update system - compares file hashes, only replaces modified files, preserves user data