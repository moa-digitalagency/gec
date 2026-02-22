[ 🇫🇷 Français ](GEC_technical_architecture.md) | [ 🇬🇧 English ](GEC_technical_architecture_en.md)

# GEC - Technical Architecture

> **INTERNAL TECHNICAL DOCUMENT.**
> This document describes the software architecture, technical stack, and data flows.
> Property of MOA Digital Agency.

## 1. Overview

The architecture is based on a modular monolithic model using **Flask (Python)** as the backend and **Jinja2 + Tailwind** for the frontend. Persistence is ensured by **PostgreSQL**.

### Architecture Diagram

```mermaid
graph TD
    User[User (Browser)] -->|HTTPS / JSON| LB[Reverse Proxy (Nginx/Apache)]
    LB -->|WSGI| Gunicorn[Gunicorn Server]

    subgraph "Flask Application (GEC)"
        Auth[Security Layer<br/>(CSRF, Auth, RateLimit)]

        subgraph "Modules"
            Core[Core Module<br/>(Mails, Workflow)]
            Admin[Admin Module<br/>(Users, Depts)]
            Stats[Reporting Module<br/>(Charts, Exports)]
        end

        ORM[SQLAlchemy ORM]
    end

    subgraph "Storage"
        DB[(PostgreSQL<br/>Encrypted Data)]
        FS[File System<br/>(Secure Uploads)]
    end

    Gunicorn --> Auth
    Auth --> Core & Admin & Stats
    Core & Admin & Stats --> ORM
    ORM --> DB
    Core --> FS
```

## 2. Tech Stack

### Backend
*   **Language:** Python 3.11+
*   **Framework:** Flask 3.x
*   **ORM:** SQLAlchemy 2.x
*   **Security:** Cryptography (Fernet), Bcrypt, Werkzeug
*   **Key Dependencies:**
    *   `flask-login`: Session management.
    *   `flask-migrate`: Database migrations.
    *   `reportlab`: PDF generation.
    *   `sendgrid-python`: Transactional email sending.

### Frontend
*   **Templating:** Jinja2 (Server-side rendering).
*   **CSS:** Tailwind CSS (Utility-first).
*   **JS:** Vanilla JS + jQuery (DOM Manipulation) + Chart.js (Analytics).
*   **Assets:** FontAwesome (Icons), Google Fonts (Inter).

### Database
*   **DBMS:** PostgreSQL 14+ (Production) / SQLite (Dev).
*   **Encryption:** Sensitive data encrypted at rest (AES-256).
*   **Connection:** Pool via SQLAlchemy Engine.

## 3. Security & Data Flow

### 3.1 Request Lifecycle
1.  **Input:** The request arrives via Gunicorn.
2.  **Middleware:**
    *   Security Headers check.
    *   CSRF Validation (if POST).
    *   Rate Limiting (if sensitive endpoint).
3.  **Routing:** Dispatch to the appropriate view (`views.py`).
4.  **Access Control:** `@login_required` and `@check_permission` decorators.
5.  **Processing:** Business logic, DB call via ORM.
6.  **Rendering:** Data injection into Jinja2 template or JSON return.

### 3.2 File Management
*   Uploaded files are NEVER served directly by the web server without validation.
*   Path: `uploads/{year}/{month}/`.
*   Naming: `secure_filename` + Unique Timestamp.

## 4. Standard Deployment
*   **OS:** Linux (Ubuntu/Debian) recommended.
*   **App Server:** Gunicorn (Sync workers or gevent).
*   **Process Manager:** Systemd.
*   **Reverse Proxy:** Nginx (SSL Management, Gzip Compression, Static Files).
