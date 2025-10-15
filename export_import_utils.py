"""
Module d'export/import de courriers avec gestion du chiffrement
Permet l'export de courriers d'une instance et l'import vers une autre instance
avec des clés de chiffrement différentes
"""

import os
import json
import zipfile
import logging
import shutil
from datetime import datetime
from app import db
from models import Courrier, CourrierForward
from encryption_utils import encryption_manager, decrypt_sensitive_data, encrypt_sensitive_data

# Version du format d'export pour assurer la compatibilité
EXPORT_FORMAT_VERSION = "1.0.0"

def export_courriers_to_json(courrier_ids=None, export_all=False):
    """
    Exporte les courriers en JSON avec déchiffrement des données sensibles
    
    Args:
        courrier_ids (list): Liste des IDs de courriers à exporter (None = tous)
        export_all (bool): Exporter tous les courriers (incluant supprimés)
        
    Returns:
        dict: Données exportées avec métadonnées
    """
    logging.info("Début de l'export des courriers...")
    
    # Requête de base
    query = Courrier.query
    
    if not export_all:
        query = query.filter_by(is_deleted=False)
    
    if courrier_ids:
        query = query.filter(Courrier.id.in_(courrier_ids))
    
    courriers = query.all()
    
    export_data = {
        "version": EXPORT_FORMAT_VERSION,
        "export_date": datetime.utcnow().isoformat(),
        "total_courriers": len(courriers),
        "courriers": [],
        "attachments": []
    }
    
    for courrier in courriers:
        # Déchiffrer les données sensibles
        courrier_data = {
            "id": courrier.id,
            "numero_accuse_reception": courrier.numero_accuse_reception,
            "type_courrier": courrier.type_courrier,
            "type_courrier_sortant_id": courrier.type_courrier_sortant_id,
            "date_redaction": courrier.date_redaction.isoformat() if courrier.date_redaction else None,
            "date_enregistrement": courrier.date_enregistrement.isoformat() if courrier.date_enregistrement else None,
            "statut": courrier.statut,
            "date_modification_statut": courrier.date_modification_statut.isoformat() if courrier.date_modification_statut else None,
            "secretaire_general_copie": courrier.secretaire_general_copie,
            "fichier_nom": courrier.fichier_nom,
            "fichier_type": courrier.fichier_type,
            "fichier_checksum": courrier.fichier_checksum,
            "fichier_encrypted": courrier.fichier_encrypted,
            "autres_informations": courrier.autres_informations,
            "is_deleted": courrier.is_deleted,
            "deleted_at": courrier.deleted_at.isoformat() if courrier.deleted_at else None,
            "utilisateur_id": courrier.utilisateur_id,
        }
        
        # Déchiffrer les champs sensibles
        try:
            if courrier.objet_encrypted:
                courrier_data["objet"] = decrypt_sensitive_data(courrier.objet_encrypted)
            else:
                courrier_data["objet"] = courrier.objet
            
            if courrier.expediteur_encrypted:
                courrier_data["expediteur"] = decrypt_sensitive_data(courrier.expediteur_encrypted)
            else:
                courrier_data["expediteur"] = courrier.expediteur
            
            if courrier.destinataire_encrypted:
                courrier_data["destinataire"] = decrypt_sensitive_data(courrier.destinataire_encrypted)
            else:
                courrier_data["destinataire"] = courrier.destinataire
            
            if courrier.numero_reference_encrypted:
                courrier_data["numero_reference"] = decrypt_sensitive_data(courrier.numero_reference_encrypted)
            else:
                courrier_data["numero_reference"] = courrier.numero_reference
                
        except Exception as e:
            logging.error(f"Erreur lors du déchiffrement du courrier {courrier.id}: {e}")
            # Utiliser les valeurs non chiffrées en fallback
            courrier_data["objet"] = courrier.objet
            courrier_data["expediteur"] = courrier.expediteur
            courrier_data["destinataire"] = courrier.destinataire
            courrier_data["numero_reference"] = courrier.numero_reference
        
        # Gérer le fichier attaché principal
        if courrier.fichier_chemin and os.path.exists(courrier.fichier_chemin):
            attachment_data = {
                "courrier_id": courrier.id,
                "type": "main",
                "filename": courrier.fichier_nom,
                "path": courrier.fichier_chemin,
                "encrypted": courrier.fichier_encrypted,
                "checksum": courrier.fichier_checksum
            }
            export_data["attachments"].append(attachment_data)
        
        # Gérer les transmissions
        forwards = CourrierForward.query.filter_by(courrier_id=courrier.id).all()
        courrier_data["forwards"] = []
        for forward in forwards:
            forward_data = {
                "from_department_id": forward.from_department_id,
                "to_department_id": forward.to_department_id,
                "forward_date": forward.forward_date.isoformat() if forward.forward_date else None,
                "comments": forward.comments,
                "read_date": forward.read_date.isoformat() if forward.read_date else None,
                "is_read": forward.is_read,
                "attached_file_original_name": forward.attached_file_original_name
            }
            
            # Gérer les fichiers joints aux transmissions
            if forward.attached_file and os.path.exists(forward.attached_file):
                attachment_data = {
                    "courrier_id": courrier.id,
                    "type": "forward",
                    "forward_id": forward.id,
                    "filename": forward.attached_file_original_name,
                    "path": forward.attached_file,
                    "encrypted": False
                }
                export_data["attachments"].append(attachment_data)
            
            courrier_data["forwards"].append(forward_data)
        
        export_data["courriers"].append(courrier_data)
    
    logging.info(f"Export terminé: {len(courriers)} courriers, {len(export_data['attachments'])} fichiers")
    return export_data


