#!/usr/bin/env python3
"""
Générateur de licences pour fichier Excel - GEC Mines
Génère 5000 licences et les sauvegarde dans un fichier Excel
"""

import pandas as pd
import secrets
from datetime import datetime
import os

def generate_license_key():
    """Génère une clé de licence unique de 12 caractères"""
    return ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(12))

def generate_excel_licenses():
    """Génère 5000 licences et les sauvegarde dans Excel"""
    
    license_types = [
        (1, "1 jour", 1000),
        (5, "5 jours", 1000), 
        (30, "1 mois", 1000),
        (180, "6 mois", 1000),
        (365, "12 mois", 1000)
    ]
    
    all_licenses = []
    batch_id = f"GEC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("🔑 Génération de 5000 licences GEC Mines")
    print("=" * 50)
    
    total_generated = 0
    for duration_days, duration_label, count in license_types:
        print(f"📋 Génération de {count} licences '{duration_label}' ({duration_days} jours)...")
        
        for i in range(count):
            license_key = generate_license_key()
            
            license_data = {
                'license_key': license_key,
                'duration_days': duration_days,
                'duration_label': duration_label,
                'status': 'ACTIVE',
                'is_used': False,
                'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'batch_id': batch_id,
                'created_by': 'SYSTEM'
            }
            
            all_licenses.append(license_data)
            total_generated += 1
            
            if (i + 1) % 200 == 0:
                print(f"   ✓ {i + 1}/{count} licences générées")
        
        print(f"   🎯 {count} licences '{duration_label}' terminées ✓")
    
    # Crée le DataFrame
    df = pd.DataFrame(all_licenses)
    
    # Sauvegarde dans Excel
    filename = 'gec_licenses.xlsx'
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Feuille principale avec toutes les licences
        df.to_excel(writer, sheet_name='Toutes_Licences', index=False)
        
        # Feuilles séparées par type
        for duration_days, duration_label, count in license_types:
            sheet_name = duration_label.replace(' ', '_')
            type_df = df[df['duration_label'] == duration_label]
            type_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Feuille de statistiques
        stats_data = []
        for duration_days, duration_label, count in license_types:
            type_count = len(df[df['duration_label'] == duration_label])
            stats_data.append({
                'Type': duration_label,
                'Durée (jours)': duration_days,
                'Nombre généré': type_count,
                'Statut': 'ACTIVE'
            })
        
        stats_data.append({
            'Type': 'TOTAL',
            'Durée (jours)': '-',
            'Nombre généré': len(df),
            'Statut': 'ALL'
        })
        
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
    
    print("=" * 50)
    print(f"✅ Génération terminée avec succès !")
    print(f"📊 Total généré: {total_generated} licences")
    print(f"💾 Fichier sauvegardé: {filename}")
    print(f"🔖 Batch ID: {batch_id}")
    
    # Affiche quelques exemples
    print("\n🎲 Exemples de licences générées:")
    for duration_days, duration_label, count in license_types:
        examples = df[df['duration_label'] == duration_label]['license_key'].head(3).tolist()
        print(f"   {duration_label}: {', '.join(examples)}")
    
    return filename, total_generated

if __name__ == "__main__":
    try:
        filename, count = generate_excel_licenses()
        print(f"\n🎉 F