# GEC Mines - Mail Management System

## Overview

This is a Flask-based web application for managing mail correspondence at GEC (Secrétariat Général des Mines). The system allows users to register, view, search, and manage mail documents with file attachments, providing a complete digital mail tracking solution.

## User Preferences

Preferred communication style: Simple, everyday language.
Design preferences: Clean, corporate design using Democratic Republic of Congo colors (blue, yellow, red, green) with Tailwind CSS.
Dashboard design: User confirmed perfect and should not be changed ("le design est parfait, le tableau de board j'adore ne change sauf").

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **ORM**: SQLAlchemy with Flask-SQLAlchemy integration
- **Authentication**: Flask-Login for session management
- **Database**: SQLite (default) with PostgreSQL support via environment configuration
- **File Storage**: Local filesystem with configurable upload directory
- **PDF Generation**: ReportLab for document export functionality

### Frontend Architecture
- **Template Engine**: Jinja2 (Flask's default)
- **CSS Framework**: Tailwind CSS (replaced Bootstrap for cleaner corporate design)
- **Icons**: Font Awesome 6.0.0
- **Tables**: DataTables 1.13.6 for enhanced table functionality
- **JavaScript**: Vanilla JS with jQuery for DataTables integration
- **Design System**: Democratic Republic of Congo colors (RDC blue: #003087, yellow: #FFD700, red: #CE1126, green: #009639)

### Security Features
- Password hashing using Werkzeug's security utilities
- Session-based authentication with Flask-Login
- File upload validation with allowed extensions
- CSRF protection through Flask's session management
- Proxy fix middleware for secure deployment

## Key Components

### Models (models.py)
- **User**: User authentication and profile management
- **Courrier**: Mail correspondence tracking with metadata
- **LogActivite**: Activity logging for audit trails
- **ParametresSysteme**: System configuration (logo, software name, receipt number format)

### Views (views.py)
- Authentication routes (login/logout)
- Dashboard with statistics
- Mail registration and viewing
- Search functionality
- File handling and exports
- Settings management with customizable parameters

### Utilities (utils.py)
- File validation and handling
- Unique ID generation for mail tracking
- Activity logging system
- PDF export functionality

## Data Flow

1. **User Authentication**: Users log in through Flask-Login system
2. **Mail Registration**: New mail entries are created with optional file attachments
3. **File Storage**: Uploaded files are stored in the `uploads/` directory
4. **Database Operations**: All data is persisted through SQLAlchemy ORM
5. **Activity Logging**: User actions are tracked in the LogActivite table
6. **Search & Export**: Users can search mail records and export to PDF

## External Dependencies

### Frontend Libraries (CDN)
- Tailwind CSS (utility-first CSS framework)
- Font Awesome 6.0.0 (icons)
- DataTables 1.13.6 (enhanced tables)
- jQuery (required for DataTables)

### Python Packages
- Flask and related extensions (SQLAlchemy, Login)
- Werkzeug for security and file handling
- ReportLab for PDF generation
- SQLAlchemy for database operations

## Deployment Strategy

### Environment Configuration
- Database URL configurable via `DATABASE_URL` environment variable
- Session secret configurable via `SESSION_SECRET` environment variable
- Defaults to SQLite for development, easily switchable to PostgreSQL

### File System Requirements
- `uploads/` directory for file storage (auto-created)
- `exports/` directory for PDF exports
- Static assets served from `static/` directory

### Production Considerations
- ProxyFix middleware configured for reverse proxy deployment
- Connection pooling configured for database efficiency
- File size limits set to 16MB
- Logging configured for debugging and monitoring

### Default Setup
- Default admin user creation on first run
- Automatic database table creation
- Development server runs on host 0.0.0.0:5000

The application is designed for easy deployment on cloud platforms with minimal configuration changes needed for production environments.

## Recent Changes (July 13, 2025)

✓ Complete design overhaul using Tailwind CSS with DRC national colors
✓ Optimized all pages (view_mail, search, mail_detail) with consistent design structure
✓ Added ParametresSysteme model for system configuration
✓ Implemented settings page for customizing:
  - Software name and logo
  - Receipt number format with variables
  - Organization contact information
✓ Enhanced receipt number generation with configurable format
✓ Updated navigation to include settings access
✓ Improved responsive design and accessibility
✓ Maintained backward compatibility with existing data

### Multi-language System Implementation (Completed)
✓ Created JSON-based translation files (French default, English supplement)
✓ Added language support functions in utils.py and utils/lang.py
✓ Implemented language switching functionality with user preferences
✓ Added role and language columns to user table with migrations
✓ Complete user management system with role-based permissions
✓ Responsive mobile navigation with enhanced language selector
✓ Role hierarchy: Super Admin → Admin → User with appropriate permissions
✓ Enhanced universal hamburger menu for all devices (desktop, tablet, mobile)
✓ Adaptive menu positioning: overlay on mobile, dropdown on desktop
✓ Structured sections with user info display and role indicators

### User Management Features (Completed)
✓ Three-tier role system (super_admin, admin, user)
✓ Permission-based access control throughout application
✓ User creation/editing/deletion for super administrators only
✓ Enhanced mobile navigation with role-based menu items
✓ Language preferences saved per user with session management
✓ User 1 configured as default super administrator (admin/admin123)

### Navigation System (July 13, 2025)
✓ Universal hamburger menu working across all devices
✓ Simplified JavaScript with inline styles for reliability
✓ Menu displays correctly with RDC blue background (#003087)
✓ Quick actions restored to horizontal layout in mail detail view
✓ Menu links functional with proper event handling
✓ Automatic menu closure on link clicks and outside clicks

### Advanced Administration Features (July 13, 2025)
✓ User dropdown menu with logout functionality in top navigation
✓ Activity logs page for super admin monitoring with comprehensive filtering
✓ Role management system with detailed permissions matrix
✓ Super admin only access to logs and role management
✓ Status selection capability added to mail registration form
✓ Complete permission-based access control throughout application

### Mail Access Permissions System (July 13, 2025)
✓ Three-tier mail access control system implemented:
  - read_all_mail: Complete access to all mail in the system (Super Admin)
  - read_department_mail: Access to department mail only (Admin)
  - read_own_mail: Access to personal registered mail only (User)
✓ Updated User.has_permission() method to use role-based permissions
✓ Enhanced mail filtering in view_mail route with new permission checks
✓ New permissions category "Accès Courrier" added to role management interface
✓ Permission system with fallback to legacy role-based access
✓ Complete integration with existing department-based access control

### System Configuration Enhancement (July 13, 2025)
✓ Added configurable footer text in system settings (excludes encrypted copyright)
✓ Implemented encrypted copyright storage with base64 encoding
✓ Added PDF export configuration parameters:
  - Configurable PDF logo (separate from main logo)
  - Configurable PDF title (default: "Ministère des Mines")
  - Configurable PDF subtitle (default: "Secrétariat Général")
✓ Updated settings page with new configuration sections
✓ Modified PDF export to use system-configured parameters
✓ Enhanced footer template to display configurable text + encrypted copyright
✓ Added context processor to inject system parameters in all templates
✓ Database migration completed for new configuration columns
✓ Copyright protection: "© 2025 GEC. Made with 💖 and ☕  By MOA-Digital Agency LLC" encrypted in database

### Complete Documentation Package (July 14, 2025)
✓ Created comprehensive README.md with project overview and user guide
✓ Created technical DOCUMENTATION.md with complete specifications and CDC
✓ Verified and updated language files (fr.json, en.json) with complete translations
✓ Documented all system features, architecture, and deployment procedures
✓ Added API routes documentation and security specifications
✓ Created technical architecture diagrams and data models documentation

### Backup/Restore System Implementation (July 14, 2025)
✓ Complete backup/restore functionality in system settings
✓ Full system archive creation: database + files + uploads + configuration
✓ PostgreSQL and SQLite backup support with automatic detection
✓ ZIP-based archive format with metadata and security measures
✓ Restoration with automatic safety backup before restore
✓ Super Admin restricted access with comprehensive interface
✓ Updated language files with backup/restore translations (fr.json, en.json)
✓ Enhanced settings.html template with backup management interface

### Installation Guides Creation (July 14, 2025)
✓ Created INSTALL_CPANEL_FR.md: Complete cPanel installation guide in French
✓ Created INSTALL_CPANEL_EN.md: Complete cPanel installation guide in English
✓ Created INSTALL_VPS_FR.md: Complete VPS installation guide in French
✓ Created INSTALL_VPS_EN.md: Complete VPS installation guide in English
✓ Updated README.md and DOCUMENTATION.md with backup features and installation references
✓ All guides include step-by-step instructions, troubleshooting, and security considerations

### Drafting Date Feature Integration (July 14, 2025)
✓ Added date_redaction field to Courrier model and PostgreSQL database
✓ Integrated drafting date field in mail registration form (optional)
✓ Updated mail list view with separate columns for drafting and registration dates
✓ Added drafting date filters (from/to) in search interface
✓ Enhanced mail detail view to display drafting date prominently
✓ Updated PDF exports (individual and list) to include drafting date
✓ Complete integration across registration, viewing, filtering, and export workflows
✓ System now tracks both letter drafting date and system registration date

### Documentation Reorganization and Database Setup (July 14, 2025)
✓ Created comprehensive docs/ folder with all documentation
✓ Created README_FR.md and README_EN.md with complete project overviews
✓ Created DATABASE_SETUP_FR.md and DATABASE_SETUP_EN.md with SQL scripts
✓ Created init_database.sql and init_data.sql for easy database setup
✓ Created init_database.py script for automated database initialization
✓ Updated installation guides for both cPanel and VPS in French and English
✓ Complete documentation package ready for deployment and maintenance

### System Parameters and PDF Enhancement (July 14, 2025 - Evening)
✓ Fixed critical system parameter bug: all template updates to use dynamic parameters
✓ Corrected hardcoded application names to use parametres.nom_logiciel dynamically
✓ Updated login pages, navigation, and all templates for parameter consistency
✓ Fixed PDF/page information synchronization for identical data display
✓ Added Date de Rédaction to mail detail page (was missing)
✓ Enhanced PDF export consistency: individual and list exports match page content exactly
✓ Added logo support in PDF exports using reportlab.platypus.Image
✓ Implemented logo_pdf priority over logo_url with fallback handling
✓ PDF logos properly centered and sized for both individual and list exports
✓ Complete system parameter integration: name, logos, contact info, PDF headers all dynamic

### Logo Display and PDF Enhancement (July 17, 2025)
✓ Fixed critical PDF logo rendering: URLs relative to absolute path conversion for ReportLab
✓ Added Flask upload route `/uploads/<filename>` for proper file serving and preview
✓ Implemented aspect ratio preservation in PDF logos using PIL calculations
✓ Logo deformation resolved: maintains original proportions in all PDF exports
✓ Template synchronization: mail detail pages and PDF exports show identical information
✓ Logo preview functionality restored in system parameters page
✓ Removed default admin credentials display from login page for security
✓ Complete logo system: upload → preview → PDF export workflow functional

### System Reset and Documentation Simplification (July 18, 2025)
✓ Complete database cleanup: all test data and logs removed for fresh start
✓ File system cleanup: uploads, exports, backups directories cleared
✓ Simplified PythonAnywhere deployment guides (FR/EN) for 30-minute setup
✓ Streamlined installation process from 11 steps to 9 simple steps
✓ Removed complex configurations and maintenance sections for clarity
✓ Focus on essential setup: account → files → dependencies → database → deploy
✓ Application ready for clean deployment with default admin credentials