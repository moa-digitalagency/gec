"""
Script pour corriger les colonnes manquantes dans parametres_systeme
Exécutez ce script pour ajouter les colonnes SMTP manquantes
"""

import sqlite3
import sys

def fix_parametres_systeme_columns():
    """Ajoute les colonnes manquantes à la table parametres_systeme"""
    
    db_path = 'gec_mines.db'
    
    migrations = [
        ("smtp_server", "ALTER TABLE parametres_systeme ADD COLUMN smtp_server VARCHAR(200)"),
        ("smtp_port", "ALTER TABLE parametres_systeme ADD COLUMN smtp_port INTEGER DEFAULT 587"),
        ("smtp_use_tls", "ALTER TABLE parametres_systeme ADD COLUMN smtp_use_tls BOOLEAN DEFAULT 1"),
        ("smtp_username", "ALTER TABLE parametres_systeme ADD COLUMN smtp_username VARCHAR(200)"),
        ("smtp_password", "ALTER TABLE parametres_systeme ADD COLUMN smtp_password VARCHAR(500)"),
        ("appellation_departement", "ALTER TABLE parametres_systeme ADD COLUMN appellation_departement VARCHAR(100) DEFAULT 'Départements'"),
    ]
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Vérification et ajout des colonnes manquantes...\n")
        
        for column_name, sql in migrations:
            try:
                cursor.execute(sql)
                print(f"✅ Colonne '{column_name}' ajoutée avec succès")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"ℹ️  Colonne '{column_name}' existe déjà")
                else:
                    print(f"❌ Erreur pour '{column_name}': {e}")
        
        conn.commit()
        print("\n✅ Migration terminée avec succès !")
        print("🚀 Vous pouvez maintenant redémarrer l'application")
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_parametres_systeme_columns()
