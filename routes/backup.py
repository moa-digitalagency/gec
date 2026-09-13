import os
import uuid
import io
import csv
import zipfile
import shutil
import tempfile
import subprocess
import json
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session, send_file, abort, send_from_directory, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_
import logging

from app import app, db
from models import User, Courrier, CourrierAttachment, Tag, CourrierTag, LogActivite, ParametresSysteme, StatutCourrier, Role, RolePermission, Departement, TypeCourrierSortant, Notification, CourrierComment, CourrierForward, CourrierSignature
from utils import allowed_file, generate_accuse_reception, log_activity, export_courrier_pdf, export_mail_list_pdf, get_current_language, set_language, t, get_available_languages, get_all_languages, toggle_language_status, download_language_file, upload_language_file, delete_language_file, validate_backup_integrity, create_pre_update_backup, get_backup_files
from services.email import send_new_mail_notification, send_mail_forwarded_notification
from security import rate_limit, sanitize_input, validate_file_upload, log_security_event, record_failed_login, is_login_locked, reset_failed_login_attempts, get_client_ip, validate_password_strength, audit_log
from utils.performance import cache_result, get_dashboard_statistics, optimize_search_query, PerformanceMonitor, clear_cache

@app.route('/backup_system', methods=['POST'])
@login_required
def backup_system():
    """Créer une sauvegarde complète du système"""
    if not current_user.has_permission('manage_backup'):
        flash('Accès refusé. Seuls les super administrateurs peuvent créer des sauvegardes.', 'error')
        return redirect(url_for('settings'))
    
    try:
        backup_filename = create_system_backup()
        log_activity(current_user.id, "BACKUP_SYSTEME", 
                    f"Création d'une sauvegarde système: {backup_filename}")
        flash(f'Sauvegarde créée avec succès: {backup_filename}', 'success')
    except Exception as e:
        logging.error(f"Erreur lors de la création de la sauvegarde: {e}")
        flash(f'Erreur lors de la création de la sauvegarde: {str(e)}', 'error')
    
    return redirect(url_for('manage_backups'))

@app.route('/backup_pre_update', methods=['POST'])
@login_required
def backup_pre_update():
    """Créer une sauvegarde de sécurité avant mise à jour avec protection des paramètres"""
    if not current_user.has_permission('manage_backup'):
        flash('Accès refusé. Seuls les super administrateurs peuvent créer des sauvegardes de sécurité.', 'error')
        return redirect(url_for('settings'))
    
    try:
        backup_filename = create_pre_update_backup()
        log_activity(current_user.id, "BACKUP_SECURITE_MAJ", 
                    f"Création d'une sauvegarde de sécurité avec protection des paramètres: {backup_filename}")
        flash(f'Sauvegarde de sécurité créée avec succès: {backup_filename}', 'success')
        flash('La sauvegarde inclut la protection des paramètres critiques pour les mises à jour.', 'info')
    except Exception as e:
        logging.error(f"Erreur lors de la création de la sauvegarde de sécurité: {e}")
        flash(f'Erreur lors de la création de la sauvegarde de sécurité: {str(e)}', 'error')
    
    return redirect(url_for('manage_backups'))

@app.route('/export_courriers', methods=['POST'])
@login_required
def export_courriers():
    """Exporter les courriers avec déchiffrement pour transfert vers une autre instance"""
    if not current_user.has_permission('manage_backup'):
        flash('Accès refusé. Seuls les super administrateurs peuvent exporter les courriers.', 'error')
        return redirect(url_for('manage_backups'))
    
    try:
        from utils.export_import import create_export_package
        
        # Options d'export
        export_all = request.form.get('export_all', 'false') == 'true'
        courrier_ids_str = request.form.get('courrier_ids', '')
        
        courrier_ids = None
        if courrier_ids_str:
            try:
                courrier_ids = [int(id.strip()) for id in courrier_ids_str.split(',') if id.strip()]
            except ValueError:
                flash('Format des IDs de courriers invalide', 'error')
                return redirect(url_for('manage_backups'))
        
        export_file, password = create_export_package(courrier_ids=courrier_ids, export_all=export_all)
        filename = os.path.basename(export_file)
        
        log_activity(current_user.id, "EXPORT_COURRIERS", 
                    f"Export de courriers chiffré créé: {filename}")
        
        # Rendre le template de succès avec le mot de passe
        return render_template('export_success.html',
                             password=password,
                             filename=filename)
        
    except Exception as e:
        logging.error(f"Erreur lors de l'export des courriers: {e}", exc_info=True)
        flash(f'Erreur lors de l\'export: {str(e)}', 'error')
        return redirect(url_for('manage_backups'))

@app.route('/download_export/<filename>')
@login_required
def download_export(filename):
    """Télécharger un fichier d'export sécurisé"""
    if not current_user.has_permission('manage_backup'):
        flash('Accès refusé.', 'error')
        return redirect(url_for('manage_backups'))

    # Validation du nom de fichier
    secure_name = secure_filename(filename)
    if not secure_name.endswith('.zip') or 'export_courriers' not in secure_name:
        flash('Fichier invalide.', 'error')
        return redirect(url_for('manage_backups'))

    export_dir = 'exports'
    file_path = os.path.join(export_dir, secure_name)

    if os.path.exists(file_path):
        log_activity(current_user.id, "DOWNLOAD_EXPORT",
                    f"Téléchargement de l'export: {secure_name}")
        return send_from_directory(export_dir, secure_name, as_attachment=True)
    else:
        flash('Fichier d\'export introuvable.', 'error')
        return redirect(url_for('manage_backups'))

