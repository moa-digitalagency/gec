"""
Système de migration automatique pour GEC
Permet d'ajouter automatiquement les nouvelles colonnes sans perdre les données existantes
"""
import logging
import os
from sqlalchemy import text, inspect
from flask import current_app

def get_database_type():
    """Détermine le type de base de données (SQLite ou PostgreSQL)"""
    database_url = os.environ.get("DATABASE_URL", "sqlite:///gec_mines.db")
    if database_url and (database_url.startswith("postgresql://") or database_url.startswith("postgres://")):
        return "postgresql"
    else:
        return "sqlite"

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
            # Normalisation des booléens pour PostgreSQL vs SQLite
            if "DEFAULT 1" in column_definition or "DEFAULT 0" in column_definition:
                 if get_database_type() == "postgresql":
                     column_definition = column_definition.replace("DEFAULT 1", "DEFAULT TRUE").replace("DEFAULT 0", "DEFAULT FALSE")

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

def check_table_exists(engine, table_name):
    """Vérifie si une table existe"""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        return table_name in tables
    except Exception as e:
        logging.warning(f"Impossible de vérifier la table {table_name}: {e}")
        return False

def create_table_safely(engine, table_name, create_sql):
    """Crée une table de manière sécurisée si elle n'existe pas"""
    try:
        if not check_table_exists(engine, table_name):
            logging.info(f"Création de la table {table_name}")
            with engine.connect() as connection:
                connection.execute(text(create_sql))
                connection.commit()
            return True
        else:
            logging.debug(f"Table {table_name} existe déjà")
            return False
    except Exception as e:
        logging.error(f"Erreur lors de la création de la table {table_name}: {e}")
        return False

