"""
Script pour créer les tables manquantes dans la base de données
Exécutez ce script pour créer parametres_systeme et autres tables manquantes
"""

import sqlite3
import sys

def create_missing_tables():
    """Crée les tables manquantes dans la base de données"""
    
    db_path = 'gec_mines.db'
    
    # SQL pour créer la table parametres_systeme complète
    create_parametres_systeme = """
    CREATE TABLE IF NOT EXISTS parametres_systeme (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_logiciel VARCHAR(100) NOT NULL DEFAULT 'GEC - Gestion du Courrier',
        logo_url VARCHAR(500),
        mode_numero_accuse VARCHAR(20) NOT NULL DEFAULT 'automatique',
        format_numero_accuse VARCHAR(50) NOT NULL DEFAULT 'GEC-{year}-{counter:05d}',
        adresse_organisme TEXT,
        telephone VARCHAR(20),
        email_contact VARCHAR(120),
        texte_footer TEXT DEFAULT 'Système de Gestion Électronique du Courrier',
        copyright_crypte VARCHAR(500) NOT NULL DEFAULT '',
        logo_pdf VARCHAR(500),
        titre_pdf VARCHAR(200) DEFAULT 'Secrétariat Général',
        sous_titre_pdf VARCHAR(200) DEFAULT 'Secrétariat Général',
        pays_pdf VARCHAR(200) DEFAULT 'République Démocratique du Congo',
        copyright_text TEXT DEFAULT '© 2025 GEC. Made with love and coffee by MOA-Digital Agency LLC',
        smtp_server VARCHAR(200),
        smtp_port INTEGER DEFAULT 587,
        smtp_use_tls BOOLEAN NOT NULL DEFAULT 1,
        smtp_username VARCHAR(200),
        smtp_password VARCHAR(500),
        appellation_departement VARCHAR(100) NOT NULL DEFAULT 'Départements',
        titre_responsable_structure VARCHAR(100) NOT NULL DEFAULT 'Secrétaire Général',
        email_provider VARCHAR(20) NOT NULL DEFAULT 'sendgrid',
        sendgrid_api_key VARCHAR(500),
        notify_superadmin_new_mail BOOLEAN NOT NULL DEFAULT 1,
        date_modification DATETIME DEFAULT CURRENT_TIMESTAMP,
        modifie_par_id INTEGER,
        FOREIGN KEY (modifie_par_id) REFERENCES user(id)
    );
    """
    
    # Autres tables qui pourraient manquer
    create_migration_log = """
    CREATE TABLE IF NOT EXISTS migration_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        migration_name VARCHAR(200) NOT NULL,
        status VARCHAR(20) NOT NULL,
        message TEXT,
        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_system_health = """
    CREATE TABLE IF NOT EXISTS system_health (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        check_type VARCHAR(50) NOT NULL,
        status VARCHAR(20) NOT NULL,
        message TEXT,
        details TEXT,
        checked_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Création des tables manquantes...\n")
        
        # Créer les tables
        tables = [
            ("parametres_systeme", create_parametres_systeme),
            ("migration_log", create_migration_log),
            ("system_health", create_system_health),
        ]
        
        for table_name, sql in tables:
            try:
                cursor.execute(sql)
                print(f"✅ Table '{table_name}' créée avec succès")
            except sqlite3.OperationalError as e:
                if "already exists" in str(e).lower():
                    print(f"ℹ️  Table '{table_name}' existe déjà")
                else:
                    print(f"❌ Erreur pour '{table_name}': {e}")
        
        conn.commit()
        print("\n✅ Création des tables terminée avec succès !")
        print("🚀 Vous pouvez maintenant redémarrer l'application")
        
    except Exception as e:
        print(f"❌ Erreur lors de la création des tables: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_missing_tables()