def create_export_package(courrier_ids=None, export_all=False, output_dir='exports'):
    """
    Crée un package d'export complet avec JSON et fichiers
    
    Args:
        courrier_ids (list): Liste des IDs de courriers à exporter
        export_all (bool): Exporter tous les courriers
        output_dir (str): Répertoire de sortie
        
    Returns:
        str: Chemin du fichier ZIP créé
    """
    # Créer le dossier d'export s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    # Exporter les données
    export_data = export_courriers_to_json(courrier_ids, export_all)
    
    # Créer le nom du fichier avec timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_filename = f"export_courriers_{timestamp}.zip"
    export_path = os.path.join(output_dir, export_filename)
    
    with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Ajouter le fichier JSON
        json_filename = "courriers_data.json"
        json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
        zipf.writestr(json_filename, json_data)
        
        # Créer un dossier temporaire pour déchiffrer les fichiers
        temp_dir = os.path.join(output_dir, f'temp_export_{timestamp}')
        os.makedirs(temp_dir, exist_ok=True)
        
        failed_files = []
        try:
            # Ajouter les fichiers déchiffrés
            for attachment in export_data["attachments"]:
                source_path = attachment["path"]
                arc_name = f"attachments/{attachment['courrier_id']}_{attachment['filename']}"
                
                if attachment.get("encrypted", False):
                    # Déchiffrer le fichier temporairement
                    temp_decrypted_path = os.path.join(temp_dir, attachment['filename'])
                    try:
                        encryption_manager.decrypt_file(source_path, temp_decrypted_path)
                        zipf.write(temp_decrypted_path, arc_name)
                        logging.info(f"Fichier déchiffré et ajouté: {arc_name}")
                    except Exception as e:
                        error_msg = f"Erreur lors du déchiffrement du fichier {source_path}: {e}"
                        logging.error(error_msg)
                        failed_files.append({
                            "courrier_id": attachment['courrier_id'],
                            "filename": attachment['filename'],
                            "error": str(e)
                        })
                        # NE PAS ajouter le fichier chiffré - cela causerait un double chiffrement à l'import
                else:
                    # Fichier non chiffré, ajouter directement
                    if os.path.exists(source_path):
                        zipf.write(source_path, arc_name)
                    else:
                        failed_files.append({
                            "courrier_id": attachment['courrier_id'],
                            "filename": attachment['filename'],
                            "error": "Fichier introuvable"
                        })
        finally:
            # Nettoyer le dossier temporaire
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    # Vérifier s'il y a eu des erreurs
    if failed_files:
        # Supprimer le fichier ZIP créé car il est incomplet
        if os.path.exists(export_path):
            os.remove(export_path)
        
        error_details = "\n".join([
            f"- Courrier {f['courrier_id']}, fichier '{f['filename']}': {f['error']}" 
            for f in failed_files
        ])
        error_message = f"L'export a échoué. {len(failed_files)} fichier(s) n'ont pas pu être déchiffrés:\n{error_details}"
        logging.error(error_message)
        raise ValueError(error_message)
    
    logging.info(f"Package d'export créé avec succès: {export_path}")
    return export_path


