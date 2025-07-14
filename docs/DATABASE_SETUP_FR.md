# Configuration de la Base de Données - GEC Mines

## Vue d'ensemble

Ce guide détaille la configuration de la base de données PostgreSQL pour le système GEC Mines, incluant les scripts de création, l'initialisation des données, et les procédures de maintenance.

## Prérequis

- PostgreSQL 12+ installé
- Accès administrateur à PostgreSQL
- Client psql ou interface graphique (pgAdmin)

## 1. Création de la Base de Données

### 1.1 Connexion à PostgreSQL
```bash
# Connexion en tant qu'utilisateur postgres
sudo -u postgres psql

# Ou avec mot de passe
psql -U postgres -h localhost
```

### 1.2 Création de l'utilisateur et de la base
```sql
-- Créer un utilisateur dédié
CREATE USER gec_user WITH PASSWORD 'motdepasse_securise';

-- Créer la base de données
CREATE DATABASE gec_mines 
    WITH OWNER gec_user 
    ENCODING 'UTF8' 
    LC_COLLATE = 'fr_FR.UTF-8' 
    LC_CTYPE = 'fr_FR.UTF-8' 
    TEMPLATE template0;

-- Accorder les privilèges
GRANT ALL PRIVILEGES ON DATABASE gec_mines TO gec_user;

-- Connecter à la nouvelle base
\c gec_mines

-- Accorder les privilèges sur le schéma
GRANT ALL ON SCHEMA public TO gec_user;
```

## 2. Structure des Tables

### 2.1 Script de Création Complet

Créez un fichier `init_database.sql` :

```sql
-- =============================================================================
-- GEC MINES - SCRIPT D'INITIALISATION DE LA BASE DE DONNÉES
-- Version: 2.1.0
-- Date: Juillet 2025
-- =============================================================================

-- Table des départements
CREATE TABLE departement (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    code VARCHAR(10) UNIQUE NOT NULL,
    chef_departement_id INTEGER,
    actif BOOLEAN DEFAULT TRUE,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des rôles
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

-- Table des permissions de rôles
CREATE TABLE role_permission (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL,
    permission_nom VARCHAR(100) NOT NULL,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accorde_par_id INTEGER,
    FOREIGN KEY (role_id) REFERENCES role(id) ON DELETE CASCADE
);

-- Table des utilisateurs
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

-- Table des statuts de courrier
CREATE TABLE statut_courrier (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(200),
    couleur VARCHAR(50) DEFAULT 'bg-gray-100 text-gray-800',
    actif BOOLEAN DEFAULT TRUE,
    ordre INTEGER DEFAULT 0,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des courriers
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

-- Table des logs d'activité
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

-- Table des paramètres système
CREATE TABLE parametres_systeme (
    id SERIAL PRIMARY KEY,
    nom_logiciel VARCHAR(100) NOT NULL DEFAULT 'GEC - Mines RDC',
    logo_url VARCHAR(500),
    format_numero_accuse VARCHAR(50) DEFAULT 'GEC-{year}-{counter:05d}',
    adresse_organisme TEXT,
    telephone VARCHAR(20),
    email_contact VARCHAR(120),
    texte_footer TEXT DEFAULT 'Système de Gestion Électronique du Courrier',
    copyright_crypte VARCHAR(500) DEFAULT '',
    logo_pdf VARCHAR(500),
    titre_pdf VARCHAR(200) DEFAULT 'Ministère des Mines',
    sous_titre_pdf VARCHAR(200) DEFAULT 'Secrétariat Général',
    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modifie_par_id INTEGER,
    FOREIGN KEY (modifie_par_id) REFERENCES "user"(id)
);

-- Ajout des contraintes de clé étrangère pour les départements
ALTER TABLE departement 
ADD CONSTRAINT fk_departement_chef 
FOREIGN KEY (chef_departement_id) REFERENCES "user"(id);

-- Index pour améliorer les performances
CREATE INDEX idx_courrier_utilisateur ON courrier(utilisateur_id);
CREATE INDEX idx_courrier_date_enregistrement ON courrier(date_enregistrement);
CREATE INDEX idx_courrier_date_redaction ON courrier(date_redaction);
CREATE INDEX idx_courrier_type ON courrier(type_courrier);
CREATE INDEX idx_courrier_statut ON courrier(statut);
CREATE INDEX idx_log_activite_utilisateur ON log_activite(utilisateur_id);
CREATE INDEX idx_log_activite_date ON log_activite(date_action);
CREATE INDEX idx_user_departement ON "user"(departement_id);
```