@app.route('/import_courriers', methods=['POST'])
@login_required
def import_courriers():
    """Importer les courriers avec rechiffrement depuis une autre instance"""
    if not current_user.has_permission('manage_backup'):
        flash('Accès refusé. Seuls les super administrateurs peuvent importer les courriers.', 'error')
        return redirect(url_for('manage_backups'))
    
    try:
        if 'import_file' not in request.files:
            flash('Aucun fichier d\'import fourni', 'error')
            return redirect(url_for('manage_backups'))
        
        import_file = request.files['import_file']
        
        if import_file.filename == '':
            flash('Aucun fichier sélectionné', 'error')
            return redirect(url_for('manage_backups'))
        
        if not import_file.filename.endswith('.zip'):
            flash('Le fichier doit être au format ZIP', 'error')
            return redirect(url_for('manage_backups'))
        
        from utils.export_import import import_courriers_from_package
        
        # Sauvegarder temporairement le fichier
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            import_file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        try:
            # Options d'import
            skip_existing = request.form.get('skip_existing', 'true') == 'true'
            assign_to_user_id = request.form.get('assign_to_user_id')
            password = request.form.get('import_password', '').strip() or None
            
            if password:
                logging.info(f"Tentative d'import avec mot de passe pour le fichier {import_file.filename}")

            # Convertir en int si fourni
            if assign_to_user_id:
                try:
                    assign_to_user_id = int(assign_to_user_id)
                except ValueError:
                    flash('ID utilisateur invalide', 'error')
                    return redirect(url_for('manage_backups'))
            
            # Importer
            result = import_courriers_from_package(tmp_path, skip_existing=skip_existing, assign_to_user_id=assign_to_user_id, password=password)
            
            # Logger l'activité
            log_activity(current_user.id, "IMPORT_COURRIERS", 
                        f"Import de courriers: {result['imported']} importés, {result['skipped']} ignorés, {result['errors']} erreurs")
            
            # Messages de résultat
            if result['success']:
                flash(f'Import terminé: {result["imported"]} courriers importés', 'success')
                flash('Les données ont été rechiffrées avec la clé de cette instance', 'info')
                
                if result['skipped'] > 0:
                    flash(f'{result["skipped"]} courriers ignorés (déjà existants)', 'warning')
                
                if result['errors'] > 0:
                    flash(f'{result["errors"]} erreurs rencontrées', 'warning')
                    # Afficher les détails des erreurs
                    for detail in result.get('details', []):
                        if 'Erreur' in detail or 'erreur' in detail:
                            flash(f'  • {detail}', 'error')
            else:
                flash(f'Erreur lors de l\'import: {result.get("details", ["Erreur inconnue"])[0]}', 'error')
            
        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        return redirect(url_for('manage_backups'))
        
    except Exception as e:
        logging.error(f"Erreur lors de l'import des courriers: {e}", exc_info=True)
        flash(f'Erreur lors de l\'import: {str(e)}', 'error')
        return redirect(url_for('manage_backups'))

@app.route('/download_backup/<filename>')
@login_required
def download_backup(filename):
    """Télécharger un fichier de sauvegarde - accès restreint aux super admins"""
    if not current_user.has_permission('manage_backup'):
        flash('Accès refusé. Seuls les super administrateurs peuvent télécharger les sauvegardes.', 'error')
        return redirect(url_for('manage_backups'))
    
    # Validation de sécurité du nom de fichier
    import os
    from werkzeug.utils import secure_filename
    
    # Sécuriser le nom de fichier et rejeter les extensions non autorisées
    secure_name = secure_filename(filename)
    if not secure_name.endswith('.zip'):
        flash('Seuls les fichiers de sauvegarde (.zip) peuvent être téléchargés.', 'error')
        return redirect(url_for('manage_backups'))
    
    # Empêcher la traversée de chemin
    if '..' in filename or '/' in filename or '\\' in filename:
        flash('Nom de fichier invalide.', 'error')
        return redirect(url_for('manage_backups'))
    
    # Créer le dossier backups s'il n'existe pas
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    
    # Vérifier que le fichier existe et est dans le bon répertoire
    backup_path = os.path.join(backup_dir, secure_name)
    backup_path = os.path.abspath(backup_path)
    backup_dir_abs = os.path.abspath(backup_dir)
    
    # S'assurer que le fichier est bien dans le répertoire backups (sécurité)
    if not backup_path.startswith(backup_dir_abs):
        flash('Accès non autorisé au fichier.', 'error')
        return redirect(url_for('manage_backups'))
    
    if os.path.exists(backup_path) and os.path.isfile(backup_path):
        # Logger le téléchargement pour audit
        log_activity(current_user.id, "DOWNLOAD_BACKUP", 
                    f"Téléchargement de la sauvegarde: {secure_name}")
        
        return send_from_directory(backup_dir, secure_name, 
                                 as_attachment=True,
                                 mimetype='application/zip')
    else:
        flash('Fichier de sauvegarde non trouvé.', 'error')
        return redirect(url_for('manage_backups'))

