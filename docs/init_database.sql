-- =============================================================================
-- GEC MINES - SCRIPT D'INITIALISATION DE LA BASE DE DONNÉES
-- Version: 2.1.0
-- Date: Juillet 2025
-- =============================================================================

-- Table des départements
CREATE TABLE IF NOT EXISTS departement (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    code VARCHAR(10) UNIQUE NOT NULL,
    chef_departement_id INTEGER,
    actif BOOLEAN DEFAULT TRUE,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des rôles
CREATE TABLE IF NOT EXISTS role (
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
CREATE TABLE IF NOT EXISTS role_permission (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL,
    permission_nom VARCHAR(100) NOT NULL,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accorde_par_id INTEGER,
    FOREIGN KEY (role_id) REFERENCES role(id) ON DELETE CASCADE
);

-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS "user" (
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
CREATE TABLE IF NOT EXISTS statut_courrier (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(200),
    couleur VARCHAR(50) DEFAULT 'bg-gray-100 text-gray-800',
    actif BOOLEAN DEFAULT TRUE,
    ordre INTEGER DEFAULT 0,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des courriers
CREATE TABLE IF NOT EXISTS courrier (
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
CREATE TABLE IF NOT EXISTS log_activite (
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
CREATE TABLE IF NOT EXISTS parametres_systeme (
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

-- Ajout des contraintes de clé étrangère pour les départements (si pas déjà ajoutées)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_departement_chef'
    ) THEN
        ALTER TABLE departement 
        ADD CONSTRAINT fk_departement_chef 
        FOREIGN KEY (chef_departement_id) REFERENCES "user"(id);
    END IF;
END $$;

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_courrier_utilisateur ON courrier(utilisateur_id);
CREATE INDEX IF NOT EXISTS idx_courrier_date_enregistrement ON courrier(date_enregistrement);
CREATE INDEX IF NOT EXISTS idx_courrier_date_redaction ON courrier(date_redaction);
CREATE INDEX IF NOT EXISTS idx_courrier_type ON courrier(type_courrier);
CREATE INDEX IF NOT EXISTS idx_courrier_statut ON courrier(statut);
CREATE INDEX IF NOT EXISTS idx_log_activite_utilisateur ON log_activite(utilisateur_id);
CREATE INDEX IF NOT EXISTS idx_log_activite_date ON log_activite(date_action);
CREATE INDEX IF NOT EXISTS idx_user_departement ON "user"(departement_id);