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
        print("❌ ERREUR: Variable d'environnement DATABASE_URL non définie")
        print("Exemple: export DATABASE_URL='postgresql://user:password@localhost/gec_mines'")
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
                'PLACEHOLDER_PASSWORD_HASH',
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
        
        # Vérification rapide
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM \"user\""))
            user_count = result.scalar()
            result = conn.execute(text("SELECT COUNT(*) FROM departement"))
            dept_count = result.scalar()
            print(f"\n📊 Données créées :")
            print(f"   - {user_count} utilisateur(s)")
            print(f"   - {dept_count} département(s)")
        
    except Exception as e:
        print(f"❌ ERREUR lors de l'initialisation : {e}")
        sys.exit(1)

def verify_installation():
    """Vérifie que l'installation s'est bien déroulée"""
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
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}" LIMIT 1'))
                count = result.scalar()
                print(f"✅ Table {table}: {count} enregistrement(s)")
        
        print("\n🎉 Installation vérifiée avec succès !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur de vérification: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialiser la base de données GEC Mines')
    parser.add_argument('--verify', action='store_true', help='Vérifier l\'installation existante')
    
    args = parser.parse_args()
    
    if args.verify:
        verify_installation()
    else:
        init_database()