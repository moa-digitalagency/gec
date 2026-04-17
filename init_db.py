import os
import logging
from app import app, db
import models
from utils.migrations import run_automatic_migrations, apply_database_specific_fixes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def init_db():
    """
    Initialize the database, run migrations, and seed default data.
    This script is idempotent and safe to run on existing databases.
    """
    logging.info("Starting database initialization...")

    with app.app_context():
        try:
            # 1. Create tables if they don't exist
            logging.info("Creating tables...")
            db.create_all()
            logging.info("Tables created successfully.")

            # 2. Run automatic migrations (add missing columns)
            logging.info("Running automatic migrations...")
            run_automatic_migrations(app, db)
            apply_database_specific_fixes(db.engine)
            logging.info("Migrations completed.")

            # 3. Initialize default data (Roles, Permissions, Statuses, Departments, etc.)
            logging.info("Initializing default data...")
            models.init_default_data()
            logging.info("Default data initialized.")

            # 4. Initialize Super Admin
            logging.info("Checking Super Admin account...")
            models.User.init_super_admin()
            logging.info("Super Admin check completed.")

            logging.info("Database initialization completed successfully!")

        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            raise e

if __name__ == "__main__":
    init_db()
