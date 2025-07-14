# Database Configuration - GEC Mines

## Overview

This guide details the PostgreSQL database configuration for the GEC Mines system, including creation scripts, data initialization, and maintenance procedures.

## Prerequisites

- PostgreSQL 12+ installed
- Administrative access to PostgreSQL
- psql client or graphical interface (pgAdmin)

## 1. Database Creation

### 1.1 Connect to PostgreSQL
```bash
# Connect as postgres user
sudo -u postgres psql

# Or with password
psql -U postgres -h localhost
```

### 1.2 Create user and database
```sql
-- Create dedicated user
CREATE USER gec_user WITH PASSWORD 'secure_password';

-- Create database
CREATE DATABASE gec_mines 
    WITH OWNER gec_user 
    ENCODING 'UTF8' 
    LC_COLLATE = 'en_US.UTF-8' 
    LC_CTYPE = 'en_US.UTF-8' 
    TEMPLATE template0;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE gec_mines TO gec_user;

-- Connect to new database
\c gec_mines

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO gec_user;
```

## 2. Table Structure

### 2.1 Complete Creation Script

Create an `init_database.sql` file:

```sql
-- =============================================================================
-- GEC MINES - DATABASE INITIALIZATION SCRIPT
-- Version: 2.1.0
-- Date: July 2025
-- =============================================================================

-- Departments table
CREATE TABLE departement (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    code VARCHAR(10) UNIQUE NOT NULL,
    chef_departement_id INTEGER,
    actif BOOLEAN DEFAULT TRUE,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Roles table
CREATE TABLE role (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(50) UNIQUE NOT NULL,
    nom_affichage VARCHAR(100) NOT NULL,
    description TEXT,
    couleur VARCHAR(50) DEFAULT 'bg-gray-100 text-gray-800',
    icone VARCHAR(50) DEFAULT 'fas fa-user',
    actif BOOLEAN DEFAULT TRUE,
    modifiable BOOLEAN DEFAULT TRUE,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cree_par_id INTEGER
);

-- Role permissions table
CREATE TABLE role_permission (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL,
    permission_nom VARCHAR(100) NOT NULL,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accorde_par_id INTEGER,
    FOREIGN KEY (role_id) REFERENCES role(id) ON DELETE CASCADE
);

-- Users table
CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    nom_complet VARCHAR(120) NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actif BOOLEAN DEFAULT TRUE,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    langue VARCHAR(5) NOT NULL DEFAULT 'fr',
    photo_profile VARCHAR(255),
    departement_id INTEGER,
    matricule VARCHAR(50),
    fonction VARCHAR(200),
    FOREIGN KEY (departement_id) REFERENCES departement(id)
);

-- Mail status table
CREATE TABLE statut_courrier (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(200),
    couleur VARCHAR(50) DEFAULT 'bg-gray-100 text-gray-800',
    actif BOOLEAN DEFAULT TRUE,
    ordre INTEGER DEFAULT 0,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Mail table
CREATE TABLE courrier (
    id SERIAL PRIMARY KEY,
    numero_accuse_reception VARCHAR(50) UNIQUE NOT NULL,
    numero_reference VARCHAR(100),
    objet TEXT NOT NULL,
    type_courrier VARCHAR(20) NOT NULL DEFAULT 'ENTRANT',
    expediteur VARCHAR(200),
    destinataire VARCHAR(200),
    date_redaction DATE,
    date_enregistrement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fichier_nom VARCHAR(255),
    fichier_chemin VARCHAR(500),
    fichier_type VARCHAR(50),
    statut VARCHAR(50) NOT NULL DEFAULT 'RECU',
    date_modification_statut TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    utilisateur_id INTEGER NOT NULL,
    modifie_par_id INTEGER,
    FOREIGN KEY (utilisateur_id) REFERENCES "user"(id),
    FOREIGN KEY (modifie_par_id) REFERENCES "user"(id)
);

-- Activity logs table
CREATE TABLE log_activite (
    id SERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    description TEXT,
    date_action TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    utilisateur_id INTEGER NOT NULL,
    courrier_id INTEGER,
    FOREIGN KEY (utilisateur_id) REFERENCES "user"(id),
    FOREIGN KEY (courrier_id) REFERENCES courrier(id)
);

-- System parameters table
CREATE TABLE parametres_systeme (
    id SERIAL PRIMARY KEY,
    nom_logiciel VARCHAR(100) NOT NULL DEFAULT 'GEC - Mines RDC',
    logo_url VARCHAR(500),
    format_numero_accuse VARCHAR(50) DEFAULT 'GEC-{year}-{counter:05d}',
    adresse_organisme TEXT,
    telephone VARCHAR(20),
    email_contact VARCHAR(120),
    texte_footer TEXT DEFAULT 'Electronic Mail Management System',
    copyright_crypte VARCHAR(500) DEFAULT '',
    logo_pdf VARCHAR(500),
    titre_pdf VARCHAR(200) DEFAULT 'Ministry of Mines',
    sous_titre_pdf VARCHAR(200) DEFAULT 'General Secretariat',
    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modifie_par_id INTEGER,
    FOREIGN KEY (modifie_par_id) REFERENCES "user"(id)
);

-- Add foreign key constraint for departments
ALTER TABLE departement 
ADD CONSTRAINT fk_departement_chef 
FOREIGN KEY (chef_departement_id) REFERENCES "user"(id);

-- Indexes for performance improvement
CREATE INDEX idx_courrier_utilisateur ON courrier(utilisateur_id);
CREATE INDEX idx_courrier_date_enregistrement ON courrier(date_enregistrement);
CREATE INDEX idx_courrier_date_redaction ON courrier(date_redaction);
CREATE INDEX idx_courrier_type ON courrier(type_courrier);
CREATE INDEX idx_courrier_statut ON courrier(statut);
CREATE INDEX idx_log_activite_utilisateur ON log_activite(utilisateur_id);
CREATE INDEX idx_log_activite_date ON log_activite(date_action);
CREATE INDEX idx_user_departement ON "user"(departement_id);
```

