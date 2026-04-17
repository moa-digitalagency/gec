[ 🇫🇷 Français ](GEC_features_full_list.md) | [ 🇬🇧 English ](GEC_features_full_list_en.md)

# GEC - Full Features List (The Bible)

> **CONFIDENTIAL AND PROPRIETARY.**
> This document details every feature of the GEC (Electronic Mail Management) system.
> Property of MOA Digital Agency. Reproduction prohibited.

---

## 1. Security & Authentication (Module `Security`)

### 1.1 Authentication
*   **Secure Login:**
    *   Password hashing with **Bcrypt** (12 rounds) + Application Salt (`GEC_PASSWORD_SALT`).
    *   Brute-force protection (Temporary IP block after 5 failures).
    *   Login attempt tracking (`login_attempts`).
*   **Session Management:**
    *   Secure session tokens (`generate_secure_session_token`).
    *   Strict CSRF validation on all forms (`generate_csrf_token`).
    *   Automatic session expiration (Configurable timeout).

### 1.2 Access Control (RBAC)
*   **Hierarchical Role System:**
    *   **Super Admin:** Full access, system configuration, maintenance.
    *   **Admin:** User management, limited configuration, supervision.
    *   **User:** Registration, consultation, and processing within scope.
    *   **Custom Roles:** Creation of roles with specific color, icon, and description.
*   **Granular Permissions:**
    *   Atomic permission system (e.g., `manage_users`, `register_mail`, `view_trash`).
    *   Dynamic verification via `@check_permission` decorator.
*   **Visibility Logic (`MailAccessFilter`):**
    *   `read_all_mail`: Total visibility.
    *   `read_department_mail`: Visibility restricted to user's department + forwarded mails.
    *   `read_own_mail`: Visibility restricted to assigned/created mails + forwarded mails.

### 1.3 Cryptography & Data Protection
*   **Database Encryption (AES-256):**
    *   Uses `cryptography` library (Fernet).
    *   **Encrypted Fields (User):** Email, Full Name, ID Number, Job Title, Password Hash.
    *   **Encrypted Fields (Mail):** Subject, Sender, Recipient, Reference Number.
    *   **Encrypted Fields (System):** SMTP Passwords, API Keys.
*   **File Integrity:**
    *   SHA-256 Checksum calculation on upload to ensure integrity.
    *   On-demand verification via `verify_file_integrity`.

### 1.4 Application Security
*   **Rate Limiting:** Protection of sensitive endpoints (Login, Upload) via `@rate_limit`.
*   **Sanitization:** Automatic input cleaning (`sanitize_input`) to prevent XSS and SQL Injection.
*   **Audit Logging:** Immutable traceability in `LogActivite` (Who, What, When, IP).
*   **Secure HTTP Headers:** HSTS, X-Frame-Options, CSP, X-XSS-Protection.

---

## 2. Mail Management (Module `Core`)

### 2.1 Registration
*   **Typology:** Strict distinction between `INCOMING` vs `OUTGOING`.
*   **Data Validation:**
    *   Consistency check (Sender/Recipient required based on type).
    *   Date format validation and mandatory fields.
*   **Receipt Number Generation:**
    *   Configurable format (e.g., `GEC-{year}-{counter:05d}`).
    *   Support for dynamic variables and atomic sequencer.
*   **Attachment Management:**
    *   Mandatory upload upon registration.
    *   Strict MIME type validation (PDF, Images) and size limit (Max 16MB).
    *   Secure filename renaming to avoid collisions and malicious executions.

### 2.2 Lifecycle & Statuses
*   **Status Workflow:**
    *   Standard states: `RECEIVED`, `IN_PROGRESS`, `PROCESSED`, `ARCHIVED`, `URGENT`.
    *   Status transition logged and notified.
*   **Trash Management (Soft Delete):**
    *   Logical deletion with restoration capability.
    *   Permanent purge reserved for administrators.

### 2.3 Advanced Search
*   **Search Engine:**
    *   Indexing on: Receipt No, Reference, Subject, Third Party.
    *   Case-insensitive and accent-insensitive search.
*   **Multi-criteria Filtering:**
    *   By Period (Registration / Drafting).
    *   By Status / Type / Priority.
    *   By Department / User.
    *   By SG Copy presence.

---

## 3. Collaboration & Workflow

### 3.1 Forwarding
*   **Transmission Mechanism:**
    *   Transfer of responsibility or request for opinion between users.
    *   Addition of contextual message and additional attachments.
*   **Rights Inheritance:** The recipient automatically inherits read rights on the forwarded mail.
*   **History:** Visible transmission chain (Timeline).

### 3.2 Annotations & Comments
*   **Annotation System:**
    *   Adding notes (Instructions, Remarks) to the file.
    *   Timestamping and author identification.
*   **Notifications:** Automatic alerts to concerned parties upon addition.

### 3.3 Multi-channel Notifications
*   **In-App:** Real-time notification center (Badge, Dropdown).
*   **Email:** Asynchronous notifications via SMTP or Resend (Responsive HTML Template).

---

## 4. System Administration

### 4.1 Global Configuration
*   **Visual Identity:** Customization of logos, names, slogans.
*   **PDF Parameters:** Headers and footers for official exports.
*   **Email Configuration:** Provider manager (SMTP/API) with connection test.

### 4.2 Organizational Management
*   **User Management:** Full CRUD, Password Reset, Avatar.
*   **Department Management:** Hierarchical structure of the organization.
*   **Mail Types:** Configuration of document types (Letter, Memo, Decree...).

### 4.3 Internationalisation (i18n)
*   **Language Engine:**
    *   Multi-file JSON support (`fr.json`, `en.json`).
    *   Smart language detection (Session > Browser).
*   **Translation Editor:** GUI to modify labels without touching code.

---

## 5. Reporting & Business Intelligence

### 5.1 Dashboard
*   **Strategic KPIs:** Volumetrics, Processing rate, Load by department.
*   **Data Visualization:** Interactive charts (Bar, Pie, Line) via Chart.js.
*   **Caching System:** Caching of heavy statistics for optimal performance.

### 5.2 Exports & Reports
*   **PDF Engine (ReportLab):**
    *   **Mail Sheet:** Official summary document of a mail.
    *   **List Reports:** Filtered tabular export.
    *   **Audit Logs:** Security report for compliance.

---

## 6. Maintenance & Reliability

### 6.1 Backup & Restore
*   **Full-Stack Backup:**
    *   SQL Dump + Upload Files + Configuration + Env.
    *   ZIP Compression with JSON Manifest.
*   **Granular Restore:** Ability to restore all or part of the system.

### 6.2 Automated Maintenance
*   **Database Cleanup:** Scripts to purge old logs and temporary data.
*   **Schema Migration:** Automatic management of database evolution at startup.