def run_automatic_migrations(app, db):
    """
    Exécute toutes les migrations automatiques nécessaires
    Cette fonction est appelée au démarrage de l'application
    """
    logging.info("Vérification des migrations automatiques...")
    
    try:
        # Note: Sauvegarde automatique disponible via l'interface web ou manuellement
        # pour éviter les imports circulaires lors du démarrage
        
        engine = db.engine
        migrations_applied = 0
        db_type = get_database_type()

        # Définition du type auto-incrément selon la DB
        pk_type = "SERIAL PRIMARY KEY" if db_type == "postgresql" else "INTEGER PRIMARY KEY"
        
        # Vérifier et créer les tables manquantes si nécessaire
        required_tables = {
            'migration_log': f'''
                CREATE TABLE migration_log (
                    id {pk_type},
                    migration_name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version VARCHAR(50)
                )
            ''',
            'system_health': f'''
                CREATE TABLE system_health (
                    id {pk_type},
                    check_name VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            '''
        }
        
        for table_name, create_sql in required_tables.items():
            if create_table_safely(engine, table_name, create_sql):
                migrations_applied += 1
                logging.info(f"✓ Table {table_name} créée")
        
        # Migration 1: Ajouter sendgrid_api_key à parametres_systeme
        if add_column_safely(engine, 'parametres_systeme', 'sendgrid_api_key', 'VARCHAR(500)'):
            migrations_applied += 1
            logging.info("✓ Migration: Colonne sendgrid_api_key ajoutée")
        
        # Migration 3: Colonnes de sécurité et chiffrement (Utilisateurs)
        # Note: 'user' est un mot réservé en PostgreSQL, utiliser des guillemets
        user_security_columns = [
            ('email_encrypted', 'TEXT'),
            ('nom_complet_encrypted', 'TEXT'),
            ('matricule_encrypted', 'TEXT'),
            ('fonction_encrypted', 'TEXT'),
            ('password_hash_encrypted', 'TEXT'),
            ('matricule', 'VARCHAR(50)'),
            ('fonction', 'VARCHAR(200)'),
            ('photo_profile', 'VARCHAR(255)')
        ]

        # Déterminer le nom de la table user avec guillemets pour Postgres si nécessaire
        user_table_name = '"user"' if db_type == 'postgresql' else 'user'
        
        for column_name, column_type in user_security_columns:
            if add_column_safely(engine, user_table_name, column_name, column_type):
                migrations_applied += 1
                logging.info(f"✓ Migration: Colonne {column_name} ajoutée aux utilisateurs")

        # Migration 4: Colonnes de sécurité et chiffrement (Courriers)
        courrier_security_columns = [
            ('objet_encrypted', 'TEXT'),
            ('expediteur_encrypted', 'TEXT'),
            ('destinataire_encrypted', 'TEXT'),
            ('numero_reference_encrypted', 'TEXT'),
            ('fichier_checksum', 'VARCHAR(64)'),
            ('fichier_encrypted', 'BOOLEAN DEFAULT FALSE'),
            ('secretaire_general_copie', 'BOOLEAN')
        ]

        for column_name, column_type in courrier_security_columns:
            if add_column_safely(engine, 'courrier', column_name, column_type):
                migrations_applied += 1
                logging.info(f"✓ Migration: Colonne {column_name} ajoutée aux courriers")

        # Migration 5: Vérification des colonnes critiques
        critical_columns = [
            ('parametres_systeme', 'email_provider', "VARCHAR(20) DEFAULT 'sendgrid'"),
            ('parametres_systeme', 'notify_superadmin_new_mail', 'BOOLEAN DEFAULT TRUE'),
            ('parametres_systeme', 'titre_responsable_structure', "VARCHAR(100) DEFAULT 'Secrétaire Général'"),
        ]
        
        for table, column, definition in critical_columns:
            if add_column_safely(engine, table, column, definition):
                migrations_applied += 1
                logging.info(f"✓ Migration: Colonne critique {column} ajoutée à {table}")
        
        # Migration 6: Ajout des colonnes pour les pièces jointes dans les transmissions
        forward_attachment_columns = [
            ('courrier_forward', 'attached_file', 'VARCHAR(255)'),
            ('courrier_forward', 'attached_file_original_name', 'VARCHAR(255)'),
            ('courrier_forward', 'attached_file_size', 'INTEGER'),
        ]
        
        for table, column, definition in forward_attachment_columns:
            if add_column_safely(engine, table, column, definition):
                migrations_applied += 1
                logging.info(f"✓ Migration: Colonne de pièce jointe {column} ajoutée à {table}")
        
        # Migration 7: Ajout du numéro WhatsApp
        if add_column_safely(engine, 'parametres_systeme', 'whatsapp_number', "VARCHAR(20) DEFAULT '243860493345'"):
            migrations_applied += 1
            logging.info(f"✓ Migration: Colonne whatsapp_number ajoutée aux paramètres")

        # Migration 8b: Colonnes rappels / échéances sur courrier
        reminder_columns = [
            ('courrier', 'due_date', 'DATE'),
            ('courrier', 'reminder_sent_at', 'TIMESTAMP'),
        ]
        for table, col, defn in reminder_columns:
            if add_column_safely(engine, table, col, defn):
                migrations_applied += 1
                logging.info(f"✓ Migration: Colonne {col} ajoutée à {table}")

        # Migration 8: Table des pièces jointes supplémentaires
        pk_serial = "SERIAL PRIMARY KEY" if db_type == "postgresql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
        attachment_sql = f'''
            CREATE TABLE courrier_attachment (
                id {pk_serial},
                courrier_id INTEGER NOT NULL REFERENCES courrier(id),
                fichier_nom VARCHAR(255) NOT NULL,
                fichier_chemin VARCHAR(500) NOT NULL,
                fichier_type VARCHAR(50),
                fichier_taille INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                uploaded_by_id INTEGER NOT NULL REFERENCES "user"(id)
            )
        ''' if db_type == "postgresql" else f'''
            CREATE TABLE courrier_attachment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                courrier_id INTEGER NOT NULL REFERENCES courrier(id),
                fichier_nom VARCHAR(255) NOT NULL,
                fichier_chemin VARCHAR(500) NOT NULL,
                fichier_type VARCHAR(50),
                fichier_taille INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                uploaded_by_id INTEGER NOT NULL REFERENCES user(id)
            )
        '''
        if create_table_safely(engine, 'courrier_attachment', attachment_sql):
            migrations_applied += 1
            logging.info("✓ Migration: Table courrier_attachment créée")

        # Migration 9: Index GIN pour la recherche full-text (PostgreSQL uniquement)
        if db_type == 'postgresql':
            try:
                with engine.connect() as conn:
                    # Vérifier si l'index existe déjà
                    result = conn.execute(text(
                        "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_courrier_fts'"
                    ))
                    if not result.fetchone():
                        conn.execute(text("""
                            CREATE INDEX CONCURRENTLY idx_courrier_fts
                            ON courrier
                            USING gin(
                                to_tsvector('french',
                                    coalesce(objet,'') || ' ' ||
                                    coalesce(expediteur,'') || ' ' ||
                                    coalesce(destinataire,'') || ' ' ||
                                    coalesce(numero_accuse_reception,'') || ' ' ||
                                    coalesce(numero_reference,'')
                                )
                            )
                        """))
                        conn.commit()
                        migrations_applied += 1
                        logging.info("✓ Migration: Index GIN full-text idx_courrier_fts créé")
            except Exception as e:
                logging.warning(f"Index GIN (optionnel) non créé: {e}")

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
        db_type = get_database_type()
        pk_type = "SERIAL PRIMARY KEY" if db_type == "postgresql" else "INTEGER PRIMARY KEY"

        sql = f"""
        CREATE TABLE IF NOT EXISTS migration_log (
            id {pk_type},
            migration_name VARCHAR(255) NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN DEFAULT TRUE
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
