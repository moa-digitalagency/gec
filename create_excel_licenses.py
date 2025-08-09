#!/usr/bin/env python3
"""
Générateur de fichier Excel avec les licences depuis la base de données
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

def create_excel_from_db():
    """Crée le fichier Excel avec toutes les licences de la base"""
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL non définie")
        return
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Récupère toutes les licences
            query = text("""
                SELECT license_key, duration_days, duration_label, status, is_used,
                       created_date, used_date, batch_id
                FROM licenses 
                ORDER BY duration_days, license_key
            """)
            
            result = connection.execute(query).fetchall()
            
            if not result:
                print("❌ Aucune licence trouvée dans la base de données")
                return
            
            # Conversion en DataFrame
            df = pd.DataFrame(result, columns=[
                'Clé de Licence', 'Durée (jours)', 'Type', 'Statut', 'Utilisée',
                'Date de Création', 'Date d\'Utilisation', 'Batch ID'
            ])
            
            # Formatage des colonnes
            df['Utilisée'] = df['Utilisée'].map({True: 'OUI', False: 'NON'})
            df['Date de Création'] = pd.to_datetime(df['Date de Création']).dt.strftime('%d/%m/%Y %H:%M')
            df['Date d\'Utilisation'] = df['Date d\'Utilisation'].fillna('N/A')
            
            # Sauvegarde du fichier Excel
            filename = 'gec_licenses.xlsx'
            
            # Crée plusieurs feuilles par type
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Feuille complète
                df.to_excel(writer, sheet_name='Toutes les Licences', index=False)
                
                # Feuilles par type de licence
                for duration_label in df['Type'].unique():
                    df_type = df[df['Type'] == duration_label]
                    sheet_name = duration_label.replace(' ', '_')
                    df_type.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Feuille de statistiques
                stats_data = []
                for duration_label in df['Type'].unique():
                    type_df = df[df['Type'] == duration_label]
                    total = len(type_df)
                    used = len(type_df[type_df['Utilisée'] == 'OUI'])
                    available = total - used
                    
                    stats_data.append({
                        'Type de Licence': duration_label,
                        'Total': total,
                        'Utilisées': used,
                        'Disponibles': available,
                        'Pourcentage Utilisé': f"{(used/total*100):