"""
Script pour recréer la table parametres_systeme avec la structure complète
ATTENTION: Ce script supprime l'ancienne table parametres_systeme
"""

import sqlite3
import sys

def recreate_parametres_table():
    """Supprime et recrée la table parametres_systeme avec toutes les colonnes"""
    
    db_path = 'gec_mines.db'
    
    # SQL pour supprimer l'ancienne table
    drop_table = "DROP TABLE IF EXISTS parametres_systeme;"
    
    # SQL pour créer la nouvelle table avec toutes les colonnes
    create_table = """
    CREATE TABLE parametres_systeme (
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
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("⚠️  ATTENTION: Suppression de l'ancienne table parametres_systeme...")
        cursor.execute(drop_table)
        print("✅ Ancienne table supprimée")
        
        print("\n🔄 Création de la nouvelle table parametres_systeme avec toutes les colonnes...")
        cursor.execute(create_table)
        print("✅ Nouvelle table créée avec succès")
        
        conn.commit()
        print("\n✅ Migration terminée avec succès !")
        print("🚀 Vous pouvez maintenant redémarrer l'application")
        print("\nℹ️  NOTE: Les paramètres système seront réinitialisés à leurs valeurs par défaut")
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    recreate_parametres_table()
