#!/usr/bin/env python
"""
Script de migration pour corriger les chemins de fichiers dans la base de données.
Convertit les chemins absolus en chemins relatifs pour la compatibilité avec PythonAnywhere.
"""

import os
import sys
from app import app, db
from models import Courrier
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_file_paths():
    """Corriger tous les chemins de fichiers dans la base de données"""
    
    with app.app_context():
        # Créer les dossiers nécessaires s'ils n'existent pas
        os.makedirs('uploads', exist_ok=True)
        os.makedirs('exports', exist_ok=True)
        
        # Récupérer tous les courriers avec des fichiers
        courriers = Courrier.query.filter(Courrier.fichier_chemin.isnot(None)).all()
        
        fixed_count = 0
        error_count = 0
        
        for courrier in courriers:
            old_path = courrier.fichier_chemin
            
            # Si c'est déjà un chemin relatif, passer
            if not old_path.startswith('/'):
                continue
            
            # Extraire la partie relative du chemin
            new_path = old_path
            
            # Chercher la partie uploads dans le chemin
            if 'uploads/' in old_path:
                # Extraire tout après 'uploads/'
                parts = old_path.split('uploads/')
                if len(parts) > 1:
                    relative_part = parts[-1]
                    new_path = os.path.join('uploads', relative_part)
            elif old_path.startswith('/home/') or old_path.startswith('/Users/'):
                # Chemin absolu complet - essayer de trouver uploads
                if '/uploads/' in old_path:
                    parts = old_path.split('/uploads/')
                    if len(parts) > 1:
                        new_path = os.path.join('uploads', parts[-1])
            
            # Mettre à jour si le chemin a changé
            if new_path != old_path:
                courrier.fichier_chemin = new_path
                fixed_count += 1
                logger.info(f"Corrigé: {old_path} -> {new_path}")
                
                # Vérifier si le fichier existe au nouveau chemin
                if not os.path.exists(new_path):
                    logger.warning(f"Attention: Le fichier n'existe pas à {new_path}")
                    error_count += 1
        
        # Sauvegarder les changements
        try:
            db.session.commit()
            logger.info(f"Migration terminée: {fixed_count} chemins corrigés, {error_count} fichiers manquants")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la sauvegarde: {e}")
            return False
        
        return True

if __name__ == '__main__':
    logger.info("Début de la migration des chemins de fichiers...")
    if fix_file_paths():
        logger.info("Migration réussie!")
    else:
        logger.error("Migration échouée!")
        sys.exit(1)