### 2.2 Initialization Data

Create an `init_data.sql` file:

```sql
-- =============================================================================
-- INITIALIZATION DATA - GEC MINES
-- =============================================================================

-- Insert default departments
INSERT INTO departement (nom, description, code) VALUES
('Human Resources', 'Personnel and human resources management', 'HR'),
('Information Technology', 'IT services and technologies', 'IT'),
('Finance', 'Financial management and accounting', 'FIN'),
('General Administration', 'Administration and general coordination', 'ADM'),
('Mines and Geology', 'Mining and geological affairs', 'MIN');

-- Insert default roles
INSERT INTO role (nom, nom_affichage, description, couleur, icone, modifiable) VALUES
('super_admin', 'Super Administrator', 'Complete system access', 'bg-red-100 text-red-800', 'fas fa-crown', FALSE),
('admin', 'Administrator', 'Departmental administration', 'bg-blue-100 text-blue-800', 'fas fa-user-shield', FALSE),
('user', 'User', 'Standard user', 'bg-green-100 text-green-800', 'fas fa-user', FALSE);

-- Insert default permissions
INSERT INTO role_permission (role_id, permission_nom) VALUES
-- Super Admin - all permissions
(1, 'manage_users'),
(1, 'manage_system'),
(1, 'manage_statuses'),
(1, 'manage_departments'),
(1, 'manage_roles'),
(1, 'view_logs'),
(1, 'read_all_mail'),
(1, 'backup_system'),

-- Admin - departmental permissions
(2, 'manage_statuses'),
(2, 'read_department_mail'),

-- User - basic permissions
(3, 'read_own_mail');

-- Insert default mail statuses
INSERT INTO statut_courrier (nom, description, couleur, ordre) VALUES
('RECEIVED', 'Mail received and registered', 'bg-blue-100 text-blue-800', 1),
('IN_PROGRESS', 'Mail being processed', 'bg-yellow-100 text-yellow-800', 2),
('PROCESSED', 'Mail processed', 'bg-green-100 text-green-800', 3),
('URGENT', 'Urgent mail requiring immediate attention', 'bg-red-100 text-red-800', 4),
('ARCHIVED', 'Archived mail', 'bg-gray-100 text-gray-800', 5),
('PENDING', 'Pending validation', 'bg-orange-100 text-orange-800', 6);

-- Create default administrator user
INSERT INTO "user" (username, email, nom_complet, password_hash, role, actif, departement_id) VALUES
('admin', 'admin@gec-mines.cd', 'System Administrator', 
 'scrypt:32768:8:1$5K5K5K5K5K5K5K$5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K', 
 'super_admin', TRUE, 1);

-- Insert default system parameters
INSERT INTO parametres_systeme (
    nom_logiciel, 
    format_numero_accuse, 
    adresse_organisme, 
    telephone, 
    email_contact,
    titre_pdf,
    sous_titre_pdf,
    copyright_crypte
) VALUES (
    'GEC - Mines DRC',
    'GEC-{year}-{counter:05d}',
    'Ministry of Mines, Kinshasa, Democratic Republic of Congo',
    '+243 XX XXX XXXX',
    'contact@gec-mines.cd',
    'Ministry of Mines',
    'General Secretariat',
    'wqkgwqjlgwqjlgwqjlgwqjlgwqjlgwqjlgwqjlgwqjl=' -- Encrypted copyright
);
```