### 2.2 Données d'Initialisation

Créez un fichier `init_data.sql` :

```sql
-- =============================================================================
-- DONNÉES D'INITIALISATION - GEC MINES
-- =============================================================================

-- Insertion des départements par défaut
INSERT INTO departement (nom, description, code) VALUES
('Ressources Humaines', 'Gestion du personnel et des ressources humaines', 'RH'),
('Informatique', 'Services informatiques et technologies', 'IT'),
('Finance', 'Gestion financière et comptabilité', 'FIN'),
('Administration Générale', 'Administration et coordination générale', 'ADM'),
('Mines et Géologie', 'Affaires minières et géologiques', 'MIN');

-- Insertion des rôles par défaut
INSERT INTO role (nom, nom_affichage, description, couleur, icone, modifiable) VALUES
('super_admin', 'Super Administrateur', 'Accès complet au système', 'bg-red-100 text-red-800', 'fas fa-crown', FALSE),
('admin', 'Administrateur', 'Administration départementale', 'bg-blue-100 text-blue-800', 'fas fa-user-shield', FALSE),
('user', 'Utilisateur', 'Utilisateur standard', 'bg-green-100 text-green-800', 'fas fa-user', FALSE);

-- Insertion des permissions par défaut
INSERT INTO role_permission (role_id, permission_nom) VALUES
-- Super Admin - toutes les permissions
(1, 'manage_users'),
(1, 'manage_system'),
(1, 'manage_statuses'),
(1, 'manage_departments'),
(1, 'manage_roles'),
(1, 'view_logs'),
(1, 'read_all_mail'),
(1, 'backup_system'),

-- Admin - permissions départementales
(2, 'manage_statuses'),
(2, 'read_department_mail'),

-- User - permissions de base
(3, 'read_own_mail');

-- Insertion des statuts de courrier par défaut
INSERT INTO statut_courrier (nom, description, couleur, ordre) VALUES
('RECU', 'Courrier reçu et enregistré', 'bg-blue-100 text-blue-800', 1),
('EN_COURS', 'Courrier en cours de traitement', 'bg-yellow-100 text-yellow-800', 2),
('TRAITE', 'Courrier traité', 'bg-green-100 text-green-800', 3),
('URGENT', 'Courrier urgent nécessitant une attention immédiate', 'bg-red-100 text-red-800', 4),
('ARCHIVE', 'Courrier archivé', 'bg-gray-100 text-gray-800', 5),
('EN_ATTENTE', 'En attente de validation', 'bg-orange-100 text-orange-800', 6);

-- Création de l'utilisateur administrateur par défaut
INSERT INTO "user" (username, email, nom_complet, password_hash, role, actif, departement_id) VALUES
('admin', 'admin@gec-mines.cd', 'Administrateur Système', 
 'scrypt:32768:8:1$5K5K5K5K5K5K5K$5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K', 
 'super_admin', TRUE, 1);

-- Insertion des paramètres système par défaut
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
    'GEC - Mines RDC',
    'GEC-{year}-{counter:05d}',
    'Ministère des Mines, Kinshasa, République Démocratique du Congo',
    '+243 XX XXX XXXX',
    'contact@gec-mines.cd',
    'Ministère des Mines',
    'Secrétariat Général',
    'wqkgwqjlgwqjlgwqjlgwqjlgwqjlgwqjlgwqjlgwqjl=' -- Copyright crypté
);
```

## 3. Script d'Initialisation Python

Créez un fichier `init_database.py` :