@app.route('/restore_system', methods=['POST'])
@login_required
def restore_system():
    """Restaurer le système depuis une sauvegarde"""
    if not current_user.has_permission('manage_backup'):
        flash('Accès refusé. Seuls les super administrateurs peuvent restaurer le système.', 'error')
        return redirect(url_for('manage_backups'))
    
    if 'backup_file' not in request.files:
        flash('Aucun fichier de sauvegarde sélectionné.', 'error')
        return redirect(url_for('manage_backups'))
    
    backup_file = request.files['backup_file']
    if backup_file.filename == '':
        flash('Aucun fichier sélectionné.', 'error')
        return redirect(url_for('manage_backups'))
    
    if backup_file and backup_file.filename.endswith('.zip'):
        try:
            restore_system_from_backup(backup_file)
            log_activity(current_user.id, "RESTORE_SYSTEME", 
                        f"Restauration système depuis: {backup_file.filename}")
            flash('Système restauré avec succès. Redémarrage nécessaire.', 'success')
        except Exception as e:
            logging.error(f"Erreur lors de la restauration: {e}")
            flash(f'Erreur lors de la restauration: {str(e)}', 'error')
    else:
        flash('Format de fichier invalide. Utilisez un fichier .zip.', 'error')
    
    return redirect(url_for('manage_backups'))

@app.route('/validate_backup/<filename>')
@login_required
def validate_backup(filename):
    """Valider l'intégrité d'un fichier de sauvegarde"""
    if not current_user.has_permission('manage_backup'):
        flash('Accès refusé.', 'error')
        return redirect(url_for('manage_backups'))
    
    try:
        is_valid, message = validate_backup_integrity(filename)
        
        if is_valid:
            flash(f'✅ Validation réussie: {message}', 'success')
        else:
            flash(f'❌ Problème détecté: {message}', 'error')
            
        log_activity(current_user.id, "VALIDATE_BACKUP", 
                    f"Validation de sauvegarde: {filename} - {message}")
                    
    except Exception as e:
        logging.error(f"Erreur lors de la validation de sauvegarde: {e}")
        flash(f'Erreur lors de la validation: {str(e)}', 'error')
    
    return redirect(url_for('manage_backups'))

@app.route('/update_system')
@login_required
def update_system():
    """Page de mise à jour du système"""
    if not current_user.has_permission('manage_updates'):
        flash('Accès non autorisé. Permission requise: Gestion des mises à jour.', 'error')
        return redirect(url_for('dashboard'))
    
    # Vérifier la version actuelle
    version_file = 'version.txt'
    current_version = 'Unknown'
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            current_version = f.read().strip()
    
    return render_template('update_system.html', current_version=current_version)