## 3. Python Initialization Script

Create an `init_database.py` file:

```python
#!/usr/bin/env python3
"""
GEC Mines database initialization script
Usage: python init_database.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash

def init_database():
    """Initialize database with tables and default data"""
    
    # Check for DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        print("Example: export DATABASE_URL='postgresql://user:password@localhost/gec_mines'")
        sys.exit(1)
    
    try:
        # Create connection
        engine = create_engine(database_url)
        
        print("🔗 Connecting to database...")
        
        # Read and execute table creation script
        with open('docs/init_database.sql', 'r', encoding='utf-8') as f:
            sql_commands = f.read()
        
        with engine.connect() as conn:
            # Execute SQL commands
            for command in sql_commands.split(';'):
                command = command.strip()
                if command:
                    conn.execute(text(command))
            conn.commit()
        
        print("✅ Tables created successfully")
        
        # Read and execute data initialization script
        with open('docs/init_data.sql', 'r', encoding='utf-8') as f:
            init_commands = f.read()
        
        with engine.connect() as conn:
            # Replace admin password hash
            admin_password_hash = generate_password_hash('admin123')
            init_commands = init_commands.replace(
                'scrypt:32768:8:1$5K5K5K5K5K5K5K$5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K',
                admin_password_hash
            )
            
            # Execute SQL commands
            for command in init_commands.split(';'):
                command = command.strip()
                if command:
                    conn.execute(text(command))
            conn.commit()
        
        print("✅ Initial data inserted successfully")
        print("\n🎉 Database initialized successfully!")
        print("\n📋 Default login information:")
        print("   Username: admin")
        print("   Password: admin123")
        print("\n⚠️  IMPORTANT: Change administrator password after first login")
        
    except Exception as e:
        print(f"❌ ERROR during initialization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database()
```

## 4. Database Maintenance

### 4.1 Backup
```bash
# Complete backup
pg_dump -U gec_user -h localhost gec_mines > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
pg_dump -U gec_user -h localhost gec_mines | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 4.2 Restore
```bash
# Restore from SQL file
psql -U gec_user -h localhost gec_mines < backup_file.sql

# Restore from compressed file
gunzip -c backup_file.sql.gz | psql -U gec_user -h localhost gec_mines
```

### 4.3 Optimization
```sql
-- Analyze tables for performance optimization
ANALYZE;

-- Reindex if necessary
REINDEX DATABASE gec_mines;

-- Clean obsolete data
VACUUM FULL;
```

## 5. Environment Variables

Create a `.env` file:

```bash
# Database configuration
DATABASE_URL=postgresql://gec_user:secure_password@localhost:5432/gec_mines

# Secret key for sessions
SESSION_SECRET=your_very_long_and_complex_secret_key

# Optional configuration
FLASK_ENV=production
FLASK_DEBUG=False
```

## 6. Installation Verification

Use this script to verify installation:

```python
#!/usr/bin/env python3
"""Installation verification script"""

import os
from sqlalchemy import create_engine, text

def verify_installation():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not configured")
        return False
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Check main tables
            tables = ['user', 'courrier', 'departement', 'role', 'parametres_systeme']
            for table in tables:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"✅ Table {table}: {count} record(s)")
        
        print("\n🎉 Installation verified successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

if __name__ == "__main__":
    verify_installation()
```

## 7. Troubleshooting

### Common Issues

1. **Connection Error**
   - Check that PostgreSQL is running
   - Verify connection parameters
   - Check user permissions

2. **Encoding Error**
   - Ensure database is in UTF-8
   - Check system locale

3. **Constraint Errors**
   - Check data insertion order
   - Verify foreign keys

### Useful Logs
```sql
-- View active connections
SELECT * FROM pg_stat_activity WHERE datname = 'gec_mines';

-- View database size
SELECT pg_size_pretty(pg_database_size('gec_mines'));
```

---

**Note**: Adapt passwords and connection parameters according to your production environment.