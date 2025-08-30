"""
Système de migration automatique pour GEC
Permet d'ajouter automatiquement les nouvelles colonnes sans perdre les données existantes
"""
import logging
import os
from sqlalchemy import text, inspect
from flask import current_app

def check_column_exists(engine, table_name, column_name):
    """Vérifie si une colonne existe dans une table"""
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logging.warning(f"Impossible de vérifier la colonne {column_name} dans {table_name}: {e}")
        return False

def add_column_safely(engine, table_name, column_name, column_definition):
    """Ajoute une colonne de manière sécurisée si elle n'existe pas"""
    try:
        if not check_column_exists(engine, table_name, column_name):
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
            logging.info(f"Ajout de la colonne {column_name} à la table {table_name}")
            with engine.connect() as connection:
                connection.execute(text(sql))
                connection.commit()
            return True
        else:
            logging.debug(f"Colonne {column_name} existe déjà dans {table_name}")
            return False
    except Exception as e:
        logging.error(f"Erreur lors de l'ajout de la colonne {column_name}: {e}")
        return False

def run_automatic_migrations(app, db):
    """
    Exécute toutes les migrations automatiques nécessaires
    Cette fonction est appelée au démarrage de l'application
    """
    logging.info("Vérification des migrations automatiques...")
    
    try:
        engine = db.engine
        migrations_applied = 0
        
        # Migration 1: Ajouter sendgrid_api_key à parametres_systeme
        if add_column_safely(engine, 'parametres_systeme', 'sendgrid_api_key', 'VARCHAR(500)'):
            migrations_applied += 1
            logging.info("✓ Migration: Colonne sendgrid_api_key ajoutée")
        
        # Migration 2: Futures colonnes pour paramètres système (désactivées pour l'instant)
        # Ces colonnes seront ajoutées quand les fonctionnalités correspondantes seront développées
        # future_parametres_columns = [
        #     ('notification_templates', 'TEXT'),  # Pour futurs templates de notification
        #     ('backup_settings', 'TEXT'),          # Pour paramètres de sauvegarde
        #     ('theme_settings', 'TEXT'),           # Pour paramètres de thème
        # ]
        # 
        # for column_name, column_type in future_parametres_columns:
        #     if add_column_safely(engine, 'parametres_systeme', column_name, column_type):
        #         migrations_applied += 1
        #         logging.info(f"✓ Migration: Colonne {column_name} ajoutée aux paramètres")
        
        # Migration 3: Futures colonnes pour utilisateurs (désactivées pour l'instant)
        # Note: 'user' est un mot réservé en PostgreSQL, utiliser des guillemets si nécessaire
        # future_user_columns = [
        #     ('avatar_url', 'VARCHAR(500)'),      # Pour avatars utilisateurs
        #     ('last_activity', 'TIMESTAMP'),      # Pour suivi d'activité
        #     ('preferences', 'TEXT'),             # Pour préférences utilisateur
        # ]
        # 
        # for column_name, column_type in future_user_columns:
        #     if add_column_safely(engine, '"user"', column_name, column_type):  # Guillemets pour PostgreSQL
        #         migrations_applied += 1
        #         logging.info(f"✓ Migration: Colonne {column_name} ajoutée aux utilisateurs")
        
        # Migration 3: Vérification des colonnes critiques
        critical_columns = [
            ('parametres_systeme', 'email_provider', 'VARCHAR(20) DEFAULT \'sendgrid\''),
            ('parametres_systeme', 'notify_superadmin_new_mail', 'BOOLEAN DEFAULT 1'),
        ]
        
        for table, column, definition in critical_columns:
            if add_column_safely(engine, table, column, definition):
                migrations_applied += 1
                logging.info(f"✓ Migration: Colonne critique {column} ajoutée à {table}")
        
        if migrations_applied > 0:
            logging.info(f"🔄 {migrations_applied} migration(s) automatique(s) appliquée(s) avec succès")
            # Commit les changements
            db.session.commit()
        else:
            logging.info("✅ Aucune migration nécessaire - Base de données à jour")
            
    except Exception as e:
        logging.error(f"❌ Erreur lors des migrations automatiques: {e}")
        # En cas d'erreur, on ne fait pas crasher l'application
        pass

def create_migration_table(engine):
    """Crée une table pour tracker les migrations appliquées (pour usage future)"""
    try:
        sql = """
        CREATE TABLE IF NOT EXISTS migration_log (
            id INTEGER PRIMARY KEY,
            migration_name VARCHAR(255) NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN DEFAULT 1
        )
        """
        with engine.connect() as connection:
            connection.execute(text(sql))
            connection.commit()
        logging.debug("Table migration_log créée/vérifiée")
    except Exception as e:
        logging.warning(f"Impossible de créer la table migration_log: {e}")

def log_migration(engine, migration_name, success=True):
    """Enregistre une migration dans le log (pour usage future)"""
    try:
        sql = """
        INSERT INTO migration_log (migration_name, success) 
        VALUES (:migration_name, :success)
        """
        with engine.connect() as connection:
            connection.execute(text(sql), {"migration_name": migration_name, "success": success})
            connection.commit()
        logging.debug(f"Migration {migration_name} enregistrée dans le log")
    except Exception as e:
        logging.warning(f"Impossible d'enregistrer la migration {migration_name}: {e}")

def get_database_type():
    """Détermine le type de base de données (SQLite ou PostgreSQL)"""
    database_url = os.environ.get("DATABASE_URL", "sqlite:///gec_mines.db")
    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        return "postgresql"
    else:
        return "sqlite"

def apply_database_specific_fixes(engine):
    """Applique des corrections spécifiques au type de base de données"""
    db_type = get_database_type()
    
    if db_type == "sqlite":
        # Pour SQLite, s'assurer que les contraintes de clés étrangères sont activées
        try:
            with engine.connect() as connection:
                connection.execute(text("PRAGMA foreign_keys = ON"))
            logging.debug("Contraintes de clés étrangères activées pour SQLite")
        except Exception as e:
            logging.warning(f"Impossible d'activer les contraintes FK pour SQLite: {e}")
    
    elif db_type == "postgresql":
        # Pour PostgreSQL, des optimisations spécifiques peuvent être ajoutées
        logging.debug("Base de données PostgreSQL détectée")