```python
#!/usr/bin/env python3
"""
Script d'initialisation de la base de données GEC Mines
Usage: python init_database.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash

def init_database():
    """Initialise la base de données avec les tables et données par défaut"""
    
    # Vérifier la présence de DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        print("Example: export DATABASE_URL='postgresql://user:password@localhost/gec_mines'")
        sys.exit(1)
    
    try:
        # Créer la connexion
        engine = create_engine(database_url)
        
        print("🔗 Connexion à la base de données...")
        
        # Lire et exécuter le script de création des tables
        with open('docs/init_database.sql', 'r', encoding='utf-8') as f:
            sql_commands = f.read()
        
        with engine.connect() as conn:
            # Exécuter les commandes SQL
            for command in sql_commands.split(';'):
                command = command.strip()
                if command:
                    conn.execute(text(command))
            conn.commit()
        
        print("✅ Tables créées avec succès")
        
        # Lire et exécuter le script d'initialisation des données
        with open('docs/init_data.sql', 'r', encoding='utf-8') as f:
            init_commands = f.read()
        
        with engine.connect() as conn:
            # Remplacer le hash du mot de passe admin
            admin_password_hash = generate_password_hash('admin123')
            init_commands = init_commands.replace(
                'scrypt:32768:8:1$5K5K5K5K5K5K5K$5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K5K',
                admin_password_hash
            )
            
            # Exécuter les commandes SQL
            for command in init_commands.split(';'):
                command = command.strip()
                if command:
                    conn.execute(text(command))
            conn.commit()
        
        print("✅ Données initiales insérées avec succès")
        print("\n🎉 Base de données initialisée avec succès !")
        print("\n📋 Informations de connexion par défaut :")
        print("   Username: admin")
        print("   Password: admin123")
        print("\n⚠️  IMPORTANT: Changez le mot de passe administrateur après la première connexion")
        
    except Exception as e:
        print(f"❌ ERREUR lors de l'initialisation : {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database()
```

## 4. Maintenance de la Base de Données

### 4.1 Sauvegarde
```bash
# Sauvegarde complète
pg_dump -U gec_user -h localhost gec_mines > backup_$(date +%Y%m%d_%H%M%S).sql

# Sauvegarde avec compression
pg_dump -U gec_user -h localhost gec_mines | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 4.2 Restauration
```bash
# Restauration depuis un fichier SQL
psql -U gec_user -h localhost gec_mines < backup_file.sql

# Restauration depuis un fichier compressé
gunzip -c backup_file.sql.gz | psql -U gec_user -h localhost gec_mines
```

### 4.3 Optimisation
```sql
-- Analyse des tables pour optimiser les performances
ANALYZE;

-- Réindexation si nécessaire
REINDEX DATABASE gec_mines;

-- Nettoyage des données obsolètes
VACUUM FULL;
```

## 5. Variables d'Environnement

Créez un fichier `.env` :

```bash
# Configuration de la base de données
DATABASE_URL=postgresql://gec_user:motdepasse_securise@localhost:5432/gec_mines

# Clé secrète pour les sessions
SESSION_SECRET=votre_cle_secrete_tres_longue_et_complexe

# Configuration optionnelle
FLASK_ENV=production
FLASK_DEBUG=False
```

## 6. Vérification de l'Installation

Utilisez ce script pour vérifier l'installation :

```python
#!/usr/bin/env python3
"""Script de vérification de l'installation"""

import os
from sqlalchemy import create_engine, text

def verify_installation():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL non configuré")
        return False
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Vérifier les tables principales
            tables = ['user', 'courrier', 'departement', 'role', 'parametres_systeme']
            for table in tables:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"✅ Table {table}: {count} enregistrement(s)")
        
        print("\n🎉 Installation vérifiée avec succès !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur de vérification: {e}")
        return False

if __name__ == "__main__":
    verify_installation()
```

## 7. Dépannage

### Problèmes courants

1. **Erreur de connexion**
   - Vérifiez que PostgreSQL est démarré
   - Vérifiez les paramètres de connexion
   - Vérifiez les permissions utilisateur

2. **Erreur d'encodage**
   - Assurez-vous que la base est en UTF-8
   - Vérifiez la locale du système

3. **Erreurs de contraintes**
   - Vérifiez l'ordre d'insertion des données
   - Vérifiez les clés étrangères

### Logs utiles
```sql
-- Voir les connexions actives
SELECT * FROM pg_stat_activity WHERE datname = 'gec_mines';

-- Voir la taille de la base
SELECT pg_size_pretty(pg_database_size('gec_mines'));
```

---

**Note** : Adaptez les mots de passe et paramètres de connexion selon votre environnement de production.