def import_courriers_from_package(package_path, skip_existing=True, remap_users=None, assign_to_user_id=None):
    """
    Importe les courriers depuis un package d'export avec rechiffrement
    
    Args:
        package_path (str): Chemin du fichier ZIP d'export
        skip_existing (bool): Ignorer les courriers existants (par numéro)
        remap_users (dict): Mapping des IDs utilisateurs {ancien_id: nouvel_id}
        assign_to_user_id (int): ID de l'utilisateur à qui assigner TOUS les courriers importés
        
    Returns:
        dict: Résultat de l'import avec statistiques
    """
    import tempfile
    
    result = {
        "success": True,
        "imported": 0,
        "skipped": 0,
        "errors": 0,
        "details": []
    }
    
    # Créer un dossier temporaire pour l'extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extraire le package
        with zipfile.ZipFile(package_path, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        # Lire le fichier JSON
        json_path = os.path.join(temp_dir, 'courriers_data.json')
        if not os.path.exists(json_path):
            result["success"] = False
            result["details"].append("Fichier courriers_data.json introuvable dans le package")
            return result
        
        with open(json_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        # Vérifier la version
        if import_data.get("version") != EXPORT_FORMAT_VERSION:
            logging.warning(f"Version du format d'export différente: {import_data.get('version')} vs {EXPORT_FORMAT_VERSION}")
        
        # Mapping des IDs anciens vers nouveaux
        id_mapping = {}
        
        # Importer les courriers
        for courrier_data in import_data["courriers"]:
            try:
                # Vérifier si le courrier existe déjà
                existing = Courrier.query.filter_by(
                    numero_accuse_reception=courrier_data["numero_accuse_reception"]
                ).first()
                
                if existing and skip_existing:
                    result["skipped"] += 1
                    result["details"].append(f"Courrier {courrier_data['numero_accuse_reception']} ignoré (existe déjà)")
                    continue
                
                # Créer un nouveau courrier
                new_courrier = Courrier()
                old_id = courrier_data["id"]
                
                # Copier les champs de base
                new_courrier.numero_accuse_reception = courrier_data["numero_accuse_reception"]
                new_courrier.type_courrier = courrier_data["type_courrier"]
                new_courrier.type_courrier_sortant_id = courrier_data.get("type_courrier_sortant_id")
                new_courrier.statut = courrier_data["statut"]
                new_courrier.secretaire_general_copie = courrier_data.get("secretaire_general_copie")
                new_courrier.fichier_nom = courrier_data.get("fichier_nom")
                new_courrier.fichier_type = courrier_data.get("fichier_type")
                new_courrier.fichier_checksum = courrier_data.get("fichier_checksum")
                new_courrier.autres_informations = courrier_data.get("autres_informations")
                new_courrier.is_deleted = courrier_data.get("is_deleted", False)
                
                # Dates
                if courrier_data.get("date_redaction"):
                    new_courrier.date_redaction = datetime.fromisoformat(courrier_data["date_redaction"])
                if courrier_data.get("date_enregistrement"):
                    new_courrier.date_enregistrement = datetime.fromisoformat(courrier_data["date_enregistrement"])
                if courrier_data.get("date_modification_statut"):
                    new_courrier.date_modification_statut = datetime.fromisoformat(courrier_data["date_modification_statut"])
                if courrier_data.get("deleted_at"):
                    new_courrier.deleted_at = datetime.fromisoformat(courrier_data["deleted_at"])
                
                # Rechiffrer les données sensibles avec la clé de cette instance
                new_courrier.objet = courrier_data.get("objet", "")
                new_courrier.objet_encrypted = encrypt_sensitive_data(courrier_data.get("objet", ""))
                
                if courrier_data.get("expediteur"):
                    new_courrier.expediteur = courrier_data["expediteur"]
                    new_courrier.expediteur_encrypted = encrypt_sensitive_data(courrier_data["expediteur"])
                
                if courrier_data.get("destinataire"):
                    new_courrier.destinataire = courrier_data["destinataire"]
                    new_courrier.destinataire_encrypted = encrypt_sensitive_data(courrier_data["destinataire"])
                
                if courrier_data.get("numero_reference"):
                    new_courrier.numero_reference = courrier_data["numero_reference"]
                    new_courrier.numero_reference_encrypted = encrypt_sensitive_data(courrier_data["numero_reference"])
                
                # Assigner l'utilisateur avec validation et priorité correcte
                from models import User
                
                # Priorité 1: assign_to_user_id (si fourni et valide)
                if assign_to_user_id:
                    user_exists = User.query.filter_by(id=assign_to_user_id, is_deleted=False).first()
                    if user_exists:
                        new_courrier.utilisateur_id = assign_to_user_id
                    else:
                        raise ValueError(f"Utilisateur avec ID {assign_to_user_id} introuvable ou supprimé")
                
                # Priorité 2: utilisateur_id d'origine (si existe dans cette instance)
                elif courrier_data.get("utilisateur_id"):
                    original_user = User.query.filter_by(id=courrier_data["utilisateur_id"], is_deleted=False).first()
                    if original_user:
                        new_courrier.utilisateur_id = courrier_data["utilisateur_id"]
                    elif remap_users and courrier_data["utilisateur_id"] in remap_users:
                        # Priorité 3: mapping fourni
                        new_courrier.utilisateur_id = remap_users[courrier_data["utilisateur_id"]]
                    else:
                        # Priorité 4: super admin par défaut
                        default_user = User.query.filter_by(role='super_admin').first()
                        if default_user:
                            new_courrier.utilisateur_id = default_user.id
                
                # Aucun utilisateur dans les données source
                else:
                    # Priorité 4: super admin par défaut
                    default_user = User.query.filter_by(role='super_admin').first()
                    if default_user:
                        new_courrier.utilisateur_id = default_user.id
                
                # Enregistrer le courrier
                db.session.add(new_courrier)
                db.session.flush()  # Pour obtenir l'ID
                
                # Mapper l'ancien ID au nouveau
                id_mapping[old_id] = new_courrier.id
                
                # Importer les fichiers attachés
                attachments_dir = os.path.join(temp_dir, 'attachments')
                for attachment in import_data["attachments"]:
                    if attachment["courrier_id"] == old_id and attachment["type"] == "main":
                        # Fichier principal
                        source_file = os.path.join(attachments_dir, f"{old_id}_{attachment['filename']}")
                        if os.path.exists(source_file):
                            # Créer le chemin de destination
                            uploads_dir = 'uploads'
                            os.makedirs(uploads_dir, exist_ok=True)
                            dest_file = os.path.join(uploads_dir, f"{new_courrier.id}_{attachment['filename']}")
                            
                            # Rechiffrer le fichier avec la clé de cette instance
                            # Note: Le fichier source est déjà en clair (déchiffré à l'export)
                            if attachment.get("encrypted", False):
                                # Re-chiffrer avec la nouvelle clé
                                encryption_manager.encrypt_file(source_file, dest_file + ".encrypted")
                                new_courrier.fichier_chemin = dest_file + ".encrypted"
                                new_courrier.fichier_encrypted = True
                            else:
                                # Fichier non chiffré, copier tel quel
                                shutil.copy2(source_file, dest_file)
                                new_courrier.fichier_chemin = dest_file
                                new_courrier.fichier_encrypted = False
                        else:
                            # Fichier manquant dans l'export
                            result["details"].append(f"AVERTISSEMENT: Fichier manquant pour courrier {courrier_data['numero_accuse_reception']}: {attachment['filename']}")
                            logging.warning(f"Fichier attaché manquant lors de l'import: {source_file}")
                
                db.session.commit()
                result["imported"] += 1
                result["details"].append(f"Courrier {courrier_data['numero_accuse_reception']} importé avec succès")
                logging.info(f"Courrier importé: {courrier_data['numero_accuse_reception']} (ID: {old_id} -> {new_courrier.id})")
                
            except Exception as e:
                db.session.rollback()
                result["errors"] += 1
                result["details"].append(f"Erreur lors de l'import du courrier {courrier_data.get('numero_accuse_reception', 'inconnu')}: {str(e)}")
                logging.error(f"Erreur lors de l'import: {e}", exc_info=True)
    
    logging.info(f"Import terminé: {result['imported']} importés, {result['skipped']} ignorés, {result['errors']} erreurs")
    return result
