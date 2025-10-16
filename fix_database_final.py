"""
Script pour recréer la table parametres_systeme en utilisant le même DATABASE_URL que l'application
Ce script lit DATABASE_URL depuis les variables d'environnement pour garantir qu'il modifie la bonne base de données
"""

import os
import sys
import sqlite3
from urllib.parse import urlparse

def get_database_path():
    """Récupère le chemin de la base de données depuis DATABASE_URL"""
    # Charger .env si présent
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value.strip()
    
    # Récupérer DATABASE_URL
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///gec_mines.db')
    
    # Parser l'URL SQLite
    if database_url.startswith('sqlite:///'):
        db_path = database_url.replace('sqlite:///', '')
        return db_path
    elif database_url.startswith('sqlite://'):
        db_path = database_url.replace('sqlite://', '')
        return db_path
    else:
        print(f"❌ DATABASE_URL non SQLite: {database_url}")
        sys.exit(1)

def recreate_parametres_table():
    """Supprime et recrée la table parametres_systeme avec toutes les colonnes"""
    
    db_path = get_database_path()
    print(f"📂 Base de données cible: {db_path}")
    
    # Vérifier que le fichier existe
    if not os.path.exists(db_path):
        print(f"⚠️  Le fichier de base de données n'existe pas: {db_path}")
        print("ℹ️  Il sera créé automatiquement")
    
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
        
        print("\n⚠️  ATTENTION: Suppression de l'ancienne table parametres_systeme...")
        cursor.execute(drop_table)
        print("✅ Ancienne table supprimée")
        
        print("\n🔄 Création de la nouvelle table parametres_systeme avec toutes les colonnes...")
        cursor.execute(create_table)
        print("✅ Nouvelle table créée avec succès")
        
        # Vérifier que la colonne existe
        cursor.execute("PRAGMA table_info(parametres_systeme)")
        columns = cursor.fetchall()
        smtp_server_exists = any(col[1] == 'smtp_server' for col in columns)
        
        if smtp_server_exists:
            print("\n✅ Vérification: Colonne 'smtp_server' bien présente dans la table")
        else:
            print("\n❌ ERREUR: Colonne 'smtp_server' manquante après création!")
            sys.exit(1)
        
        conn.commit()
        print("\n✅ Migration terminée avec succès !")
        print("🚀 Vous pouvez maintenant redémarrer l'application")
        print("\nℹ️  NOTE: Les paramètres système seront réinitialisés à leurs valeurs par défaut")
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    recreate_parametres_table()
