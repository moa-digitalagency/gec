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

@app.route('/api/users_list')
@login_required
def api_users_list():
    """Retourne la liste des utilisateurs actifs pour l'autocomplete (circuit signature, etc.)"""
    users = User.query.filter_by(actif=True).order_by(User.nom_complet).all()
    return jsonify([{'id': u.id, 'nom_complet': u.nom_complet} for u in users])


@app.route('/manage_users')
@login_required
def manage_users():
    """Gestion des utilisateurs - accessible uniquement aux super admins"""
    if not current_user.can_manage_users():
        flash('Accès refusé. Seuls les super administrateurs peuvent gérer les utilisateurs.', 'error')
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 25
    users = User.query.order_by(User.date_creation.desc()).all()
    pagination = User.query.order_by(User.date_creation.desc()).paginate(page=page, per_page=per_page, error_out=False)
    departements = Departement.get_departements_actifs()
    roles = Role.query.all()
    return render_template('manage_users.html', users=users, pagination=pagination,
                         departements=departements,
                         available_languages=get_available_languages(), roles=roles)

@app.route('/add_user', methods=['GET', 'POST'])
@login_required  
def add_user():
    """Ajouter un nouvel utilisateur"""
    if not current_user.can_manage_users():
        flash('Accès refusé.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        nom_complet = request.form['nom_complet']
        password = request.form['password']
        role = request.form['role']
        langue = request.form['langue']
        matricule = request.form.get('matricule', '').strip()
        fonction = request.form.get('fonction', '').strip()
        departement_id = request.form.get('departement_id') or None
        
        # Vérifier que l'utilisateur n'existe pas déjà
        if User.query.filter_by(username=username).first():
            flash('Ce nom d\'utilisateur existe déjà.', 'error')
            return redirect(url_for('add_user'))
        
        if User.query.filter_by(email=email).first():
            flash('Cette adresse email existe déjà.', 'error')
            return redirect(url_for('add_user'))
        
        # Vérifier l'unicité du matricule si fourni
        if matricule and User.query.filter_by(matricule=matricule).first():
            flash('Ce matricule existe déjà.', 'error')
            return redirect(url_for('add_user'))
        
        # Créer le nouvel utilisateur
        new_user = User(
            username=username,
            email=email,
            nom_complet=nom_complet,
            password_hash=generate_password_hash(password),
            role=role,
            langue=langue,
            matricule=matricule if matricule else None,
            fonction=fonction if fonction else None,
            departement_id=departement_id,
            actif=True
        )
        
        db.session.add(new_user)
        db.session.flush()  # Pour obtenir l'ID du nouvel utilisateur
        
        # Gestion de l'upload de photo de profil
        file = request.files.get('photo_profile')
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ext = filename.rsplit('.', 1)[1].lower()
            filename = f"profile_{new_user.id}_{timestamp}.{ext}"
            
            # Créer le dossier dans static pour que Flask puisse servir les fichiers
            profile_folder = os.path.join('static', 'uploads', 'profiles')
            os.makedirs(profile_folder, exist_ok=True)
            filepath = os.path.join(profile_folder, filename)
            file.save(filepath)
            
            new_user.photo_profile = filename
        
        db.session.commit()
        
        log_activity(current_user.id, "CREATION_UTILISATEUR", 
                    f"Création de l'utilisateur {username} avec le rôle {role}")
        flash(f'Utilisateur {username} créé avec succès!', 'success')
        return redirect(url_for('manage_users'))
    
    departements = Departement.get_departements_actifs()
    # Get all active roles from database
    roles = Role.query.filter_by(actif=True).order_by(Role.nom_affichage).all()
    return render_template('add_user.html', 
                         available_languages=get_available_languages(),
                         departements=departements,
                         roles=roles)

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Modifier un utilisateur"""
    if not current_user.can_manage_users():
        flash('Accès refusé.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.nom_complet = request.form['nom_complet']
        user.role = request.form['role']
        user.langue = request.form['langue']
        user.matricule = request.form.get('matricule', '').strip() or None
        user.fonction = request.form.get('fonction', '').strip() or None
        user.departement_id = request.form.get('departement_id') or None
        user.actif = 'actif' in request.form
        
        # Vérifier l'unicité du matricule si fourni
        if user.matricule:
            existing_user = User.query.filter(User.matricule == user.matricule, User.id != user.id).first()
            if existing_user:
                flash('Ce matricule existe déjà.', 'error')
                return redirect(url_for('edit_user', user_id=user.id))
        
        # Mise à jour du mot de passe si fourni
        password = request.form.get('password')
        if password:
            user.password_hash = generate_password_hash(password)
        
        # Gestion de l'upload de photo de profil
        file = request.files.get('photo_profile')
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ext = filename.rsplit('.', 1)[1].lower()
            filename = f"profile_{user.id}_{timestamp}.{ext}"
            
            # Créer le dossier dans static pour que Flask puisse servir les fichiers
            profile_folder = os.path.join('static', 'uploads', 'profiles')
            os.makedirs(profile_folder, exist_ok=True)
            filepath = os.path.join(profile_folder, filename)
            file.save(filepath)
            
            # Supprimer l'ancienne photo si elle existe
            if user.photo_profile:
                old_file = os.path.join(profile_folder, user.photo_profile)
                if os.path.exists(old_file):
                    os.remove(old_file)
            
            user.photo_profile = filename
        
        db.session.commit()
        
        log_activity(current_user.id, "MODIFICATION_UTILISATEUR", 
                    f"Modification de l'utilisateur {user.username}")
        flash(f'Utilisateur {user.username} modifié avec succès!', 'success')
        return redirect(url_for('manage_users'))
    
    departements = Departement.get_departements_actifs()
    # Get all active roles from database
    roles = Role.query.filter_by(actif=True).order_by(Role.nom_affichage).all()
    return render_template('edit_user.html', user=user, 
                         available_languages=get_available_languages(),
                         departements=departements,
                         roles=roles)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Supprimer un utilisateur"""
    if not current_user.can_manage_users():
        flash('Accès refusé.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Empêcher la suppression de son propre compte
    if user.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'error')
        return redirect(url_for('manage_users'))
    
    # Empêcher la suppression du dernier super admin
    if user.role == 'super_admin':
        super_admins = User.query.filter_by(role='super_admin').count()
        if super_admins <= 1:
            flash('Impossible de supprimer le dernier super administrateur.', 'error')
            return redirect(url_for('manage_users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    log_activity(current_user.id, "SUPPRESSION_UTILISATEUR", 
                f"Suppression de l'utilisateur {username}")
    flash(f'Utilisateur {username} supprimé avec succès!', 'success')
    return redirect(url_for('manage_users'))

