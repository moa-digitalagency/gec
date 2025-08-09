#!/usr/bin/env python3
"""
Générateur initial de 5000 licences pour le serveur centralisé
"""

import os
import sys
import secrets
from datetime import datetime
from sqlalchemy import create_engine, text

# Configuration de la base de données
DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite:///license_server.db"

def generate_license_key():
    """Génère une clé de licence unique de 12 caractères"""
    return ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(12))

def generate_licenses():
    """Génère 5000 licences (1000 de chaque type)"""
    engine = create_engine(DATABASE_URL)
    
    license_types = [
        (1, "1 jour"),
        (5, "5 jours"), 
        (30, "1 mois"),
        (180, "6 mois"),
        (365, "12 mois")
    ]
    
    batch_id = f"INITIAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    total_generated = 0
    
    print(f"🚀 Génération de 5000 licences dans la base: {DATABASE_URL}")
    print(f"📦 Batch ID: {batch_id}")
    print("=" * 60)
    
    with engine.connect() as connection:
        # Crée la table si elle n'existe pas
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key VARCHAR(12) UNIQUE NOT NULL,
                duration_days INTEGER NOT NULL,
                duration_label VARCHAR(50) NOT NULL,
                status VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
                is_used BOOLEAN DEFAULT FALSE NOT NULL,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100) DEFAULT 'SYSTEM',
                batch_id VARCHAR(50),
                used_date TIMESTAMP,
                activation_date TIMESTAMP,
                expiration_date TIMESTAMP,
                used_domain VARCHAR(100),
                used_ip VARCHAR(45),
                client_info TEXT
            )
        """))
        
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_license_key ON licenses(license_key);
        """))
        
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_status_used ON licenses(status, is_used);
        """))
        
        for duration_days, duration_label in license_types:
            print(f"📋 Génération de 1000 licences de type '{duration_label}' ({duration_days} jours)...")
            
            licenses_batch = []
            for i in range(1000):
                # Génère une clé unique
                while True:
                    license_key = generate_license_key()
                    
                    # Vérifie l'unicité
                    check_query = text("SELECT COUNT(*) FROM licenses WHERE license_key = :key")
                    result = connection.execute(check_query, {"key": license_key}).fetchone()
                    
                    if result[0] == 0:
                        break
                
                licenses_batch.append({
                    'license_key': license_key,
                    'duration_days': duration_days,
                    'duration_label': duration_label,
                    'batch_id': batch_id
                })
                
                if (i + 1) % 100 == 0:
                    print(f"   ✓ {i + 1}/1000 licences générées")
            
            # Insert par batch
            insert_query = text("""
                INSERT INTO licenses (license_key, duration_days, duration_label, batch_id, created_by)
                VALUES (:license_key, :duration_days, :duration_label, :batch_id, 'SYSTEM')
            """)
            
            connection.execute(insert_query, licenses_batch)
            connection.commit()
            
            total_generated += len(licenses_batch)
            print(f"   🎯 1000 licences '{duration_label}' sauvegardées ✓")
            print()
    
    print("=" * 60)
    print(f"✅ Génération terminée avec succès !")
    print(f"📊 Total généré: {total_generated} licences")
    print(f"💾 Base de données: {DATABASE_URL}")
    print(f"🔖 Batch ID: {batch_id}")
    
    # Affiche quelques exemples
    print("\n🎲 Exemples de licences générées:")
    with engine.connect() as connection:
        for duration_days, duration_label in license_types:
            query = text("""
                SELECT license_key FROM licenses 
                WHERE duration_label = :label AND batch_id = :batch_id 
                LIMIT 3
            """)
            results = connection.execute(query, {
                "label": duration_label, 
                "batch_id": batch_id
            }).fetchall()
            
            print(f"   {duration_label}: {', '.join([r[0] for r in results])}")

def show_stats():
    """Affiche les statistiques de la base de données"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        # Statistiques globales
        total_query = text("SELECT COUNT(*) FROM licenses")
        total = connection.execute(total_query).fetchone()[0]
        
        available_query = text("SELECT COUNT(*) FROM licenses WHERE is_used = FALSE AND status = 'ACTIVE'")
        available = connection.execute(available_query).fetchone()[0]
        
        used_query = text("SELECT COUNT(*) FROM licenses WHERE is_used = TRUE")
        used = connection.execute(used_query).fetchone()[0]
        
        print(f"📊 Statistiques de la base de données:")
        print(f"   Total: {total} licences")
        print(f"   Disponibles: {available} licences")
        print(f"   Utilisées: {used} licences")
        print()
        
        # Par type
        type_query = text("""
            SELECT duration_label, COUNT(*) as count,
                   SUM(CASE WHEN is_used = FALSE AND status = 'ACTIVE' THEN 1 ELSE 0 END) as available
            FROM licenses 
            GROUP BY duration_label, duration_days
            ORDER BY duration_days
        """)
        
        results = connection.execute(type_query).fetchall()
        
        print("📋 Répartition par type:")
        for row in results:
            duration_label, count, available = row
            print(f"   {duration_label}: {count} total ({available} disponibles)")

def main():
    """Menu principal"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "generate":
            generate_licenses()
        elif command == "stats":
            show_stats()
        elif command == "reset":
            engine = create_engine(DATABASE_URL)
            with engine.connect() as connection:
                connection.execute(text("DROP TABLE IF EXISTS licenses"))
                connection.execute(text("DROP TABLE IF EXISTS license_activations"))
                connection.commit()
            print("🗑️  Base de données réinitialisée")
        else:
            print(f"❌ Commande inconnue: {command}")
            print("Usage: python generate_initial_licenses.py [generate|stats|reset]")
    else:
        print("🔑 Générateur de Licences GEC Mines")
        print("=" * 40)
        print("1. generate - Génère 5000 nouvelles licences")
        print("2. stats    - Affiche les statistiques")
        print("3. reset    - Remet à zéro la base")
        print()
        
        choice = input("Votre choix (1-3): ").strip()
        
        if choice == "1":
            generate_licenses()
        elif choice == "2":
            show_stats()
        elif choice == "3":
            confirm = input("⚠️  Confirmer la remise à zéro (oui/non): ").strip().lower()
            if confirm in ['oui', 'o', 'yes', 'y']:
                engine = create_engine(DATABASE_URL)
                with engine.connect() as connection:
                    connection.execute(text("DROP TABLE IF EXISTS licenses"))
                    connection.execute(text("DROP TABLE IF EXISTS license_activations"))
                    connection.commit()
                print("🗑️  Base de données réinitialisée")
            else:
                print("❌ Opération annulée")
        else:
            print("❌ Choix invalide")

if __name__ == "__main__":
    main()