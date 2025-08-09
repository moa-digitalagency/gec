#!/usr/bin/env python3
"""
Script pour mettre à jour le fichier Excel avec les licences de la base de données
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

def update_excel_with_licenses():
    """Met à jour le fichier Excel avec les licences de la base"""
    
    # Connexion à la base de données
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL non configurée")
        return False
    
    print(f"🔗 Connexion à la base de données...")
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as connection:
            # Récupère toutes les licences
            query = text("""
                SELECT 
                    license_key,
                    duration_days,
                    duration_label,
                    status,
                    is_used,
                    created_date,
                    batch_id,
                    used_date,
                    used_domain
                FROM licenses 
                ORDER BY duration_days, license_key
            """)
            
            result = connection.execute(query).fetchall()
            
            if not result:
                print("❌ Aucune licence trouvée dans la base")
                return False
            
            print(f"📊 {len(result)} licences trouvées")
            
            # Convertit en DataFrame
            df = pd.DataFrame(result, columns=[
                'license_key', 'duration_days', 'duration_label', 
                'status', 'is_used', 'created_date', 'batch_id',
                'used_date', 'used_domain'
            ])
            
            # Formate les colonnes
            df['is_used'] = df['is_used'].map({True: 'OUI', False: 'NON'})
            df['created_date'] = pd.to_datetime(df['created_date']).dt.strftime('%d/%m/%Y %H:%M')
            df['used_date'] = pd.to_datetime(df['used_date'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')
            
            # Renomme les colonnes pour l'affichage
            df.columns = [
                'Clé de Licence', 'Durée (jours)', 'Type de Licence',
                'Statut', 'Utilisée', 'Date de Création', 'Lot',
                'Date d\'Utilisation', 'Domaine Utilisé'
            ]
            
            # Sauvegarde dans Excel
            excel_file = 'gec_licenses.xlsx'
            
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Feuille principale avec toutes les licences
                df.to_excel(writer, sheet_name='Toutes les Licences', index=False)
                
                # Feuilles par type de licence
                for duration_label in df['Type de Licence'].unique():
                    subset = df[df['Type de Licence'] == duration_label]
                    sheet_name = duration_label.replace(' ', '_').replace('/', '_')
                    subset.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Feuille de statistiques
                stats_data = []
                for duration_label in df['Type de Licence'].unique():
                    subset = df[df['Type de Licence'] == duration_label]
                    total = len(subset)
                    used = len(subset[subset['Utilisée'] == 'OUI'])
                    available = total - used
                    
                    stats_data.append({
                        'Type': duration_label,
                        'Total': total,
                        'Utilisées': used,
                        'Disponibles': available,
                        '% Utilisées': f"{(used/total*100):.1f}%" if total > 0 else "0%"
                    })
                
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
                
                # Feuille avec les licences disponibles seulement
                available_df = df[df['Utilisée'] == 'NON'][['Clé de Licence', 'Type de Licence', 'Durée (jours)']]
                available_df.to_excel(writer, sheet_name='Licences Disponibles', index=False)
            
            print(f"✅ Fichier Excel mis à jour: {excel_file}")
            print(f"📋 Feuilles créées:")
            print("   - Toutes les Licences")
            print("   - Statistiques")
            print("   - Licences Disponibles")
            
            for duration_label in df['Type de Licence'].unique():
                sheet_name = duration_label.replace(' ', '_').replace('/', '_')
                count = len(df[df['Type de Licence'] == duration_label])
                print(f"   - {sheet_name} ({count} licences)")
            
            return True
            
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour: {e}")
        return False

def show_excel_summary():
    """Affiche un résumé du fichier Excel"""
    excel_file = 'gec_licenses.xlsx'
    
    if not os.path.exists(excel_file):
        print(f"❌ Fichier {excel_file} introuvable")
        return
    
    try:
        # Lit les statistiques
        stats_df = pd.read_excel(excel_file, sheet_name='Statistiques')
        print("📊 Résumé du fichier Excel:")
        print("=" * 50)
        
        for _, row in stats_df.iterrows():
            print(f"   {row['Type']:15} : {row['Total']:4} total ({row['Disponibles']:4} disponibles)")
        
        total_licenses = stats_df['Total'].sum()
        total_available = stats_df['Disponibles'].sum()
        total_used = stats_df['Utilisées'].sum()
        
        print("=" * 50)
        print(f"   {'TOTAL':15} : {total_licenses:4} total ({total_available:4} disponibles, {total_used:4} utilisées)")
        
    except Exception as e:
        print(f"❌ Erreur lors de la lecture: {e}")

if __name__ == "__main__":
    print("🔑 Mise à jour du fichier Excel des licences")
    print("=" * 50)
    
    if update_excel_with_licenses():
        print("\n" + "=" * 50)
        show_excel_summary()
    else:
        print("❌ Échec de la mise à jour")