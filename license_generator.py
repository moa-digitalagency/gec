#!/usr/bin/env python3
"""
Générateur de licences pour GEC Mines
Génère des lots de licences avec différentes durées et les exporte vers Excel et base de données
"""

import random
import string
import hashlib
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine, text
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LicenseGenerator:
    def __init__(self):
        self.licenses = []
        self.database_url = os.environ.get('DATABASE_URL')
        
        if not self.database_url:
            raise ValueError("DATABASE_URL non trouvée dans les variables d'environnement")
            
        self.engine = create_engine(self.database_url)
    
    def create_license_table(self):
        """Crée la table des licences dans la base de données"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS licenses (
            id SERIAL PRIMARY KEY,
            license_key VARCHAR(20) UNIQUE NOT NULL,
            duration_days INTEGER NOT NULL,
            duration_label VARCHAR(50) NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expiration_date TIMESTAMP NOT NULL,
            is_used BOOLEAN DEFAULT FALSE,
            used_date TIMESTAMP NULL,
            used_domain VARCHAR(255) NULL,
            used_ip VARCHAR(50) NULL,
            status VARCHAR(20) DEFAULT 'ACTIVE'
        );
        """
        
        # Index pour améliorer les performances
        create_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_license_key ON licenses(license_key);",
            "CREATE INDEX IF NOT EXISTS idx_license_status ON licenses(status);",
            "CREATE INDEX IF NOT EXISTS idx_license_used ON licenses(is_used);"
        ]
        
        try:
            with self.engine.connect() as connection:
                # Créer la table
                connection.execute(text(create_table_query))
                
                # Créer les index
                for index_query in create_indexes:
                    connection.execute(text(index_query))
                
                connection.commit()
                logger.info("Table 'licenses' créée avec succès")
                
        except Exception as e:
            logger.error(f"Erreur lors de la création de la table: {e}")
            raise
    
    def generate_license_key(self) -> str:
        """Génère une clé de licence unique de 12 caractères"""
        # Utilise des caractères alphanumériques (majuscules et chiffres)
        chars = string.ascii_uppercase + string.digits
        
        # Génère 12 caractères aléatoirement
        while True:
            license_key = ''.join(random.choices(chars, k=12))
            
            # Vérifie que la licence n'existe pas déjà
            if not self.license_exists(license_key):
                return license_key
    
    def license_exists(self, license_key: str) -> bool:
        """Vérifie si une licence existe déjà"""
        return any(license['license_key'] == license_key for license in self.licenses)
    
    def generate_licenses_batch(self, count: int, duration_days: int, duration_label: str):
        """Génère un lot de licences avec une durée donnée"""
        logger.info(f"Génération de {count} licences {duration_label}")
        
        batch = []
        creation_date = datetime.now()
        
        for i in range(count):
            license_key = self.generate_license_key()
            expiration_date = creation_date + timedelta(days=duration_days)
            
            license_data = {
                'license_key': license_key,
                'duration_days': duration_days,
                'duration_label': duration_label,
                'created_date': creation_date,
                'expiration_date': expiration_date,
                'is_used': False,
                'used_date': None,
                'used_domain': None,
                'used_ip': None,
                'status': 'ACTIVE'
            }
            
            batch.append(license_data)
            
            if (i + 1) % 100 == 0:
                logger.info(f"  Généré {i + 1}/{count} licences {duration_label}")
        
        self.licenses.extend(batch)
        logger.info(f"Terminé: {count} licences {duration_label} générées")
        return batch
    
    def generate_all_licenses(self):
        """Génère tous les lots de licences demandés"""
        license_types = [
            (1000, 5, "5 jours"),
            (1000, 30, "1 mois"),
            (1000, 180, "6 mois"), 
            (1000, 365, "12 mois")
        ]
        
        logger.info("Début de la génération de 4000 licences")
        
        for count, duration_days, duration_label in license_types:
            self.generate_licenses_batch(count, duration_days, duration_label)
        
        logger.info(f"Génération terminée: {len(self.licenses)} licences au total")
    
    def save_to_database(self):
        """Enregistre toutes les licences dans la base de données"""
        if not self.licenses:
            logger.warning("Aucune licence à enregistrer")
            return
        
        logger.info(f"Enregistrement de {len(self.licenses)} licences dans la base de données")
        
        # Prépare les données pour l'insertion
        insert_query = """
        INSERT INTO licenses (
            license_key, duration_days, duration_label, 
            created_date, expiration_date, is_used, status
        ) VALUES (
            :license_key, :duration_days, :duration_label,
            :created_date, :expiration_date, :is_used, :status
        )
        """
        
        try:
            with self.engine.connect() as connection:
                # Insertion par lots pour améliorer les performances
                batch_size = 100
                total_batches = (len(self.licenses) + batch_size - 1) // batch_size
                
                for i in range(0, len(self.licenses), batch_size):
                    batch = self.licenses[i:i + batch_size]
                    connection.execute(text(insert_query), batch)
                    
                    batch_num = (i // batch_size) + 1
                    logger.info(f"  Lot {batch_num}/{total_batches} enregistré")
                
                connection.commit()
                logger.info("Toutes les licences ont été enregistrées dans la base de données")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement: {e}")
            raise
    
    def export_to_excel(self, filename: str = "gec_licenses.xlsx"):
        """Exporte toutes les licences vers un fichier Excel"""
        if not self.licenses:
            logger.warning("Aucune licence à exporter")
            return
        
        logger.info(f"Export des licences vers {filename}")
        
        # Convertit les données en DataFrame
        df = pd.DataFrame(self.licenses)
        
        # Formate les dates
        df['created_date'] = pd.to_datetime(df['created_date'])
        df['expiration_date'] = pd.to_datetime(df['expiration_date'])
        
        # Réordonne les colonnes
        column_order = [
            'license_key', 'duration_label', 'duration_days',
            'created_date', 'expiration_date', 'status',
            'is_used', 'used_date', 'used_domain', 'used_ip'
        ]
        df = df[column_order]
        
        # Crée un fichier Excel avec plusieurs feuilles
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Feuille principale avec toutes les licences
            df.to_excel(writer, sheet_name='Toutes les licences', index=False)
            
            # Feuilles séparées par durée
            for duration_label in df['duration_label'].unique():
                sheet_name = duration_label.replace(' ', '_')
                df_filtered = df[df['duration_label'] == duration_label]
                df_filtered.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Feuille de statistiques
            stats_data = {
                'Type de licence': df['duration_label'].unique(),
                'Nombre de licences': [
                    len(df[df['duration_label'] == label]) 
                    for label in df['duration_label'].unique()
                ],
                'Statut': ['ACTIVE'] * len(df['duration_label'].unique())
            }
            
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
        
        logger.info(f"Export terminé: {filename}")
        return filename
    
    def generate_report(self):
        """Génère un rapport de synthèse"""
        if not self.licenses:
            return "Aucune licence générée"
        
        report = []
        report.append("=== RAPPORT DE GÉNÉRATION DES LICENCES GEC MINES ===")
        report.append(f"Date de génération: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Nombre total de licences: {len(self.licenses)}")
        report.append("")
        
        # Statistiques par durée
        report.append("RÉPARTITION PAR DURÉE:")
        duration_stats = {}
        for license in self.licenses:
            label = license['duration_label']
            if label not in duration_stats:
                duration_stats[label] = 0
            duration_stats[label] += 1
        
        for duration, count in sorted(duration_stats.items()):
            report.append(f"  - {duration}: {count} licences")
        
        report.append("")
        report.append("EXEMPLES DE LICENCES GÉNÉRÉES:")
        
        # Affiche quelques exemples de chaque type
        shown_types = set()
        for license in self.licenses[:50]:  # Limite aux 50 premières
            label = license['duration_label']
            if label not in shown_types:
                report.append(f"  - {license['license_key']} ({label})")
                shown_types.add(label)
        
        report.append("")
        report.append("STATUT: Toutes les licences sont ACTIVES et prêtes à l'utilisation")
        report.append("=" * 55)
        
        return "\n".join(report)


def main():
    """Fonction principale pour générer les licences"""
    try:
        # Initialise le générateur
        generator = LicenseGenerator()
        
        # Crée la table si nécessaire
        print("Création de la table des licences...")
        generator.create_license_table()
        
        # Génère toutes les licences
        print("Génération des licences...")
        generator.generate_all_licenses()
        
        # Sauvegarde dans la base de données
        print("Enregistrement dans la base de données...")
        generator.save_to_database()
        
        # Export vers Excel
        print("Export vers Excel...")
        excel_file = generator.export_to_excel()
        
        # Affiche le rapport
        print("\n" + generator.generate_report())
        
        print(f"\n✅ Génération terminée avec succès!")
        print(f"📊 Fichier Excel créé: {excel_file}")
        print(f"🗄️ {len(generator.licenses)} licences enregistrées dans la base de données")
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération: {e}")
        print(f"❌ Erreur: {e}")
        return False


if __name__ == "__main__":
    main()