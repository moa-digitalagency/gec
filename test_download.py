#!/usr/bin/env python
"""Script de test pour vérifier le téléchargement des fichiers"""

import os
from app import app, db
from models import Courrier
from flask import send_from_directory

def test_file_download():
    """Tester le téléchargement de fichier"""
    
    with app.app_context():
        # Récupérer le courrier avec ID 1
        courrier = Courrier.query.get(1)
        
        if not courrier:
            print("Aucun courrier avec ID 1")
            return
        
        print(f"Courrier trouvé: {courrier.numero_accuse_reception}")
        print(f"Fichier nom: {courrier.fichier_nom}")
        print(f"Fichier chemin dans DB: {courrier.fichier_chemin}")
        
        if courrier.fichier_chemin:
            file_path = courrier.fichier_chemin
            
            # Si le chemin est absolu, extraire la partie relative
            if file_path.startswith('/'):
                print(f"Chemin absolu détecté: {file_path}")
                if 'uploads/' in file_path:
                    relative_path = file_path.split('uploads/')[-1]
                    file_path = os.path.join('uploads', relative_path)
                    print(f"Converti en chemin relatif: {file_path}")
            
            print(f"Chemin final: {file_path}")
            print(f"Chemin absolu: {os.path.abspath(file_path)}")
            print(f"Le fichier existe? {os.path.exists(file_path)}")
            
            if os.path.exists(file_path):
                print("✅ Le fichier existe!")
                directory = os.path.dirname(file_path)
                filename = os.path.basename(file_path)
                print(f"Directory: {directory}")
                print(f"Filename: {filename}")
                
                # Vérifier le dossier
                if os.path.exists(directory):
                    print(f"✅ Le dossier {directory} existe")
                    files_in_dir = os.listdir(directory)
                    print(f"Fichiers dans le dossier: {files_in_dir[:5]}")  # Afficher les 5 premiers
                else:
                    print(f"❌ Le dossier {directory} n'existe pas")
            else:
                print("❌ Le fichier n'existe pas au chemin calculé")
                
                # Essayer de trouver le fichier
                print("\nRecherche du fichier...")
                if os.path.exists('uploads'):
                    uploads_files = os.listdir('uploads')
                    print(f"Fichiers dans uploads: {uploads_files}")
                    
                    # Chercher le fichier par nom
                    for f in uploads_files:
                        if 'Adobe' in f or '20250811' in f:
                            print(f"Fichier trouvé: uploads/{f}")
                            print(f"Correspond au nom dans DB? {f in courrier.fichier_chemin}")
        else:
            print("Pas de fichier attaché à ce courrier")

if __name__ == '__main__':
    test_file_download()