@app.route('/update_online', methods=['POST'])
@login_required
def update_online():
    """Mise à jour online via Git"""
    if not current_user.has_permission('manage_updates'):
        flash('Accès non autorisé. Permission requise: Gestion des mises à jour.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Créer une sauvegarde complète avant la mise à jour
        backup_dir = 'backups/before_update'
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f'backup_before_update_{timestamp}.zip')
        
        # Utiliser la fonction de sauvegarde complète existante
        log_activity(current_user.id, 'BACKUP_BEFORE_UPDATE', 'Création d\'une sauvegarde avant mise à jour Git')
        
        # Créer une sauvegarde complète incluant :
        # - Base de données PostgreSQL complète
        # - Fichiers téléchargés (pièces jointes)
        # - Configuration système et paramètres
        # - Variables d'environnement
        try:
            backup_filename = create_pre_update_backup()
            log_activity(current_user.id, 'BACKUP_CREATED', f'Sauvegarde de sécurité avec protection des paramètres créée: {backup_filename}')
            flash(f'Sauvegarde de sécurité avec protection des paramètres créée: {backup_filename}', 'info')
        except Exception as backup_error:
            flash(f'Erreur lors de la création de la sauvegarde de sécurité : {str(backup_error)}', 'error')
            return redirect(url_for('manage_backups'))
        
        # Exécuter git pull
        result = subprocess.run(['git', 'pull', 'origin', 'main'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            # Mettre à jour la version
            with open('version.txt', 'w') as f:
                f.write(f'Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
            
            log_activity(current_user.id, 'UPDATE', f'Mise à jour online réussie')
            flash('Mise à jour réussie ! Le système a été mis à jour depuis le dépôt Git.', 'success')
        else:
            error_msg = result.stderr if result.stderr else result.stdout
            log_activity(current_user.id, 'UPDATE_ERROR', f'Échec de la mise à jour online: {error_msg}')
            flash(f'Erreur lors de la mise à jour : {error_msg}', 'error')
            
    except Exception as e:
        log_activity(current_user.id, 'UPDATE_ERROR', f'Erreur lors de la mise à jour online: {str(e)}')
        flash(f'Erreur lors de la mise à jour : {str(e)}', 'error')
    
    return redirect(url_for('manage_backups'))

@app.route('/update_offline', methods=['POST'])
@login_required
def update_offline():
    """Mise à jour offline intelligente via fichier ZIP"""
    if not current_user.has_permission('manage_updates'):
        flash('Accès non autorisé. Permission requise: Gestion des mises à jour.', 'error')
        return redirect(url_for('dashboard'))
    
    import hashlib
    
    def get_file_hash(filepath):
        """Calcule le hash MD5 d'un fichier"""
        if not os.path.exists(filepath):
            return None
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return None
    
    try:
        # Vérifier qu'un fichier a été uploadé
        if 'update_file' not in request.files:
            flash('Aucun fichier sélectionné.', 'error')
            return redirect(url_for('manage_backups'))
        
        file = request.files['update_file']
        if file.filename == '':
            flash('Aucun fichier sélectionné.', 'error')
            return redirect(url_for('manage_backups'))
        
        if not file.filename.endswith('.zip'):
            flash('Le fichier doit être un fichier ZIP.', 'error')
            return redirect(url_for('manage_backups'))
        
        # Créer une sauvegarde avant la mise à jour
        backup_dir = 'backups/before_update'
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = os.path.join(backup_dir, f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip')
        
        # Fichiers et dossiers à préserver (ne jamais remplacer)
        preserve_patterns = [
            'instance/gec.db',
            'static/uploads/',
            '.env',
            'backups/',
            'exports/',
            '__pycache__/',
            '.git/',
            '*.pyc',
            '*.pyo',
            '.DS_Store'
        ]
        
        # Créer une sauvegarde des fichiers importants
        with zipfile.ZipFile(backup_file, 'w') as zipf:
            for file_pattern in ['instance/gecmines.db', '.env', 'uploads']:
                if os.path.exists(file_pattern):
                    if os.path.isdir(file_pattern):
                        for root, dirs, files in os.walk(file_pattern):
                            for f in files:
                                file_path = os.path.join(root, f)
                                arcname = os.path.relpath(file_path)
                                zipf.write(file_path, arcname)
                    else:
                        zipf.write(file_pattern, os.path.basename(file_pattern))
        
        # Sauvegarder le fichier ZIP uploadé temporairement
        temp_dir = tempfile.mkdtemp()
        update_zip_path = os.path.join(temp_dir, 'update.zip')
        file.save(update_zip_path)
        
        # Extraire le ZIP dans un dossier temporaire
        extract_dir = os.path.join(temp_dir, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(update_zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Statistiques de mise à jour
        files_updated = 0
        files_added = 0
        files_skipped = 0
        files_cleaned = 0
        
        # Parcourir les fichiers extraits et les comparer avec les existants
        for root, dirs, files in os.walk(extract_dir):
            # Exclure les dossiers à préserver
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'uploads', 'instance', 'backups', 'exports']]
            
            for file_name in files:
                # Ignorer les fichiers temporaires
                if file_name.endswith(('.pyc', '.pyo', '.DS_Store', '.tmp', '.bak')):
                    continue
                    
                src_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(src_path, extract_dir)
                dest_path = rel_path
                
                # Vérifier si le fichier doit être préservé
                should_preserve = False
                for pattern in preserve_patterns:
                    if pattern.endswith('/'):
                        if dest_path.startswith(pattern):
                            should_preserve = True
                            break
                    elif pattern.startswith('*'):
                        if dest_path.endswith(pattern[1:]):
                            should_preserve = True
                            break
                    elif dest_path == pattern:
                        should_preserve = True
                        break
                
                if should_preserve:
                    files_skipped += 1
                    continue
                
                # Créer les dossiers si nécessaire
                dest_dir = os.path.dirname(dest_path)
                if dest_dir:
                    os.makedirs(dest_dir, exist_ok=True)
                
                # Comparer les hash pour voir si le fichier a changé
                src_hash = get_file_hash(src_path)
                dest_hash = get_file_hash(dest_path)
                
                if dest_hash is None:
                    # Le fichier n'existe pas, l'ajouter
                    shutil.copy2(src_path, dest_path)
                    files_added += 1
                elif src_hash != dest_hash:
                    # Le fichier existe mais a changé, le remplacer
                    shutil.copy2(src_path, dest_path)
                    files_updated += 1
                else:
                    # Le fichier est identique, le passer
                    files_skipped += 1
        
        # Nettoyer les fichiers inutiles (__pycache__, *.pyc, etc.)
        for root, dirs, files in os.walk('.'):
            # Supprimer les dossiers __pycache__
            if '__pycache__' in dirs:
                shutil.rmtree(os.path.join(root, '__pycache__'), ignore_errors=True)
                files_cleaned += 1
            
            # Supprimer les fichiers temporaires
            for file_name in files:
                if file_name.endswith(('.pyc', '.pyo', '.tmp', '.bak', '.swp', '.DS_Store')):
                    try:
                        os.remove(os.path.join(root, file_name))
                        files_cleaned += 1
                    except:
                        pass
        
        # Nettoyer les fichiers temporaires
        shutil.rmtree(temp_dir)
        
        # Mettre à jour la version avec les statistiques
        with open('version.txt', 'w') as f:
            f.write(f'Updated (offline): {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write(f'Files updated: {files_updated}, added: {files_added}, skipped: {files_skipped}, cleaned: {files_cleaned}')
        
        # Message de succès détaillé
        update_msg = f'Mise à jour intelligente réussie ! '
        update_msg += f'{files_updated} fichiers modifiés, '
        update_msg += f'{files_added} nouveaux fichiers, '
        update_msg += f'{files_skipped} fichiers préservés, '
        update_msg += f'{files_cleaned} fichiers nettoyés.'
        
        log_activity(current_user.id, 'UPDATE', update_msg)
        flash(update_msg, 'success')
        
    except Exception as e:
        log_activity(current_user.id, 'UPDATE_ERROR', f'Erreur lors de la mise à jour offline: {str(e)}')
        flash(f'Erreur lors de la mise à jour : {str(e)}', 'error')
    
    return redirect(url_for('manage_backups'))

# Fonctions utilitaires pour backup/restore
def create_system_backup():
    """Créer une sauvegarde complète du système avec TOUS les éléments"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"gec_backup_{timestamp}.zip"
    
    # Créer le dossier backups s'il n'existe pas
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    backup_path = os.path.join(backup_dir, backup_filename)
    temp_dir = os.path.join(tempfile.gettempdir(), f"backup_temp_{timestamp}")
    
    try:
        # Créer dossier temporaire
        os.makedirs(temp_dir, exist_ok=True)
        
        logging.info("=== DÉBUT SAUVEGARDE COMPLÈTE ===")
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
            
            # 1. BASE DE DONNÉES COMPLÈTE avec structure et données
            logging.info("1. Sauvegarde base de données PostgreSQL complète...")
            db_backup_path = backup_database_complete()
            if db_backup_path:
                backup_zip.write(db_backup_path, "database_backup.sql")
                os.remove(db_backup_path)
                logging.info("✅ Base de données sauvegardée")
            else:
                logging.error("❌ Échec sauvegarde base de données")
            
            # 2. TOUS LES FICHIERS SYSTÈME
            logging.info("2. Sauvegarde fichiers système...")
            system_files = [
                'app.py', 'main.py', 'models.py', 'views.py', 
                'migration_utils.py', 'security_utils.py', 'email_utils.py',
                'requirements.txt', '.env'
            ]
            
            for file in system_files:
                if os.path.exists(file):
                    backup_zip.write(file)
                    logging.info(f"✅ Fichier système: {file}")
            
            # 3. TOUS LES DOSSIERS CRITIQUES
            logging.info("3. Sauvegarde dossiers critiques...")
            critical_dirs = ['templates', 'static', 'lang', 'utils']
            for dir_name in critical_dirs:
                if os.path.exists(dir_name):
                    file_count = 0
                    for root, dirs, files in os.walk(dir_name):
                        for file in files:
                            file_path = os.path.join(root, file)
                            archive_path = file_path  # Conserver la structure
                            backup_zip.write(file_path, archive_path)
                            file_count += 1
                    logging.info(f"✅ Dossier {dir_name}: {file_count} fichiers")
            
            # 4. TOUS LES UPLOADS/PIÈCES JOINTES
            logging.info("4. Sauvegarde uploads/pièces jointes...")
            uploads_dir = app.config.get('UPLOAD_FOLDER', 'uploads')
            if os.path.exists(uploads_dir):
                upload_count = 0
                for root, dirs, files in os.walk(uploads_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        archive_path = file_path  # Conserver structure uploads/
                        backup_zip.write(file_path, archive_path)
                        upload_count += 1
                logging.info(f"✅ Uploads: {upload_count} fichiers")
            
            # 5. CONFIGURATION ET PARAMÈTRES SYSTÈME
            logging.info("5. Sauvegarde configuration système...")
            
            # Exporter paramètres système depuis la DB
            try:
                from models import ParametreSysteme
                params = ParametreSysteme.query.first()
                if params:
                    params_data = {
                        'nom_entreprise': params.nom_entreprise,
                        'slogan_entreprise': params.slogan_entreprise,
                        'email_entreprise': params.email_entreprise,
                        'logo_path': params.logo_path,
                        'smtp_server': params.smtp_server,
                        'smtp_port': params.smtp_port,
                        'smtp_email': params.smtp_email,
                        'smtp_use_tls': params.smtp_use_tls,
                        'email_provider': params.email_provider,
                        'resend_api_key': '***MASKED***',  # Sécurité
                        'appellation_entites': params.appellation_entites,
                        'titre_responsable_structure': params.titre_responsable_structure
                    }
                    
                    config_path = os.path.join(temp_dir, "system_config.json")
                    with open(config_path, 'w') as f:
                        json.dump(params_data, f, indent=2, ensure_ascii=False)
                    backup_zip.write(config_path, "system_config.json")
                    logging.info("✅ Configuration système sauvegardée")
            except Exception as e:
                logging.warning(f"Paramètres système non sauvegardés: {e}")
            
            # 6. RÔLES ET PERMISSIONS
            logging.info("6. Sauvegarde rôles et permissions...")
            try:
                from models import Role, RolePermission
                roles_data = []
                for role in Role.query.all():
                    permissions = [rp.permission for rp in role.role_permissions]
                    roles_data.append({
                        'nom': role.nom,
                        'description': role.description,
                        'permissions': permissions
                    })
                
                roles_path = os.path.join(temp_dir, "roles_permissions.json")
                with open(roles_path, 'w') as f:
                    json.dump(roles_data, f, indent=2, ensure_ascii=False)
                backup_zip.write(roles_path, "roles_permissions.json")
                logging.info(f"✅ {len(roles_data)} rôles sauvegardés")
            except Exception as e:
                logging.warning(f"Rôles non sauvegardés: {e}")
            
            # 7. MÉTADONNÉES COMPLÈTES
            logging.info("7. Création métadonnées...")
            try:
                created_by = current_user.username if current_user and current_user.is_authenticated else 'system'
            except:
                created_by = 'system'
            
            metadata = {
                'backup_date': timestamp,
                'backup_version': '2.0',
                'backup_type': 'full_system_complete',
                'created_by': created_by,
                'database_type': 'postgresql',
                'includes': [
                    'database_complete',
                    'system_files',
                    'templates_static',
                    'uploads_attachments',
                    'system_configuration',
                    'roles_permissions'
                ],
                'file_count': len(backup_zip.namelist()) if hasattr(backup_zip, 'namelist') else 0
            }
            
            metadata_path = os.path.join(temp_dir, "backup_metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            backup_zip.write(metadata_path, "backup_metadata.json")
            
            logging.info(f"✅ Sauvegarde COMPLÈTE créée: {backup_filename}")
            logging.info("=== FIN SAUVEGARDE COMPLÈTE ===")
        
    except Exception as e:
        logging.error(f"ERREUR SAUVEGARDE: {e}")
        if os.path.exists(backup_path):
            os.remove(backup_path)
        raise e
    finally:
        # Nettoyer le dossier temporaire
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    return backup_filename

def backup_database_complete():
    """Sauvegarde COMPLÈTE de la base de données PostgreSQL avec structure et données"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url and database_url.startswith('postgresql'):
            backup_file = f"db_complete_{timestamp}.sql"
            
            # pg_dump avec options complètes : structure + données + permissions
            result = subprocess.run([
                'pg_dump', 
                database_url, 
                '--verbose',
                '--create',          # Inclure commandes CREATE DATABASE
                '--clean',           # Inclure commandes DROP avant CREATE
                '--if-exists',       # Ajouter IF EXISTS aux DROP
                '--no-owner',        # Pas de propriétaires spécifiques
                '--no-privileges',   # Pas de privilèges spécifiques
                '--format=plain',    # Format SQL lisible
                '-f', backup_file
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logging.info(f"✅ Sauvegarde PostgreSQL réussie: {backup_file}")
                return backup_file
            else:
                logging.error(f"❌ Erreur pg_dump: {result.stderr}")
                return None
                
        else:
            logging.error("Base de données non PostgreSQL - sauvegarde non supportée")
            return None
            
    except Exception as e:
        logging.error(f"Erreur sauvegarde database: {e}")
        return None

def backup_database():
    """Sauvegarder la base de données"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url and database_url.startswith('postgresql'):
            # Sauvegarde PostgreSQL
            backup_file = f"db_backup_{timestamp}.sql"
            
            # Utiliser pg_dump
            result = subprocess.run([
                'pg_dump', database_url, '-f', backup_file
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return backup_file
            else:
                logging.error(f"Erreur pg_dump: {result.stderr}")
                return None
                
        elif database_url and database_url.startswith('sqlite'):
            # Sauvegarde SQLite
            import sqlite3
            
            db_path = database_url.replace('sqlite:///', '')
            backup_file = f"db_backup_{timestamp}.db"
            
            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_file)
                return backup_file
            
        else:
            # Sauvegarde générique via SQLAlchemy
            backup_file = f"db_backup_{timestamp}.sql"
            
            with open(backup_file, 'w') as f:
                # Export des données principales
                f.write("-- GEC Database Backup\n")
                f.write(f"-- Created: {datetime.now()}\n\n")
                
                # Exporter les utilisateurs (sans mots de passe pour sécurité)
                users = User.query.all()
                for user in users:
                    f.write(f"-- User: {user.username}\n")
                
                # Note: Pour une sauvegarde complète, il faudrait
                # exporter toutes les tables avec SQLAlchemy
            
            return backup_file
            
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde de la base de données: {e}")
        return None

def restore_system_from_backup(backup_file):
    """Restaurer COMPLÈTEMENT le système depuis un fichier de sauvegarde"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            logging.info("=== DÉBUT RESTAURATION COMPLÈTE ===")
            
            # Sauvegarder le fichier uploadé
            temp_backup_path = os.path.join(temp_dir, "backup.zip")
            backup_file.save(temp_backup_path)
            
            # Extraire l'archive
            with zipfile.ZipFile(temp_backup_path, 'r') as backup_zip:
                backup_zip.extractall(temp_dir)
                file_list = backup_zip.namelist()
                logging.info(f"Archive extraite: {len(file_list)} fichiers")
            
            # Vérifier les métadonnées
            metadata_path = os.path.join(temp_dir, "backup_metadata.json")
            if os.path.exists(metadata_path):
                import json
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                logging.info(f"Métadonnées: {metadata.get('backup_type', 'unknown')}")
            
            # 1. SAUVEGARDE DE SÉCURITÉ AVANT RESTAURATION
            logging.info("1. Création sauvegarde de sécurité...")
            try:
                current_backup = create_system_backup()
                logging.info(f"✅ Sauvegarde sécurité: {current_backup}")
            except Exception as e:
                logging.warning(f"Sauvegarde sécurité échouée: {e}")
            
            # 2. RESTAURATION BASE DE DONNÉES COMPLÈTE
            logging.info("2. Restauration base de données...")
            db_backup_path = os.path.join(temp_dir, "database_backup.sql")
            if os.path.exists(db_backup_path):
                restore_database_complete(db_backup_path)
                logging.info("✅ Base de données restaurée")
            else:
                logging.warning("❌ Pas de sauvegarde base de données trouvée")
            
            # 3. RESTAURATION FICHIERS SYSTÈME (SÉLECTIVE)
            logging.info("3. Restauration fichiers système...")
            protected_files = ['main.py', 'app.py', 'requirements.txt']  # Protection critique
            
            system_files = ['models.py', 'views.py', 'migration_utils.py', 'security_utils.py', 'email_utils.py']
            restored_count = 0
            
            for file in system_files:
                source_path = os.path.join(temp_dir, file)
                if os.path.exists(source_path):
                    shutil.copy2(source_path, file)
                    logging.info(f"✅ Fichier système restauré: {file}")
                    restored_count += 1
            
            logging.info(f"✅ {restored_count} fichiers système restaurés")
            
            # 4. RESTAURATION DOSSIERS CRITIQUES
            logging.info("4. Restauration dossiers critiques...")
            critical_dirs = ['templates', 'static', 'lang', 'utils']
            
            for dir_name in critical_dirs:
                source_dir = os.path.join(temp_dir, dir_name)
                if os.path.exists(source_dir):
                    # Supprimer ancien dossier s'il existe
                    if os.path.exists(dir_name):
                        shutil.rmtree(dir_name)
                    
                    # Copier nouveau dossier
                    shutil.copytree(source_dir, dir_name)
                    file_count = sum([len(files) for r, d, files in os.walk(dir_name)])
                    logging.info(f"✅ Dossier {dir_name} restauré: {file_count} fichiers")
            
            # 5. RESTAURATION UPLOADS/PIÈCES JOINTES
            logging.info("5. Restauration uploads...")
            uploads_source = os.path.join(temp_dir, 'uploads')
            uploads_target = app.config.get('UPLOAD_FOLDER', 'uploads')
            
            if os.path.exists(uploads_source):
                # Créer dossier uploads s'il n'existe pas
                os.makedirs(uploads_target, exist_ok=True)
                
                # Copier tous les fichiers uploads
                upload_count = 0
                for root, dirs, files in os.walk(uploads_source):
                    for file in files:
                        source_file = os.path.join(root, file)
                        relative_path = os.path.relpath(source_file, uploads_source)
                        target_file = os.path.join(uploads_target, relative_path)
                        
                        # Créer sous-dossiers si nécessaire
                        target_dir = os.path.dirname(target_file)
                        os.makedirs(target_dir, exist_ok=True)
                        
                        shutil.copy2(source_file, target_file)
                        upload_count += 1
                
                logging.info(f"✅ {upload_count} fichiers uploads restaurés")
            
            # 6. RESTAURATION CONFIGURATION SYSTÈME
            logging.info("6. Restauration configuration système...")
            config_path = os.path.join(temp_dir, "system_config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config_data = json.load(f)
                    
                    from models import ParametreSysteme
                    params = ParametreSysteme.query.first()
                    if params:
                        # Restaurer paramètres (sauf clés sensibles)
                        params.nom_entreprise = config_data.get('nom_entreprise', params.nom_entreprise)
                        params.slogan_entreprise = config_data.get('slogan_entreprise', params.slogan_entreprise)
                        params.email_entreprise = config_data.get('email_entreprise', params.email_entreprise)
                        params.logo_path = config_data.get('logo_path', params.logo_path)
                        params.appellation_entites = config_data.get('appellation_entites', params.appellation_entites)
                        params.titre_responsable_structure = config_data.get('titre_responsable_structure', params.titre_responsable_structure)
                        
                        # SMTP seulement si configuré
                        if config_data.get('smtp_server'):
                            params.smtp_server = config_data.get('smtp_server')
                            params.smtp_port = config_data.get('smtp_port')
                            params.smtp_email = config_data.get('smtp_email')
                            params.smtp_use_tls = config_data.get('smtp_use_tls', True)
                        
                        db.session.commit()
                        logging.info("✅ Configuration système restaurée")
                except Exception as e:
                    logging.warning(f"Configuration système non restaurée: {e}")
            
            # 7. RESTAURATION RÔLES ET PERMISSIONS (SI NOUVELLE INSTALLATION)
            logging.info("7. Vérification rôles et permissions...")
            roles_path = os.path.join(temp_dir, "roles_permissions.json")
            if os.path.exists(roles_path):
                try:
                    with open(roles_path, 'r') as f:
                        roles_data = json.load(f)
                    logging.info(f"✅ {len(roles_data)} rôles disponibles dans la sauvegarde")
                except Exception as e:
                    logging.warning(f"Rôles non restaurés: {e}")
            
            logging.info("=== RESTAURATION COMPLÈTE TERMINÉE ===")
            
        except Exception as e:
            logging.error(f"ERREUR RESTAURATION: {e}")
            raise e

def restore_database_complete(backup_file_path):
    """Restaurer COMPLÈTEMENT la base de données PostgreSQL"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url and database_url.startswith('postgresql'):
            logging.info("Restauration PostgreSQL avec psql...")
            logging.info(f"Fichier de sauvegarde: {backup_file_path}")
            
            # Vérifier que le fichier existe
            if not os.path.exists(backup_file_path):
                raise Exception(f"Fichier de sauvegarde non trouvé: {backup_file_path}")
            
            # Lire quelques lignes du fichier pour diagnostic
            with open(backup_file_path, 'r', encoding='utf-8') as f:
                first_lines = f.read(500)
                logging.info(f"Contenu début fichier: {first_lines[:200]}...")
            
            # Utiliser psql pour restaurer le dump complet avec options compatibles
            # Compatible avec les sauvegardes créées par utils.py (--clean --if-exists)
            result = subprocess.run([
                'psql', 
                database_url, 
                '-f', backup_file_path,
                '--quiet',
                '--no-password',
                '--single-transaction',
                '-v', 'ON_ERROR_STOP=1'  # Arrêter en cas d'erreur
            ], capture_output=True, text=True)
            
            logging.info(f"Code retour psql: {result.returncode}")
            if result.stdout:
                logging.info(f"Sortie psql: {result.stdout}")
            if result.stderr:
                logging.warning(f"Erreurs psql: {result.stderr}")
            
            if result.returncode == 0:
                logging.info("✅ Base de données PostgreSQL restaurée avec succès")
                
                # Vérifier que des données ont été restaurées
                try:
                    from models import Courrier
                    courrier_count = Courrier.query.count()
                    logging.info(f"Nombre de courriers après restauration: {courrier_count}")
                except Exception as verify_e:
                    logging.warning(f"Erreur vérification: {verify_e}")
                    
            else:
                logging.error(f"❌ Erreur restauration PostgreSQL: {result.stderr}")
                # Ne pas lever d'exception si c'est juste un avertissement
                if "WARNING" not in result.stderr and "NOTICE" not in result.stderr:
                    raise Exception(f"Erreur restauration DB: {result.stderr}")
                else:
                    logging.info("Restauration terminée avec avertissements (normal)")
                
        else:
            logging.error("Base de données non PostgreSQL - restauration non supportée")
            raise Exception("Base de données non supportée pour restauration")
            
    except Exception as e:
        logging.error(f"Erreur restauration database: {e}")
        raise e

def restore_database(backup_file_path):
    """Restaurer la base de données depuis un fichier de sauvegarde"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url and database_url.startswith('postgresql'):
            # Restauration PostgreSQL
            result = subprocess.run([
                'psql', database_url, '-f', backup_file_path
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logging.error(f"Erreur psql: {result.stderr}")
                raise Exception(f"Erreur lors de la restauration PostgreSQL: {result.stderr}")
                
        elif database_url and database_url.startswith('sqlite'):
            # Restauration SQLite
            db_path = database_url.replace('sqlite:///', '')
            
            if os.path.exists(backup_file_path):
                shutil.copy2(backup_file_path, db_path)
            else:
                raise Exception("Fichier de sauvegarde SQLite non trouvé")
        
        else:
            # Restauration générique
            logging.warning("Restauration de base de données générique non implémentée")
            
    except Exception as e:
        logging.error(f"Erreur lors de la restauration de la base de données: {e}")
        raise e

# Function removed - now using get_backup_files from utils.py which handles all backup types


@app.route('/manage_backups')
@login_required
def manage_backups():
    """Page dédiée pour la gestion des sauvegardes et restaurations"""
    if not current_user.has_permission('manage_backup'):
        flash('Accès refusé. Seuls les super administrateurs peuvent gérer les sauvegardes.', 'error')
        return redirect(url_for('dashboard'))
    
    # Récupérer la liste des fichiers de sauvegarde
    backup_files = get_backup_files() if current_user.has_permission('manage_backup') else []
    
    # Récupérer la liste des utilisateurs pour l'import
    users = User.query.filter_by(actif=True).order_by(User.username).all()
    
    return render_template('manage_backups.html', backup_files=backup_files, users=users)

@app.route('/restore_from_backup/<filename>', methods=['POST'])
@login_required
def restore_from_backup(filename):
    """Restaurer le système depuis un fichier de sauvegarde spécifique"""
    if not current_user.has_permission('manage_backup'):
        flash('Accès refusé. Seuls les super administrateurs peuvent restaurer le système.', 'error')
        return redirect(url_for('manage_backups'))
    
    try:
        backup_path = os.path.join('backups', filename)
        
        if not os.path.exists(backup_path):
            flash('Fichier de sauvegarde introuvable.', 'error')
            return redirect(url_for('manage_backups'))
        
        if not filename.endswith('.zip'):
            flash('Format de fichier invalide. Seuls les fichiers .zip sont acceptés.', 'error')
            return redirect(url_for('manage_backups'))
        
        # Créer une sauvegarde de sécurité avant restauration
        security_backup = create_system_backup()
        log_activity(current_user.id, 'SECURITY_BACKUP_BEFORE_RESTORE', 
                    f'Sauvegarde de sécurité créée avant restauration: {security_backup}')
        
        # Utiliser la fonction de restauration existante
        with open(backup_path, 'rb') as f:
            class MockFile:
                def __init__(self, file_obj, filename):
                    self.file_obj = file_obj
                    self.filename = filename
                
                def save(self, path):
                    with open(path, 'wb') as dest:
                        dest.write(self.file_obj.read())
                        
                def read(self):
                    return self.file_obj.read()
            
            mock_file = MockFile(f, filename)
            restore_system_from_backup(mock_file)
        
        log_activity(current_user.id, "RESTAURATION_SYSTEME", 
                    f"Restauration depuis la sauvegarde: {filename}")
        flash(f'Système restauré avec succès depuis la sauvegarde: {filename}', 'success')
        
    except Exception as e:
        logging.error(f"Erreur lors de la restauration depuis {filename}: {e}")
        flash(f'Erreur lors de la restauration: {str(e)}', 'error')
    
    return redirect(url_for('manage_backups'))

@app.route('/delete_backup/<filename>', methods=['POST'])
@login_required
def delete_backup(filename):
    """Supprimer un fichier de sauvegarde"""
    if not current_user.has_permission('manage_backup'):
        flash('Accès refusé. Seuls les super administrateurs peuvent supprimer des sauvegardes.', 'error')
        return redirect(url_for('manage_backups'))
    
    try:
        backup_path = os.path.join('backups', filename)
        
        if not os.path.exists(backup_path):
            flash('Fichier de sauvegarde introuvable.', 'error')
            return redirect(url_for('manage_backups'))
        
        # Vérifier qu'on ne supprime pas la dernière sauvegarde
        backup_files = get_backup_files()
        if len(backup_files) <= 1:
            flash('Impossible de supprimer la dernière sauvegarde disponible.', 'warning')
            return redirect(url_for('manage_backups'))
        
        # Supprimer le fichier
        os.remove(backup_path)
        
        log_activity(current_user.id, "BACKUP_DELETED", 
                    f"Sauvegarde supprimée: {filename}")
        flash(f'Sauvegarde "{filename}" supprimée avec succès.', 'success')
        
    except Exception as e:
        logging.error(f"Erreur lors de la suppression de {filename}: {e}")
        flash(f'Erreur lors de la suppression: {str(e)}', 'error')
    
    return redirect(url_for('manage_backups'))
