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

@app.route('/manage_statuses', methods=['GET', 'POST'])
@login_required
def manage_statuses():
    # Vérifier les permissions d'accès à la gestion des statuts
    if not (current_user.has_permission('manage_statuses') or current_user.is_super_admin()):
        flash('Vous n\'avez pas les permissions pour gérer les statuts.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            nom = request.form.get('nom', '').strip().upper()
            description = request.form.get('description', '').strip()
            couleur = request.form.get('couleur', 'bg-gray-100 text-gray-800')
            ordre = int(request.form.get('ordre', 0))
            
            if nom:
                existing = StatutCourrier.query.filter_by(nom=nom).first()
                if not existing:
                    statut = StatutCourrier(
                        nom=nom,
                        description=description,
                        couleur=couleur,
                        ordre=ordre
                    )
                    db.session.add(statut)
                    db.session.commit()
                    flash(f'Statut "{nom}" ajouté avec succès!', 'success')
                else:
                    flash(f'Le statut "{nom}" existe déjà.', 'error')
        
        elif action == 'update':
            statut_id = request.form.get('statut_id')
            statut = StatutCourrier.query.get(statut_id)
            if statut:
                statut.description = request.form.get('description', '').strip()
                statut.couleur = request.form.get('couleur', 'bg-gray-100 text-gray-800')
                statut.ordre = int(request.form.get('ordre', 0))
                statut.actif = request.form.get('actif') == 'on'
                db.session.commit()
                flash(f'Statut "{statut.nom}" mis à jour!', 'success')
        
        elif action == 'delete':
            statut_id = request.form.get('statut_id')
            statut = StatutCourrier.query.get(statut_id)
            if statut:
                # Vérifier s'il y a des courriers avec ce statut
                courriers_count = Courrier.query.filter_by(statut=statut.nom).count()
                if courriers_count > 0:
                    flash(f'Impossible de supprimer le statut "{statut.nom}": {courriers_count} courrier(s) l\'utilisent encore.', 'error')
                else:
                    db.session.delete(statut)
                    db.session.commit()
                    flash(f'Statut "{statut.nom}" supprimé!', 'success')
    
    statuts = StatutCourrier.query.order_by(StatutCourrier.ordre).all()
    couleurs_disponibles = [
        ('bg-blue-100 text-blue-800', 'Bleu'),
        ('bg-green-100 text-green-800', 'Vert'),
        ('bg-yellow-100 text-yellow-800', 'Jaune'),
        ('bg-red-100 text-red-800', 'Rouge'),
        ('bg-purple-100 text-purple-800', 'Violet'),
        ('bg-gray-100 text-gray-800', 'Gris'),
        ('bg-indigo-100 text-indigo-800', 'Indigo'),
        ('bg-pink-100 text-pink-800', 'Rose')
    ]
    
    return render_template('manage_statuses.html', 
                          statuts=statuts,
                          couleurs_disponibles=couleurs_disponibles)

@app.route('/manage_roles')
@login_required
def manage_roles():
    """Gestion des rôles et permissions - accessible uniquement aux super admins"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    # S'assurer que les données par défaut sont initialisées
    from models import init_default_data
    init_default_data()
    
    # Récupérer les rôles depuis la base de données
    roles = Role.query.order_by(Role.date_creation).all()
    
    # Préparer les données des rôles avec leurs permissions
    roles_data = {}
    for role in roles:
        roles_data[role.nom] = {
            'id': role.id,
            'name': role.nom_affichage,
            'description': role.description,
            'permissions': role.get_permissions_list(),
            'color': role.couleur,
            'icon': role.icone,
            'modifiable': role.modifiable,
            'count': User.query.filter_by(role=role.nom).count()
        }
    
    # Définition de toutes les permissions disponibles
    all_permissions = {
        'manage_users': {
            'name': 'Gérer les utilisateurs',
            'description': 'Créer, modifier et supprimer des comptes utilisateur',
            'category': 'Administration'
        },
        'manage_roles': {
            'name': 'Gérer les rôles',
            'description': 'Modifier les permissions des rôles utilisateur',
            'category': 'Administration'
        },
        'manage_system_settings': {
            'name': 'Paramètres système',
            'description': 'Configurer les paramètres généraux du système',
            'category': 'Configuration'
        },
        'view_all_logs': {
            'name': 'Consulter les logs',
            'description': 'Accéder aux journaux d\'activité du système',
            'category': 'Surveillance'
        },
        'manage_statuses': {
            'name': 'Gérer les statuts',
            'description': 'Créer et modifier les statuts de courrier',
            'category': 'Configuration'
        },
        'register_mail': {
            'name': 'Enregistrer courriers',
            'description': 'Créer de nouveaux enregistrements de courrier',
            'category': 'Courrier'
        },
        'view_mail': {
            'name': 'Consulter courriers',
            'description': 'Voir et accéder aux courriers enregistrés',
            'category': 'Courrier'
        },
        'search_mail': {
            'name': 'Rechercher courriers',
            'description': 'Effectuer des recherches dans les courriers',
            'category': 'Courrier'
        },
        'export_data': {
            'name': 'Exporter données',
            'description': 'Exporter les courriers en PDF et autres formats',
            'category': 'Courrier'
        },
        'delete_mail': {
            'name': 'Supprimer courriers',
            'description': 'Supprimer définitivement des courriers',
            'category': 'Courrier'
        },
        'view_trash': {
            'name': 'Accéder à la corbeille',
            'description': 'Voir les courriers supprimés dans la corbeille',
            'category': 'Courrier'
        },
        'restore_mail': {
            'name': 'Restaurer courriers',
            'description': 'Restaurer des courriers depuis la corbeille',
            'category': 'Courrier'
        },
        'read_all_mail': {
            'name': 'Lire tous les courriers',
            'description': 'Accès complet à tous les courriers du système',
            'category': 'Accès Courrier'
        },
        'read_department_mail': {
            'name': 'Lire courriers du département',
            'description': 'Accès aux courriers du département uniquement',
            'category': 'Accès Courrier'
        },
        'read_own_mail': {
            'name': 'Lire ses propres courriers',
            'description': 'Accès uniquement aux courriers enregistrés par soi-même',
            'category': 'Accès Courrier'
        },
        'edit_all_mail': {
            'name': 'Modifier tous les courriers',
            'description': 'Modifier n\'importe quel courrier du système',
            'category': 'Édition Courrier'
        },
        'edit_department_mail': {
            'name': 'Modifier les courriers du département',
            'description': 'Modifier les courriers de son département uniquement',
            'category': 'Édition Courrier'
        },
        'edit_own_mail': {
            'name': 'Modifier ses propres courriers',
            'description': 'Modifier uniquement les courriers enregistrés par soi-même',
            'category': 'Édition Courrier'
        },
        'manage_updates': {
            'name': 'Gérer les mises à jour système',
            'description': 'Effectuer des mises à jour en ligne ou hors ligne du système',
            'category': 'Administration'
        },
        'manage_backup': {
            'name': 'Gérer les sauvegardes',
            'description': 'Créer et restaurer des sauvegardes du système',
            'category': 'Administration'
        }
    }
    
    return render_template('manage_roles.html',
                         roles_permissions=roles_data,
                         all_permissions=all_permissions,
                         roles=roles)

@app.route('/add_role', methods=['GET', 'POST'])
@login_required
def add_role():
    """Ajouter un nouveau rôle"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        nom = request.form['nom'].strip().lower().replace(' ', '_')
        nom_affichage = request.form['nom_affichage'].strip()
        description = request.form['description'].strip()
        couleur = request.form['couleur']
        icone = request.form['icone']
        permissions = request.form.getlist('permissions')
        
        # Vérifier que le rôle n'existe pas déjà
        if Role.query.filter_by(nom=nom).first():
            flash('Ce nom de rôle existe déjà.', 'error')
            return redirect(url_for('add_role'))

        # Un rôle doit obligatoirement avoir au moins une action assignée
        if not permissions:
            flash('Un rôle doit avoir au moins une action assignée.', 'error')
            return redirect(url_for('add_role'))

        try:
            # Créer le nouveau rôle
            nouveau_role = Role(
                nom=nom,
                nom_affichage=nom_affichage,
                description=description,
                couleur=couleur,
                icone=icone,
                cree_par_id=current_user.id
            )
            db.session.add(nouveau_role)
            db.session.flush()  # Pour obtenir l'ID
            
            # Ajouter les permissions
            for perm in permissions:
                role_permission = RolePermission(
                    role_id=nouveau_role.id,
                    permission_nom=perm,
                    accorde_par_id=current_user.id
                )
                db.session.add(role_permission)
            
            db.session.commit()
            log_activity(current_user.id, "CREATION_ROLE", 
                        f"Création du rôle {nom_affichage}")
            flash(f'Rôle "{nom_affichage}" créé avec succès!', 'success')
            return redirect(url_for('manage_roles'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création du rôle: {str(e)}', 'error')
    
    # Définir les permissions disponibles
    all_permissions = {
        'manage_users': 'Gérer les utilisateurs',
        'manage_roles': 'Gérer les rôles',
        'manage_system_settings': 'Paramètres système',
        'view_all_logs': 'Consulter les logs',
        'view_security_logs': 'Consulter logs de sécurité',
        'manage_security_settings': 'Gérer paramètres de sécurité',
        'manage_statuses': 'Gérer les statuts',
        'register_mail': 'Enregistrer courriers',
        'view_mail': 'Consulter courriers',
        'search_mail': 'Rechercher courriers',
        'export_data': 'Exporter données',
        'delete_mail': 'Supprimer courriers',
        'view_trash': 'Accéder à la corbeille',
        'restore_mail': 'Restaurer courriers supprimés',
        'read_all_mail': 'Lire tous les courriers',
        'read_department_mail': 'Lire courriers du département',
        'read_own_mail': 'Lire ses propres courriers',
        'edit_all_mail': 'Modifier tous les courriers',
        'edit_department_mail': 'Modifier les courriers du département',
        'edit_own_mail': 'Modifier ses propres courriers',
        'manage_updates': 'Gérer les mises à jour système',
        'manage_backup': 'Gérer les sauvegardes'
    }
    
    couleurs_disponibles = [
        ('bg-blue-100 text-blue-800', 'Bleu'),
        ('bg-green-100 text-green-800', 'Vert'),
        ('bg-yellow-100 text-yellow-800', 'Jaune'),
        ('bg-red-100 text-red-800', 'Rouge'),
        ('bg-purple-100 text-purple-800', 'Violet'),
        ('bg-gray-100 text-gray-800', 'Gris'),
        ('bg-indigo-100 text-indigo-800', 'Indigo'),
        ('bg-pink-100 text-pink-800', 'Rose')
    ]
    
    return render_template('add_role.html',
                         all_permissions=all_permissions,
                         couleurs_disponibles=couleurs_disponibles)

@app.route('/edit_role/<int:role_id>', methods=['GET', 'POST'])
@login_required
def edit_role(role_id):
    """Modifier un rôle existant"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    role = Role.query.get_or_404(role_id)
    
    # Vérifier si le rôle est modifiable
    if not role.modifiable:
        flash('Ce rôle système ne peut pas être modifié.', 'error')
        return redirect(url_for('manage_roles'))
    
    if request.method == 'POST':
        role.nom_affichage = request.form['nom_affichage'].strip()
        role.description = request.form['description'].strip()
        role.couleur = request.form['couleur']
        role.icone = request.form['icone']
        role.actif = 'actif' in request.form
        
        permissions = request.form.getlist('permissions')

        # Un rôle doit obligatoirement avoir au moins une action assignée
        if not permissions:
            flash('Un rôle doit avoir au moins une action assignée.', 'error')
            return redirect(url_for('edit_role', role_id=role.id))

        try:
            # Supprimer les anciennes permissions
            RolePermission.query.filter_by(role_id=role.id).delete()
            
            # Ajouter les nouvelles permissions
            for perm in permissions:
                role_permission = RolePermission(
                    role_id=role.id,
                    permission_nom=perm,
                    accorde_par_id=current_user.id
                )
                db.session.add(role_permission)
            
            db.session.commit()
            log_activity(current_user.id, "MODIFICATION_ROLE", 
                        f"Modification du rôle {role.nom_affichage}")
            flash(f'Rôle "{role.nom_affichage}" modifié avec succès!', 'success')
            return redirect(url_for('manage_roles'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification: {str(e)}', 'error')
    
    # Définir les permissions disponibles
    all_permissions = {
        'manage_users': 'Gérer les utilisateurs',
        'manage_roles': 'Gérer les rôles',
        'manage_system_settings': 'Paramètres système',
        'view_all_logs': 'Consulter les logs',
        'view_security_logs': 'Consulter logs de sécurité',
        'manage_security_settings': 'Gérer paramètres de sécurité',
        'manage_statuses': 'Gérer les statuts',
        'register_mail': 'Enregistrer courriers',
        'view_mail': 'Consulter courriers',
        'search_mail': 'Rechercher courriers',
        'export_data': 'Exporter données',
        'delete_mail': 'Supprimer courriers',
        'view_trash': 'Accéder à la corbeille',
        'restore_mail': 'Restaurer courriers supprimés',
        'read_all_mail': 'Lire tous les courriers',
        'read_department_mail': 'Lire courriers du département',
        'read_own_mail': 'Lire ses propres courriers',
        'edit_all_mail': 'Modifier tous les courriers',
        'edit_department_mail': 'Modifier les courriers du département',
        'edit_own_mail': 'Modifier ses propres courriers',
        'manage_updates': 'Gérer les mises à jour système',
        'manage_backup': 'Gérer les sauvegardes'
    }
    
    couleurs_disponibles = [
        ('bg-blue-100 text-blue-800', 'Bleu'),
        ('bg-green-100 text-green-800', 'Vert'),
        ('bg-yellow-100 text-yellow-800', 'Jaune'),
        ('bg-red-100 text-red-800', 'Rouge'),
        ('bg-purple-100 text-purple-800', 'Violet'),
        ('bg-gray-100 text-gray-800', 'Gris'),
        ('bg-indigo-100 text-indigo-800', 'Indigo'),
        ('bg-pink-100 text-pink-800', 'Rose')
    ]
    
    return render_template('edit_role.html',
                         role=role,
                         all_permissions=all_permissions,
                         role_permissions=role.get_permissions_list(),
                         couleurs_disponibles=couleurs_disponibles)

@app.route('/delete_role/<int:role_id>', methods=['POST'])
@login_required
def delete_role(role_id):
    """Supprimer un rôle"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    role = Role.query.get_or_404(role_id)
    
    # Vérifier si le rôle est modifiable
    if not role.modifiable:
        flash('Ce rôle système ne peut pas être supprimé.', 'error')
        return redirect(url_for('manage_roles'))
    
    # Vérifier s'il y a des utilisateurs avec ce rôle
    users_count = User.query.filter_by(role=role.nom).count()
    if users_count > 0:
        flash(f'Impossible de supprimer le rôle "{role.nom_affichage}": {users_count} utilisateur(s) l\'utilisent encore.', 'error')
        return redirect(url_for('manage_roles'))
    
    try:
        nom_role = role.nom_affichage
        db.session.delete(role)
        db.session.commit()
        log_activity(current_user.id, "SUPPRESSION_ROLE", 
                    f"Suppression du rôle {nom_role}")
        flash(f'Rôle "{nom_role}" supprimé avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'error')
    
    return redirect(url_for('manage_roles'))

@app.route('/manage_departments')
@login_required
def manage_departments():
    """Gestion des départements - accessible uniquement aux super admins"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    departements = Departement.query.order_by(Departement.nom).all()
    return render_template('manage_departments.html', 
                         departements=departements)

@app.route('/add_department', methods=['GET', 'POST'])
@login_required
def add_department():
    """Ajouter un nouveau département"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        nom = request.form['nom'].strip()
        code = request.form['code'].strip().upper()
        description = request.form['description'].strip()
        chef_departement_id = request.form.get('chef_departement_id') or None
        
        try:
            nouveau_departement = Departement(
                nom=nom,
                code=code,
                description=description,
                chef_departement_id=chef_departement_id
            )
            db.session.add(nouveau_departement)
            db.session.commit()
            
            # Récupérer l'appellation pour le message
            parametres = ParametresSysteme.get_parametres()
            appellation = (parametres.appellation_departement or 'Départements')[:-1]
            
            log_activity(current_user.id, "CREATION_DEPARTEMENT", 
                        f"Création du département {nom}")
            flash(f'{appellation} "{nom}" créé avec succès!', 'success')
            return redirect(url_for('manage_departments'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création: {str(e)}', 'error')
    
    users = User.query.filter_by(actif=True).order_by(User.nom_complet).all()
    return render_template('add_department.html', users=users)

@app.route('/edit_department/<int:dept_id>', methods=['GET', 'POST'])
@login_required
def edit_department(dept_id):
    """Modifier un département"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    departement = Departement.query.get_or_404(dept_id)
    
    if request.method == 'POST':
        nom = request.form['nom'].strip()
        code = request.form['code'].strip().upper()
        
        # Récupérer l'appellation pour les messages
        parametres = ParametresSysteme.get_parametres()
        appellation = (parametres.appellation_departement or 'Départements')[:-1].lower()
        
        # Vérifier les doublons (sauf pour ce département)
        if Departement.query.filter(Departement.nom == nom, Departement.id != dept_id).first():
            flash(f'Ce nom de {appellation} existe déjà.', 'error')
            return redirect(url_for('edit_department', dept_id=dept_id))
        
        if Departement.query.filter(Departement.code == code, Departement.id != dept_id).first():
            flash(f'Ce code de {appellation} existe déjà.', 'error')
            return redirect(url_for('edit_department', dept_id=dept_id))
        
        try:
            departement.nom = nom
            departement.code = code
            departement.description = request.form['description'].strip()
            departement.chef_departement_id = request.form.get('chef_departement_id') or None
            departement.actif = 'actif' in request.form
            
            db.session.commit()
            log_activity(current_user.id, "MODIFICATION_DEPARTEMENT", 
                        f"Modification du département {nom}")
            
            # Récupérer l'appellation pour le message
            parametres = ParametresSysteme.get_parametres()
            appellation = (parametres.appellation_departement or 'Départements')[:-1]
            flash(f'{appellation} "{nom}" modifié avec succès!', 'success')
            return redirect(url_for('manage_departments'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification: {str(e)}', 'error')
    
    users = User.query.filter_by(actif=True).order_by(User.nom_complet).all()
    return render_template('edit_department.html', departement=departement, users=users)

@app.route('/delete_department/<int:dept_id>', methods=['POST'])
@login_required
def delete_department(dept_id):
    """Supprimer un département"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    departement = Departement.query.get_or_404(dept_id)
    
    # Récupérer l'appellation pour les messages
    parametres = ParametresSysteme.get_parametres()
    appellation = (parametres.appellation_departement or 'Départements')[:-1].lower()
    
    # Vérifier si des utilisateurs sont assignés à ce département
    users_count = User.query.filter_by(departement_id=dept_id).count()
    if users_count > 0:
        flash(f'Impossible de supprimer ce {appellation}. {users_count} utilisateur(s) y sont assignés.', 'error')
        return redirect(url_for('manage_departments'))
    
    try:
        nom = departement.nom
        db.session.delete(departement)
        db.session.commit()
        
        log_activity(current_user.id, "SUPPRESSION_DEPARTEMENT", 
                    f"Suppression du département {nom}")
        
        # Récupérer l'appellation pour le message
        parametres = ParametresSysteme.get_parametres()
        appellation = (parametres.appellation_departement or 'Départements')[:-1]
        flash(f'{appellation} "{nom}" supprimé avec succès!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'error')
    
    return redirect(url_for('manage_departments'))

@app.route('/manage_outgoing_types')
@login_required
def manage_outgoing_types():
    """Page de gestion des types de courrier sortant"""
    if not (current_user.is_super_admin() or current_user.has_permission('manage_system_settings')):
        flash(t('access_denied') or 'Accès refusé.', 'error')
        return redirect(url_for('dashboard'))
    
    from models import TypeCourrierSortant
    types = TypeCourrierSortant.query.order_by(TypeCourrierSortant.ordre_affichage, TypeCourrierSortant.nom).all()
    return render_template('manage_outgoing_types.html', types=types)

@app.route('/add_outgoing_type', methods=['POST'])
@login_required
def add_outgoing_type():
    """Ajouter un nouveau type de courrier sortant"""
    if not (current_user.is_super_admin() or current_user.has_permission('manage_system_settings')):
        flash(t('access_denied') or 'Accès refusé.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from models import TypeCourrierSortant
        
        nom = request.form.get('nom', '').strip()
        description = request.form.get('description', '').strip()
        ordre_affichage = request.form.get('ordre_affichage', 0)
        
        if not nom:
            flash(t('name_required') or 'Le nom est obligatoire.', 'error')
            return redirect(url_for('manage_outgoing_types'))
        
        # Vérifier si le nom existe déjà
        existing = TypeCourrierSortant.query.filter_by(nom=nom).first()
        if existing:
            flash(t('type_name_exists') or 'Un type avec ce nom existe déjà.', 'error')
            return redirect(url_for('manage_outgoing_types'))
        
        # Créer le nouveau type
        nouveau_type = TypeCourrierSortant(
            nom=nom,
            description=description if description else None,
            ordre_affichage=int(ordre_affichage) if ordre_affichage else 0,
            cree_par_id=current_user.id
        )
        
        db.session.add(nouveau_type)
        db.session.commit()
        
        log_activity(current_user.id, "TYPE_SORTANT_AJOUTE", 
                    f"Type de courrier sortant ajouté: {nom}")
        
        flash(t('type_added_successfully') or f'Type "{nom}" ajouté avec succès.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de l'ajout du type: {e}")
        flash(t('error_adding_type') or 'Erreur lors de l\'ajout du type.', 'error')
    
    return redirect(url_for('manage_outgoing_types'))

@app.route('/edit_outgoing_type/<int:type_id>', methods=['GET', 'POST'])
@login_required
def edit_outgoing_type(type_id):
    """Modifier un type de courrier sortant"""
    if not (current_user.is_super_admin() or current_user.has_permission('manage_system_settings')):
        flash('Accès refusé.', 'error')
        return redirect(url_for('dashboard'))
    
    from models import TypeCourrierSortant
    type_courrier = TypeCourrierSortant.query.get_or_404(type_id)
    
    if request.method == 'POST':
        try:
            nom = request.form.get('nom', '').strip()
            description = request.form.get('description', '').strip()
            ordre_affichage = request.form.get('ordre_affichage', 0)
            
            if not nom:
                flash('Le nom est obligatoire.', 'error')
                return redirect(url_for('edit_outgoing_type', type_id=type_id))
            
            # Vérifier si le nom existe déjà (autre que le type actuel)
            existing = TypeCourrierSortant.query.filter(
                TypeCourrierSortant.nom == nom,
                TypeCourrierSortant.id != type_id
            ).first()
            if existing:
                flash('Un type avec ce nom existe déjà.', 'error')
                return redirect(url_for('edit_outgoing_type', type_id=type_id))
            
            # Mettre à jour le type
            ancien_nom = type_courrier.nom
            type_courrier.nom = nom
            type_courrier.description = description if description else None
            type_courrier.ordre_affichage = int(ordre_affichage) if ordre_affichage else 0
            
            db.session.commit()
            
            log_activity(current_user.id, "TYPE_SORTANT_MODIFIE", 
                        f"Type de courrier sortant modifié: {ancien_nom} -> {nom}")
            
            flash(f'Type "{nom}" modifié avec succès.', 'success')
            return redirect(url_for('manage_outgoing_types'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la modification du type: {e}")
            flash('Erreur lors de la modification du type.', 'error')
    
    return render_template('edit_outgoing_type.html', type_courrier=type_courrier)

@app.route('/toggle_outgoing_type_status/<int:type_id>', methods=['POST'])
@login_required
def toggle_outgoing_type_status(type_id):
    """Activer/désactiver un type de courrier sortant"""
    if not (current_user.is_super_admin() or current_user.has_permission('manage_system_settings')):
        flash(t('access_denied') or 'Accès refusé.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from models import TypeCourrierSortant
        type_courrier = TypeCourrierSortant.query.get_or_404(type_id)
        
        ancien_statut = type_courrier.actif
        type_courrier.actif = not type_courrier.actif
        
        db.session.commit()
        
        nouveau_statut = "activé" if type_courrier.actif else "désactivé"
        log_activity(current_user.id, "TYPE_SORTANT_STATUT_CHANGE", 
                    f"Type {type_courrier.nom} {nouveau_statut}")
        
        flash(t('status_changed_successfully') or f'Statut du type "{type_courrier.nom}" modifié avec succès.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors du changement de statut: {e}")
        flash(t('error_changing_status') or 'Erreur lors du changement de statut.', 'error')
    
    return redirect(url_for('manage_outgoing_types'))

@app.route('/delete_outgoing_type/<int:type_id>', methods=['POST'])
@login_required
def delete_outgoing_type(type_id):
    """Supprimer un type de courrier sortant"""
    if not (current_user.is_super_admin() or current_user.has_permission('manage_system_settings')):
        flash(t('access_denied') or 'Accès refusé.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from models import TypeCourrierSortant
        type_courrier = TypeCourrierSortant.query.get_or_404(type_id)
        
        # Vérifier si le type est utilisé
        if type_courrier.courriers.count() > 0:
            flash(t('cannot_delete_used_type') or 'Impossible de supprimer un type utilisé par des courriers.', 'error')
            return redirect(url_for('manage_outgoing_types'))
        
        nom_type = type_courrier.nom
        db.session.delete(type_courrier)
        db.session.commit()
        
        log_activity(current_user.id, "TYPE_SORTANT_SUPPRIME", 
                    f"Type de courrier sortant supprimé: {nom_type}")
        
        flash(t('type_deleted_successfully') or f'Type "{nom_type}" supprimé avec succès.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de la suppression du type: {e}")
        flash(t('error_deleting_type') or 'Erreur lors de la suppression du type.', 'error')
    
    return redirect(url_for('manage_outgoing_types'))

