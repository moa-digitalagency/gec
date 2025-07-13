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

### Multi-language System Implementation (In Progress)
✓ Created JSON-based translation files (French default, English supplement)
✓ Added language support functions in utils.py
✓ Implemented language switching functionality
✓ Added role and language columns to user table
→ Working on user management with role-based permissions
→ Implementing responsive mobile navigation with language selector