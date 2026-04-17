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

@app.route('/upload_profile_photo', methods=['POST'])
@login_required
def upload_profile_photo():
    """Upload d'une photo de profil"""
    if 'photo' not in request.files:
        flash('Aucun fichier sélectionné.', 'error')
        return redirect(url_for('dashboard'))
    
    file = request.files['photo']
    if file.filename == '':
        flash('Aucun fichier sélectionné.', 'error')
        return redirect(url_for('dashboard'))
    
    if file and file.filename and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = filename.rsplit('.', 1)[1].lower()
        filename = f"profile_{current_user.id}_{timestamp}.{ext}"
        
        profile_folder = os.path.join('uploads', 'profiles')
        os.makedirs(profile_folder, exist_ok=True)
        filepath = os.path.join(profile_folder, filename)
        file.save(filepath)
        
        if current_user.photo_profile:
            old_file = os.path.join(profile_folder, current_user.photo_profile)
            if os.path.exists(old_file):
                os.remove(old_file)
        
        current_user.photo_profile = filename
        db.session.commit()
        
        log_activity(current_user.id, "UPLOAD_PHOTO_PROFIL", 
                    "Upload d'une nouvelle photo de profil")
        flash('Photo de profil mise à jour avec succès!', 'success')
    else:
        flash('Type de fichier non autorisé.', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/profile')
@login_required
def profile():
    """Afficher le profil de l'utilisateur actuel"""
    return render_template('profile.html', user=current_user,
                         available_languages=get_available_languages())

@app.route('/update_notification_prefs', methods=['POST'])
@login_required
def update_notification_prefs():
    """Mettre à jour les préférences de notifications par email de l'utilisateur"""
    current_user.notif_enabled   = bool(request.form.get('notif_enabled'))
    current_user.notif_new_mail  = bool(request.form.get('notif_new_mail'))
    current_user.notif_forwarded = bool(request.form.get('notif_forwarded'))
    current_user.notif_status    = bool(request.form.get('notif_status'))
    current_user.notif_deadline  = bool(request.form.get('notif_deadline'))
    current_user.notif_commented = bool(request.form.get('notif_commented'))
    digest = request.form.get('notif_digest', 'instant')
    if digest not in ('instant', 'daily', 'weekly'):
        digest = 'instant'
    current_user.notif_digest = digest
    try:
        db.session.commit()
        log_activity(current_user.id, "PREFS_NOTIFICATIONS", "Préférences de notifications email mises à jour")
        flash('Préférences de notifications enregistrées.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la sauvegarde.', 'error')
    return redirect(url_for('profile'))

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Modifier le profil de l'utilisateur actuel"""
    if request.method == 'POST':
        # Mise à jour des informations de base
        current_user.nom_complet = request.form['nom_complet']
        current_user.langue = request.form['langue']
        
        # Seuls les super admins peuvent modifier email, département, matricule et fonction
        if current_user.is_super_admin():
            current_user.email = request.form['email']
            current_user.matricule = request.form.get('matricule', '')
            current_user.fonction = request.form.get('fonction', '')
            current_user.departement_id = request.form.get('departement_id') or None
        
        # Mise à jour du mot de passe si fourni
        password = request.form.get('password')
        if password:
            current_user.password_hash = generate_password_hash(password)
        
        # Gestion de l'upload de photo de profil
        file = request.files.get('photo_profile')
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ext = filename.rsplit('.', 1)[1].lower()
            filename = f"profile_{current_user.id}_{timestamp}.{ext}"
            
            # Créer le dossier dans static pour que Flask puisse servir les fichiers
            profile_folder = os.path.join('static', 'uploads', 'profiles')
            os.makedirs(profile_folder, exist_ok=True)
            filepath = os.path.join(profile_folder, filename)
            file.save(filepath)
            
            # Supprimer l'ancienne photo si elle existe
            if current_user.photo_profile:
                old_file = os.path.join(profile_folder, current_user.photo_profile)
                if os.path.exists(old_file):
                    os.remove(old_file)
            
            current_user.photo_profile = filename
        
        try:
            db.session.commit()
            log_activity(current_user.id, "MODIFICATION_PROFIL", f"Profil modifié par {current_user.username}")
            flash('Profil mis à jour avec succès!', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour du profil: {str(e)}', 'error')
    
    # Récupérer les départements pour le formulaire
    departements = Departement.get_departements_actifs()
    return render_template('edit_profile.html', user=current_user, 
                         departements=departements,
                         available_languages=get_available_languages())

