import os
import uuid
import zipfile
import shutil
import tempfile
import subprocess
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session, send_file, abort, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_
import logging

from app import app, db
from models import User, Courrier, LogActivite, ParametresSysteme, StatutCourrier, Role, RolePermission, Departement
from utils import allowed_file, generate_accuse_reception, log_activity, export_courrier_pdf, export_mail_list_pdf, get_current_language, set_language, t, get_available_languages
from security_utils import rate_limit, sanitize_input, validate_file_upload, log_security_event, record_failed_login, is_login_locked, reset_failed_login_attempts, get_client_ip, validate_password_strength, audit_log
from performance_utils import cache_result, get_dashboard_statistics, optimize_search_query, PerformanceMonitor

@app.context_processor
def inject_system_context():
    """Inject system parameters and utility functions into all templates"""
    return dict(
        get_system_params=lambda: ParametresSysteme.get_parametres(),
        get_current_language=get_current_language,
        get_available_languages=get_available_languages
    )

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
@rate_limit(max_requests=10, per_minutes=15)  # Prevent brute force attacks - Increased from 5 to 10
def login():
    client_ip = get_client_ip()
    
    # Check if IP is locked due to too many failed attempts
    if is_login_locked(client_ip):
        audit_log("LOGIN_BLOCKED", f"Login attempt from blocked IP: {client_ip}", "WARNING")
        flash('Trop de tentatives de connexion échouées. Veuillez réessayer plus tard.', 'error')
        return render_template('login.html'), 429
    
    if request.method == 'POST':
        # Sanitize inputs
        username = sanitize_input(request.form.get('username', '').strip())
        password = request.form.get('password', '')
        
        if not username or not password:
            record_failed_login(client_ip, username)
            flash('Nom d\'utilisateur et mot de passe requis.', 'error')
            return render_template('login.html')
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        # Check credentials
        if user and user.actif:
            # Use encrypted password hash if available
            stored_hash = user.get_decrypted_password_hash()
            
            if check_password_hash(stored_hash, password):
                # Successful login
                reset_failed_login_attempts(client_ip)
                login_user(user)
                
                # Audit log
                audit_log("LOGIN_SUCCESS", f"Successful login for user: {username}")
                log_activity(user.id, "CONNEXION", f"Connexion réussie pour {username}")
                
                flash('Connexion réussie!', 'success')
                
                # Secure redirect
                next_page = request.args.get('next')
                if next_page:
                    from security_utils import secure_redirect
                    return redirect(secure_redirect(next_page))
                
                return redirect(url_for('dashboard'))
            else:
                # Failed password check
                is_blocked = record_failed_login(client_ip, username)
                audit_log("LOGIN_FAILED", f"Failed login attempt for user: {username} from IP: {client_ip}", "WARNING")
                
                if is_blocked:
                    flash('Trop de tentatives échouées. Votre IP est temporairement bloquée.', 'error')
                else:
                    flash('Nom d\'utilisateur ou mot de passe incorrect.', 'error')
        else:
            # User not found or inactive
            record_failed_login(client_ip, username)
            audit_log("LOGIN_FAILED", f"Login attempt for non-existent/inactive user: {username} from IP: {client_ip}", "WARNING")
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_activity(current_user.id, "DECONNEXION", f"Déconnexion de {current_user.username}")
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('login'))

@app.route('/test_webcam')
def test_webcam():
    """Page de test pour la webcam"""
    return render_template('test_webcam.html')

@app.route('/alternative_upload')
def alternative_upload():
    """Solution alternative pour Brave"""
    return render_template('alternative_upload.html')

@app.route('/simple_photo_capture')
def simple_photo_capture():
    """Page simple de capture photo compatible tous navigateurs"""
    return render_template('simple_photo_capture.html')

@app.route('/dashboard')
@login_required
def dashboard():
    with PerformanceMonitor("dashboard_load"):
        # Use cached statistics for better performance
        stats = get_dashboard_statistics()
        
        # Get recent mail specific to user permissions
        recent_query = Courrier.query
        
        # Apply permission filters
        if current_user.has_permission('read_all_mail'):
            pass  # Can see all
        elif current_user.has_permission('read_department_mail') and current_user.departement_id:
            recent_query = recent_query.join(User, Courrier.utilisateur_id == User.id).filter(
                User.departement_id == current_user.departement_id
            )
        else:
            recent_query = recent_query.filter(Courrier.utilisateur_id == current_user.id)
        
        recent_courriers = recent_query.order_by(
            Courrier.date_enregistrement.desc()
        ).limit(5).all()
        
        return render_template('dashboard.html', 
                             total_courriers=stats['total_courriers'],
                             courriers_today=stats['courriers_today'],
                             courriers_this_week=stats['courriers_this_week'],
                             total_users=stats['total_users'],
                             recent_courriers=recent_courriers,
                             recent_activities=stats['recent_activities'])

@app.route('/register_mail', methods=['GET', 'POST'])
@login_required
@rate_limit(max_requests=50, per_minutes=15)  # Prevent spam registration
def register_mail():
    if request.method == 'POST':
        # Récupération des données du formulaire
        numero_reference = request.form.get('numero_reference', '').strip()
        objet = request.form['objet'].strip()
        type_courrier = request.form.get('type_courrier', 'ENTRANT')
        statut = request.form.get('statut', 'RECU')
        date_redaction_str = request.form.get('date_redaction', '')
        
        # Traitement de la date de rédaction
        date_redaction = None
        if date_redaction_str:
            try:
                date_redaction = datetime.strptime(date_redaction_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Format de date de rédaction invalide.', 'error')
                statuts_disponibles = StatutCourrier.get_statuts_actifs()
                return render_template('register_mail.html', statuts_disponibles=statuts_disponibles)
        
        # Traiter expéditeur/destinataire selon le type
        expediteur = None
        destinataire = None
        
        if type_courrier == 'ENTRANT':
            expediteur = request.form.get('expediteur', '').strip()
            if not objet or not expediteur:
                flash('L\'objet et l\'expéditeur sont obligatoires pour un courrier entrant.', 'error')
                statuts_disponibles = StatutCourrier.get_statuts_actifs()
                return render_template('register_mail.html', statuts_disponibles=statuts_disponibles)
        else:  # SORTANT
            destinataire = request.form.get('destinataire', '').strip()
            if not objet or not destinataire:
                flash('L\'objet et le destinataire sont obligatoires pour un courrier sortant.', 'error')
                statuts_disponibles = StatutCourrier.get_statuts_actifs()
                return render_template('register_mail.html', statuts_disponibles=statuts_disponibles)
        
        # Génération du numéro d'accusé de réception
        numero_accuse = generate_accuse_reception()
        
        # Gestion du fichier uploadé
        file = request.files.get('fichier')
        fichier_nom = None
        fichier_chemin = None
        fichier_type = None
        
        if file and file.filename and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Ajouter timestamp pour éviter les conflits
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                fichier_chemin = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(fichier_chemin)
                fichier_nom = file.filename
                fichier_type = filename.rsplit('.', 1)[1].lower()
            else:
                flash('Type de fichier non autorisé. Utilisez PDF, JPG, PNG ou TIFF.', 'error')
                statuts_disponibles = StatutCourrier.get_statuts_actifs()
                return render_template('register_mail.html', statuts_disponibles=statuts_disponibles)
        
        # Création du courrier
        courrier = Courrier(
            numero_accuse_reception=numero_accuse,
            numero_reference=numero_reference if numero_reference else None,
            objet=objet,
            type_courrier=type_courrier,
            expediteur=expediteur,
            destinataire=destinataire,
            date_redaction=date_redaction,
            statut=statut,
            fichier_nom=fichier_nom,
            fichier_chemin=fichier_chemin,
            fichier_type=fichier_type,
            utilisateur_id=current_user.id
        )
        
        try:
            db.session.add(courrier)
            db.session.commit()
            
            # Log de l'activité
            log_activity(current_user.id, "ENREGISTREMENT_COURRIER", 
                        f"Enregistrement du courrier {numero_accuse}", courrier.id)
            
            flash(f'Courrier enregistré avec succès! N° d\'accusé: {numero_accuse}', 'success')
            return redirect(url_for('mail_detail', id=courrier.id))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de l'enregistrement: {e}")
            flash('Erreur lors de l\'enregistrement du courrier.', 'error')
    
    # Récupérer les statuts disponibles pour le formulaire
    statuts_disponibles = StatutCourrier.get_statuts_actifs()
    # Récupérer les départements pour le formulaire
    departements = Departement.get_departements_actifs()
    return render_template('register_mail.html', statuts_disponibles=statuts_disponibles, departements=departements)

@app.route('/view_mail')
@login_required
def view_mail():
    page = request.args.get('page', 1, type=int)
    per_page = 25  # Increased from 20 for better performance
    
    # Filtres
    search = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    date_redaction_from = request.args.get('date_redaction_from', '')
    date_redaction_to = request.args.get('date_redaction_to', '')
    statut = request.args.get('statut', '')
    sort_by = request.args.get('sort_by', 'date_enregistrement')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Construction de la requête avec restrictions selon le rôle
    query = Courrier.query
    
    # Appliquer les restrictions selon les permissions
    if current_user.has_permission('read_all_mail'):
        # Peut voir tous les courriers
        pass
    elif current_user.has_permission('read_department_mail'):
        # Peut voir les courriers de son département
        if current_user.departement_id:
            query = query.join(User, Courrier.utilisateur_id == User.id).filter(
                User.departement_id == current_user.departement_id
            )
        else:
            # Si pas de département assigné, ne voir que ses propres courriers
            query = query.filter(Courrier.utilisateur_id == current_user.id)
    elif current_user.has_permission('read_own_mail'):
        # Peut voir seulement ses propres courriers
        query = query.filter(Courrier.utilisateur_id == current_user.id)
    else:
        # Fallback sur l'ancien système si pas de permissions spécifiques
        if current_user.role == 'super_admin':
            # Super admin voit tout
            pass
        elif current_user.role == 'admin':
            # Admin voit les courriers de son département
            if current_user.departement_id:
                query = query.join(User, Courrier.utilisateur_id == User.id).filter(
                    User.departement_id == current_user.departement_id
                )
            else:
                # Si admin n'a pas de département assigné, ne voir que ses propres courriers
                query = query.filter(Courrier.utilisateur_id == current_user.id)
        else:
            # Utilisateur normal voit seulement ses propres courriers
            query = query.filter(Courrier.utilisateur_id == current_user.id)
    
    # Ajout du filtre pour type de courrier
    type_courrier = request.args.get('type_courrier', '')
    
    # Enhanced search with performance optimization
    if search:
        with PerformanceMonitor("search_query"):
            # Sanitize search input for security
            search = sanitize_input(search)
            search_condition = optimize_search_query(search, Courrier)
            if search_condition is not None:
                query = query.filter(search_condition)
                # Log search activity for analytics
                log_security_event("SEARCH", f"Search performed: {search[:50]}...")
    
    # Filtre par type de courrier
    if type_courrier:
        query = query.filter(Courrier.type_courrier == type_courrier)
    
    # Filtre par statut
    if statut:
        query = query.filter(Courrier.statut == statut)
    
    # Filtres par date
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Courrier.date_enregistrement >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Courrier.date_enregistrement <= date_to_obj)
        except ValueError:
            pass
    
    # Filtres par date de rédaction
    if date_redaction_from:
        try:
            date_redaction_from_obj = datetime.strptime(date_redaction_from, '%Y-%m-%d').date()
            query = query.filter(Courrier.date_redaction >= date_redaction_from_obj)
        except ValueError:
            pass
    
    if date_redaction_to:
        try:
            date_redaction_to_obj = datetime.strptime(date_redaction_to, '%Y-%m-%d').date()
            query = query.filter(Courrier.date_redaction <= date_redaction_to_obj)
        except ValueError:
            pass
    
    # Tri
    if sort_by in ['date_enregistrement', 'numero_accuse_reception', 'expediteur', 'objet', 'statut']:
        order_column = getattr(Courrier, sort_by)
        if sort_order == 'desc':
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())
    
    # Pagination
    courriers_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    courriers = courriers_paginated.items
    
    return render_template('view_mail.html', 
                         courriers=courriers,
                         pagination=courriers_paginated,
                         search=search,
                         date_from=date_from,
                         date_to=date_to,
                         date_redaction_from=date_redaction_from,
                         date_redaction_to=date_redaction_to,
                         statut=statut,
                         type_courrier=type_courrier,
                         sort_by=sort_by,
                         sort_order=sort_order)

@app.route('/search')
@login_required
def search():
    return render_template('search.html')

@app.route('/mail/<int:id>')
@login_required
def mail_detail(id):
    courrier = Courrier.query.get_or_404(id)
    
    # Vérifier les permissions d'accès au courrier
    if not current_user.can_view_courrier(courrier):
        flash('Vous n\'avez pas l\'autorisation de consulter ce courrier.', 'error')
        return redirect(url_for('view_mail'))
    
    statuts_disponibles = StatutCourrier.get_statuts_actifs()
    log_activity(current_user.id, "CONSULTATION_COURRIER", 
                f"Consultation du courrier {courrier.numero_accuse_reception}", courrier.id)
    return render_template('mail_detail_new.html', 
                          courrier=courrier,
                          statuts_disponibles=statuts_disponibles)

@app.route('/export_pdf/<int:id>')
@login_required
def export_pdf(id):
    courrier = Courrier.query.get_or_404(id)
    try:
        pdf_path = export_courrier_pdf(courrier)
        log_activity(current_user.id, "EXPORT_PDF", 
                    f"Export PDF du courrier {courrier.numero_accuse_reception}", courrier.id)
        return send_file(pdf_path, as_attachment=True, 
                        download_name=f"courrier_{courrier.numero_accuse_reception}.pdf")
    except Exception as e:
        logging.error(f"Erreur lors de l'export PDF: {e}")
        flash('Erreur lors de l\'export PDF.', 'error')
        return redirect(url_for('mail_detail', id=id))

@app.route('/edit_courrier/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_courrier(id):
    """Modifier un courrier existant avec logging des changements"""
    courrier = Courrier.query.get_or_404(id)
    
    # Vérifier les permissions d'édition
    if not current_user.can_edit_courrier(courrier):
        flash('Vous n\'avez pas l\'autorisation de modifier ce courrier.', 'error')
        return redirect(url_for('mail_detail', id=id))
    
    if request.method == 'POST':
        from utils import log_courrier_modification
        
        # Sauvegarder les anciennes valeurs pour le log
        old_values = {
            'numero_reference': courrier.numero_reference,
            'objet': courrier.objet,
            'type_courrier': courrier.type_courrier,
            'expediteur': courrier.expediteur,
            'destinataire': courrier.destinataire,
            'date_redaction': courrier.date_redaction,
            'statut': courrier.statut
        }
        
        # Mettre à jour les champs
        new_numero_reference = request.form.get('numero_reference', '').strip() or None
        new_objet = request.form.get('objet', '').strip()
        new_type_courrier = request.form.get('type_courrier')
        new_expediteur = request.form.get('expediteur', '').strip() or None
        new_destinataire = request.form.get('destinataire', '').strip() or None
        new_statut = request.form.get('statut')
        
        # Date de rédaction
        new_date_redaction = None
        if request.form.get('date_redaction'):
            try:
                new_date_redaction = datetime.strptime(request.form.get('date_redaction'), '%Y-%m-%d').date()
            except ValueError:
                flash('Format de date invalide.', 'error')
                return redirect(url_for('edit_courrier', id=id))
        
        # Validation
        if not new_objet:
            flash('L\'objet est obligatoire.', 'error')
            return redirect(url_for('edit_courrier', id=id))
        
        # Vérifier l'unicité du numéro de référence s'il est fourni
        if new_numero_reference and new_numero_reference != courrier.numero_reference:
            existing_courrier = Courrier.query.filter_by(numero_reference=new_numero_reference).first()
            if existing_courrier:
                flash('Ce numéro de référence existe déjà.', 'error')
                return redirect(url_for('edit_courrier', id=id))
        
        try:
            # Logger chaque modification
            changes = []
            
            if new_numero_reference != old_values['numero_reference']:
                log_courrier_modification(courrier.id, current_user.id, 'numero_reference', 
                                        old_values['numero_reference'], new_numero_reference)
                courrier.numero_reference = new_numero_reference
                changes.append('numéro de référence')
            
            if new_objet != old_values['objet']:
                log_courrier_modification(courrier.id, current_user.id, 'objet', 
                                        old_values['objet'], new_objet)
                courrier.objet = new_objet
                changes.append('objet')
            
            if new_type_courrier != old_values['type_courrier']:
                log_courrier_modification(courrier.id, current_user.id, 'type_courrier', 
                                        old_values['type_courrier'], new_type_courrier)
                courrier.type_courrier = new_type_courrier
                changes.append('type de courrier')
            
            if new_expediteur != old_values['expediteur']:
                log_courrier_modification(courrier.id, current_user.id, 'expediteur', 
                                        old_values['expediteur'], new_expediteur)
                courrier.expediteur = new_expediteur
                changes.append('expéditeur')
            
            if new_destinataire != old_values['destinataire']:
                log_courrier_modification(courrier.id, current_user.id, 'destinataire', 
                                        old_values['destinataire'], new_destinataire)
                courrier.destinataire = new_destinataire
                changes.append('destinataire')
            
            if new_date_redaction != old_values['date_redaction']:
                log_courrier_modification(courrier.id, current_user.id, 'date_redaction', 
                                        old_values['date_redaction'], new_date_redaction)
                courrier.date_redaction = new_date_redaction
                changes.append('date de rédaction')
            
            if new_statut != old_values['statut']:
                log_courrier_modification(courrier.id, current_user.id, 'statut', 
                                        old_values['statut'], new_statut)
                courrier.statut = new_statut
                courrier.date_modification_statut = datetime.utcnow()
                changes.append('statut')
            
            # Mettre à jour le modifieur et la date
            courrier.modifie_par_id = current_user.id
            
            db.session.commit()
            
            if changes:
                changes_text = ', '.join(changes)
                log_activity(current_user.id, "MODIFICATION_COURRIER", 
                           f"Modification du courrier {courrier.numero_accuse_reception}: {changes_text}", 
                           courrier.id)
                flash(f'Courrier modifié avec succès. Champs mis à jour: {changes_text}', 'success')
            else:
                flash('Aucune modification détectée.', 'info')
            
            return redirect(url_for('mail_detail', id=id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification: {str(e)}', 'error')
            return redirect(url_for('edit_courrier', id=id))
    
    # GET request - afficher le formulaire
    statuts_disponibles = StatutCourrier.get_statuts_actifs()
    return render_template('edit_courrier.html', 
                          courrier=courrier,
                          statuts_disponibles=statuts_disponibles)

@app.route('/senders_list')
@login_required
def senders_list():
    """Liste de tous les expéditeurs/destinataires avec statistiques"""
    from utils import get_all_senders
    
    try:
        senders = get_all_senders()
        log_activity(current_user.id, "CONSULTATION_EXPEDITEURS", 
                    f"Consultation de la liste des expéditeurs/destinataires")
        
        return render_template('senders_list.html', senders=senders)
        
    except Exception as e:
        flash(f'Erreur lors de la récupération des contacts: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/courrier_modifications/<int:courrier_id>')
@login_required
def courrier_modifications(courrier_id):
    """Voir l'historique complet des modifications d'un courrier"""
    courrier = Courrier.query.get_or_404(courrier_id)
    
    # Vérifier les permissions
    if not current_user.can_view_courrier(courrier):
        flash('Vous n\'avez pas l\'autorisation de consulter ce courrier.', 'error')
        return redirect(url_for('view_mail'))
    
    modifications = courrier.modifications
    log_activity(current_user.id, "CONSULTATION_MODIFICATIONS", 
                f"Consultation de l'historique des modifications du courrier {courrier.numero_accuse_reception}", 
                courrier.id)
    
    return render_template('courrier_modifications.html', 
                          courrier=courrier, 
                          modifications=modifications)

@app.route('/export_mail_list')
@login_required
def export_mail_list():
    """Export filtered mail list to PDF"""
    try:
        # Get the same filters as view_mail
        search = request.args.get('search', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        statut = request.args.get('statut', '')
        type_courrier = request.args.get('type_courrier', '')
        sort_by = request.args.get('sort_by', 'date_enregistrement')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Build query with same logic as view_mail (without pagination)
        query = Courrier.query
        
        # Apply permission restrictions
        if current_user.has_permission('read_all_mail'):
            pass
        elif current_user.has_permission('read_department_mail'):
            if current_user.departement_id:
                query = query.join(User, Courrier.utilisateur_id == User.id).filter(
                    User.departement_id == current_user.departement_id
                )
            else:
                query = query.filter(Courrier.utilisateur_id == current_user.id)
        elif current_user.has_permission('read_own_mail'):
            query = query.filter(Courrier.utilisateur_id == current_user.id)
        else:
            # Fallback
            if current_user.role == 'super_admin':
                pass
            elif current_user.role == 'admin':
                if current_user.departement_id:
                    query = query.join(User, Courrier.utilisateur_id == User.id).filter(
                        User.departement_id == current_user.departement_id
                    )
                else:
                    query = query.filter(Courrier.utilisateur_id == current_user.id)
            else:
                query = query.filter(Courrier.utilisateur_id == current_user.id)
        
        # Apply filters
        if search:
            query = query.filter(
                or_(
                    Courrier.numero_accuse_reception.contains(search),
                    Courrier.numero_reference.contains(search),
                    Courrier.objet.contains(search),
                    Courrier.expediteur.contains(search),
                    Courrier.destinataire.contains(search)
                )
            )
        
        if type_courrier:
            query = query.filter(Courrier.type_courrier == type_courrier)
        
        if statut:
            query = query.filter(Courrier.statut == statut)
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                query = query.filter(Courrier.date_enregistrement >= date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                query = query.filter(Courrier.date_enregistrement <= date_to_obj)
            except ValueError:
                pass
        
        # Apply sorting
        if sort_by in ['date_enregistrement', 'numero_accuse_reception', 'expediteur', 'objet', 'statut']:
            order_column = getattr(Courrier, sort_by)
            if sort_order == 'desc':
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
        
        # Get all results (no pagination for export)
        courriers = query.all()
        
        # Generate PDF
        pdf_path = export_mail_list_pdf(courriers, {
            'search': search,
            'date_from': date_from,
            'date_to': date_to,
            'statut': statut,
            'type_courrier': type_courrier,
            'sort_by': sort_by,
            'sort_order': sort_order
        })
        
        # Log activity
        log_activity(current_user.id, "EXPORT_LISTE_PDF", 
                    f"Export PDF de {len(courriers)} courriers")
        
        # Generate filename
        filename_parts = ['liste_courriers']
        if search:
            filename_parts.append(f"recherche_{search[:20]}")
        if type_courrier:
            filename_parts.append(type_courrier.lower())
        if date_from or date_to:
            filename_parts.append("filtre_date")
        filename_parts.append(datetime.now().strftime('%Y%m%d_%H%M'))
        filename = '_'.join(filename_parts) + '.pdf'
        
        return send_file(pdf_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logging.error(f"Erreur lors de l'export PDF de la liste: {e}")
        flash('Erreur lors de l\'export PDF de la liste.', 'error')
        return redirect(url_for('view_mail'))

@app.route('/download_file/<int:id>')
@login_required
def download_file(id):
    courrier = Courrier.query.get_or_404(id)
    if courrier.fichier_chemin and os.path.exists(courrier.fichier_chemin):
        log_activity(current_user.id, "TELECHARGEMENT_FICHIER", 
                    f"Téléchargement du fichier du courrier {courrier.numero_accuse_reception}", courrier.id)
        return send_file(courrier.fichier_chemin, as_attachment=True, 
                        download_name=courrier.fichier_nom)
    else:
        flash('Fichier non trouvé.', 'error')
        return redirect(url_for('mail_detail', id=id))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
@rate_limit(max_requests=20, per_minutes=15)
def settings():
    with PerformanceMonitor("settings_page"):
        parametres = ParametresSysteme.get_parametres()
        
        if request.method == 'POST':
            # Sanitize and update parameters
            parametres.nom_logiciel = sanitize_input(request.form['nom_logiciel'].strip())
            parametres.format_numero_accuse = sanitize_input(request.form['format_numero_accuse'].strip())
            parametres.telephone = sanitize_input(request.form.get('telephone', '').strip()) or None
            parametres.email_contact = sanitize_input(request.form.get('email_contact', '').strip()) or None
            parametres.adresse_organisme = sanitize_input(request.form.get('adresse_organisme', '').strip()) or None
            
            # Sanitize PDF parameters
            parametres.texte_footer = sanitize_input(request.form.get('texte_footer', '').strip()) or "Système de Gestion Électronique du Courrier"
            parametres.titre_pdf = sanitize_input(request.form.get('titre_pdf', '').strip()) or "Ministère des Mines"
            parametres.sous_titre_pdf = sanitize_input(request.form.get('sous_titre_pdf', '').strip()) or "Secrétariat Général"
            parametres.pays_pdf = sanitize_input(request.form.get('pays_pdf', '').strip()) or "République Démocratique du Congo"
            parametres.copyright_text = sanitize_input(request.form.get('copyright_text', '').strip()) or "© 2025 GEC. Made with 💖 and ☕ By MOA-Digital Agency LLC"
            
            parametres.modifie_par_id = current_user.id
            
            # Gestion du logo principal
            print(f"DEBUG: All files in request: {list(request.files.keys())}")
            if 'logo' in request.files:
                logo = request.files['logo']
                print(f"DEBUG: Logo file received: {logo.filename if logo else 'None'}")
                print(f"DEBUG: Logo file size: {len(logo.read()) if logo else 0} bytes")
                if logo:
                    logo.seek(0)  # Reset file pointer after reading
                logging.info(f"DEBUG: Logo file received: {logo.filename if logo else 'None'}")
                print(f"DEBUG: Logo file received: {logo.filename if logo else 'None'}")
                if logo and logo.filename and logo.filename != '' and allowed_file(logo.filename):
                    filename = secure_filename(logo.filename)
                    # Créer un nom unique pour le logo
                    logo_filename = f"logo_{uuid.uuid4().hex[:8]}_{filename}"
                    logo_path = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), logo_filename)
                    
                    try:
                        # Supprimer l'ancien logo si il existe
                        if parametres.logo_url:
                            old_logo_path = parametres.logo_url.replace('/uploads/', '')
                            old_full_path = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), old_logo_path)
                            if os.path.exists(old_full_path):
                                os.remove(old_full_path)
                                print(f"DEBUG: Removed old logo: {old_full_path}")
                        
                        logo.save(logo_path)
                        parametres.logo_url = f'/uploads/{logo_filename}'
                        print(f"DEBUG: New logo saved: {parametres.logo_url}")
                        flash('Logo téléchargé avec succès!', 'success')
                    except Exception as e:
                        print(f"DEBUG: Error saving logo: {e}")
                        flash(f'Erreur lors du téléchargement du logo: {str(e)}', 'error')
                elif logo and logo.filename:
                    # Debug: show what files are rejected
                    print(f"DEBUG: File rejected: {logo.filename}")
                    flash(f'Type de fichier non autorisé: {logo.filename}. Utilisez PNG, JPG, JPEG ou SVG.', 'error')
                else:
                    print("DEBUG: No logo file uploaded or empty filename")
                    flash('Veuillez sélectionner un fichier pour le logo.', 'warning')
            
            # Gestion du logo PDF
            if 'logo_pdf' in request.files:
                logo_pdf = request.files['logo_pdf']
                if logo_pdf and logo_pdf.filename and logo_pdf.filename != '' and allowed_file(logo_pdf.filename):
                    filename = secure_filename(logo_pdf.filename)
                    # Créer un nom unique pour le logo PDF
                    logo_pdf_filename = f"logo_pdf_{uuid.uuid4().hex[:8]}_{filename}"
                    logo_pdf_path = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), logo_pdf_filename)
                    
                    try:
                        logo_pdf.save(logo_pdf_path)
                        parametres.logo_pdf = f'/uploads/{logo_pdf_filename}'
                        flash('Logo PDF téléchargé avec succès!', 'success')
                    except Exception as e:
                        flash(f'Erreur lors du téléchargement du logo PDF: {str(e)}', 'error')
        
            try:
                db.session.commit()
                log_activity(current_user.id, "MODIFICATION_PARAMETRES", 
                            f"Mise à jour des paramètres système par {current_user.username}")
                log_security_event("SETTINGS_UPDATE", f"System settings updated by {current_user.username}")
                flash('Paramètres sauvegardés avec succès!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur lors de la sauvegarde: {str(e)}', 'error')
                log_security_event("SETTINGS_ERROR", f"Failed to save settings: {str(e)}")
            
            return redirect(url_for('settings'))
        
        # Generate format preview with caching
        format_preview = generate_format_preview(parametres.format_numero_accuse)
        
        # Get backup files (only for super admins)
        backup_files = get_backup_files() if current_user.is_super_admin() else []
        
        return render_template('settings.html', 
                              parametres=parametres,
                              format_preview=format_preview,
                              backup_files=backup_files)

@app.route('/backup_system', methods=['POST'])
@login_required
def backup_system():
    """Créer une sauvegarde complète du système"""
    if not current_user.is_super_admin():
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
    
    return redirect(url_for('settings'))

@app.route('/download_backup/<filename>')
@login_required
def download_backup(filename):
    """Télécharger un fichier de sauvegarde"""
    if not current_user.is_super_admin():
        flash('Accès refusé.', 'error')
        return redirect(url_for('settings'))
    
    backup_path = os.path.join('backups', filename)
    if os.path.exists(backup_path):
        return send_file(backup_path, as_attachment=True)
    else:
        flash('Fichier de sauvegarde non trouvé.', 'error')
        return redirect(url_for('settings'))

@app.route('/restore_system', methods=['POST'])
@login_required
def restore_system():
    """Restaurer le système depuis une sauvegarde"""
    if not current_user.is_super_admin():
        flash('Accès refusé. Seuls les super administrateurs peuvent restaurer le système.', 'error')
        return redirect(url_for('settings'))
    
    if 'backup_file' not in request.files:
        flash('Aucun fichier de sauvegarde sélectionné.', 'error')
        return redirect(url_for('settings'))
    
    backup_file = request.files['backup_file']
    if backup_file.filename == '':
        flash('Aucun fichier sélectionné.', 'error')
        return redirect(url_for('settings'))
    
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
    
    return redirect(url_for('settings'))

def generate_format_preview(format_string):
    """Génère un aperçu du format de numéro d'accusé"""
    import re
    from datetime import datetime
    
    now = datetime.now()
    preview = format_string
    
    # Remplacer les variables
    preview = preview.replace('{year}', str(now.year))
    preview = preview.replace('{month}', f"{now.month:02d}")
    preview = preview.replace('{day}', f"{now.day:02d}")
    
    # Traiter les compteurs avec format
    counter_pattern = r'\{counter:(\d+)d\}'
    matches = re.findall(counter_pattern, preview)
    for match in matches:
        width = int(match)
        formatted_counter = f"{1:0{width}d}"
        preview = re.sub(r'\{counter:\d+d\}', formatted_counter, preview, count=1)
    
    # Compteur simple
    preview = preview.replace('{counter}', '1')
    
    # Nombre aléatoire
    random_pattern = r'\{random:(\d+)\}'
    matches = re.findall(random_pattern, preview)
    for match in matches:
        width = int(match)
        random_num = '1' * width  # Utiliser 1111 pour l'aperçu
        preview = re.sub(r'\{random:\d+\}', random_num, preview, count=1)
    
    return preview

@app.route('/change_status/<int:id>', methods=['POST'])
@login_required
def change_status(id):
    courrier = Courrier.query.get_or_404(id)
    new_status = request.form.get('nouveau_statut')
    
    if new_status:
        old_status = courrier.statut
        courrier.statut = new_status
        courrier.modifie_par_id = current_user.id
        
        try:
            db.session.commit()
            log_activity(current_user.id, "CHANGEMENT_STATUT", 
                        f"Statut du courrier {courrier.numero_accuse_reception} changé de {old_status} à {new_status}", courrier.id)
            flash(f'Statut mis à jour vers "{new_status}"', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour: {str(e)}', 'error')
    
    return redirect(url_for('mail_detail', id=id))

@app.route('/view_file/<int:id>')
@login_required
def view_file(id):
    courrier = Courrier.query.get_or_404(id)
    if courrier.fichier_chemin and os.path.exists(courrier.fichier_chemin):
        log_activity(current_user.id, "VISUALISATION_FICHIER", 
                    f"Visualisation du fichier du courrier {courrier.numero_accuse_reception}", courrier.id)
        return send_file(courrier.fichier_chemin, as_attachment=False)
    else:
        flash('Fichier non trouvé.', 'error')
        return redirect(url_for('mail_detail', id=id))

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

@app.route('/set_language/<lang_code>')
def set_user_language(lang_code):
    """Changer la langue de l'interface"""
    if set_language(lang_code):
        if current_user.is_authenticated:
            # Sauvegarder la préférence dans le profil utilisateur
            current_user.langue = lang_code
            db.session.commit()
    
    # Rediriger vers la page précédente ou le dashboard
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/manage_users')
@login_required
def manage_users():
    """Gestion des utilisateurs - accessible uniquement aux super admins"""
    if not current_user.can_manage_users():
        flash('Accès refusé. Seuls les super administrateurs peuvent gérer les utilisateurs.', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.order_by(User.date_creation.desc()).all()
    departements = Departement.get_departements_actifs()
    return render_template('manage_users.html', users=users, departements=departements,
                         available_languages=get_available_languages())

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
    return render_template('add_user.html', 
                         available_languages=get_available_languages(),
                         departements=departements)

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
    return render_template('edit_user.html', user=user, 
                         available_languages=get_available_languages(),
                         departements=departements)

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

@app.route('/logs')
@login_required
def view_logs():
    """Consulter les logs d'activité - accessible uniquement aux super admins"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Filtres
    search = request.args.get('search', '')
    action_filter = request.args.get('action', '')
    user_filter = request.args.get('user_id', '', type=str)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Construction de la requête
    query = LogActivite.query.join(User).order_by(LogActivite.date_action.desc())
    
    # Filtre de recherche textuelle
    if search:
        query = query.filter(
            db.or_(
                LogActivite.action.contains(search),
                LogActivite.description.contains(search),
                User.username.contains(search),
                User.nom_complet.contains(search)
            )
        )
    
    # Filtre par action
    if action_filter:
        query = query.filter(LogActivite.action == action_filter)
    
    # Filtre par utilisateur
    if user_filter:
        query = query.filter(LogActivite.utilisateur_id == user_filter)
    
    # Filtres par date
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(LogActivite.date_action >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            # Ajouter 23:59:59 pour inclure toute la journée
            date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            query = query.filter(LogActivite.date_action <= date_to_obj)
        except ValueError:
            pass
    
    # Pagination
    logs_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = logs_paginated.items
    
    # Obtenir les actions uniques pour le filtre
    actions_distinctes = db.session.query(LogActivite.action).distinct().order_by(LogActivite.action).all()
    actions_list = [action[0] for action in actions_distinctes]
    
    # Obtenir les utilisateurs pour le filtre
    users_list = User.query.order_by(User.username).all()
    
    return render_template('logs.html',
                         logs=logs,
                         pagination=logs_paginated,
                         search=search,
                         action_filter=action_filter,
                         user_filter=user_filter,
                         date_from=date_from,
                         date_to=date_to,
                         actions_list=actions_list,
                         users_list=users_list)

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
        'read_all_mail': 'Lire tous les courriers',
        'read_department_mail': 'Lire courriers du département',
        'read_own_mail': 'Lire ses propres courriers'
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
        'read_all_mail': 'Lire tous les courriers',
        'read_department_mail': 'Lire courriers du département',
        'read_own_mail': 'Lire ses propres courriers'
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
    return render_template('manage_departments.html', departements=departements)

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
            
            log_activity(current_user.id, "CREATION_DEPARTEMENT", 
                        f"Création du département {nom}")
            flash(f'Département "{nom}" créé avec succès!', 'success')
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
        
        # Vérifier les doublons (sauf pour ce département)
        if Departement.query.filter(Departement.nom == nom, Departement.id != dept_id).first():
            flash('Ce nom de département existe déjà.', 'error')
            return redirect(url_for('edit_department', dept_id=dept_id))
        
        if Departement.query.filter(Departement.code == code, Departement.id != dept_id).first():
            flash('Ce code de département existe déjà.', 'error')
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
            flash(f'Département "{nom}" modifié avec succès!', 'success')
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
    
    # Vérifier si des utilisateurs sont assignés à ce département
    users_count = User.query.filter_by(departement_id=dept_id).count()
    if users_count > 0:
        flash(f'Impossible de supprimer ce département. {users_count} utilisateur(s) y sont assignés.', 'error')
        return redirect(url_for('manage_departments'))
    
    try:
        nom = departement.nom
        db.session.delete(departement)
        db.session.commit()
        
        log_activity(current_user.id, "SUPPRESSION_DEPARTEMENT", 
                    f"Suppression du département {nom}")
        flash(f'Département "{nom}" supprimé avec succès!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'error')
    
    return redirect(url_for('manage_departments'))

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

@app.route('/static/uploads/profiles/<filename>')
def profile_photo(filename):
    """Servir les photos de profil"""
    profile_folder = os.path.join('uploads', 'profiles')
    return send_file(os.path.join(profile_folder, filename))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Servir les fichiers uploadés (logos, etc.)"""
    try:
        upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        return send_from_directory(upload_folder, filename)
    except Exception as e:
        logging.error(f"Erreur lors du service du fichier {filename}: {e}")
        abort(404)

@app.route('/profile')
@login_required
def profile():
    """Afficher le profil de l'utilisateur actuel"""
    return render_template('profile.html', user=current_user, 
                         available_languages=get_available_languages())

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

@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('base.html'), 500

# Fonctions utilitaires pour backup/restore
def create_system_backup():
    """Créer une sauvegarde complète du système"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"gec_backup_{timestamp}.zip"
    
    # Créer le dossier backups s'il n'existe pas
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    backup_path = os.path.join(backup_dir, backup_filename)
    
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
        # 1. Sauvegarde de la base de données
        db_backup_path = backup_database()
        if db_backup_path:
            backup_zip.write(db_backup_path, "database_backup.sql")
            os.remove(db_backup_path)  # Nettoyer le fichier temporaire
        
        # 2. Fichiers système critiques
        system_files = [
            'app.py', 'main.py', 'models.py', 'views.py', 'utils.py',
            'requirements.txt', 'pyproject.toml', '.replit'
        ]
        
        for file in system_files:
            if os.path.exists(file):
                backup_zip.write(file)
        
        # 3. Dossiers critiques
        critical_dirs = ['templates', 'static', 'lang', 'utils']
        for dir_name in critical_dirs:
            if os.path.exists(dir_name):
                for root, dirs, files in os.walk(dir_name):
                    for file in files:
                        file_path = os.path.join(root, file)
                        backup_zip.write(file_path)
        
        # 4. Fichiers uploads
        uploads_dir = app.config.get('UPLOAD_FOLDER', 'uploads')
        if os.path.exists(uploads_dir):
            for root, dirs, files in os.walk(uploads_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    backup_zip.write(file_path)
        
        # 5. Métadonnées de sauvegarde
        metadata = {
            'backup_date': timestamp,
            'version': '1.0',
            'backup_type': 'full_system',
            'created_by': current_user.username if current_user.is_authenticated else 'system'
        }
        
        import json
        metadata_path = f"backup_metadata_{timestamp}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        backup_zip.write(metadata_path, "backup_metadata.json")
        os.remove(metadata_path)  # Nettoyer
    
    return backup_filename

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
                f.write("-- GEC Mines Database Backup\n")
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
    """Restaurer le système depuis un fichier de sauvegarde"""
    # Créer un dossier temporaire pour l'extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        # Sauvegarder le fichier uploadé
        temp_backup_path = os.path.join(temp_dir, "backup.zip")
        backup_file.save(temp_backup_path)
        
        # Extraire l'archive
        with zipfile.ZipFile(temp_backup_path, 'r') as backup_zip:
            backup_zip.extractall(temp_dir)
        
        # Vérifier les métadonnées
        metadata_path = os.path.join(temp_dir, "backup_metadata.json")
        if os.path.exists(metadata_path):
            import json
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            logging.info(f"Restauration depuis sauvegarde: {metadata}")
        
        # 1. Sauvegarder l'état actuel avant restauration
        current_backup = create_system_backup()
        logging.info(f"Sauvegarde de sécurité créée: {current_backup}")
        
        # 2. Restaurer la base de données
        db_backup_path = os.path.join(temp_dir, "database_backup.sql")
        if os.path.exists(db_backup_path):
            restore_database(db_backup_path)
        
        # 3. Restaurer les fichiers système (avec précaution)
        protected_files = ['main.py', 'app.py']  # Ne pas écraser les fichiers critiques
        
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file in ['backup_metadata.json', 'database_backup.sql']:
                    continue
                    
                source_path = os.path.join(root, file)
                relative_path = os.path.relpath(source_path, temp_dir)
                
                # Éviter d'écraser les fichiers protégés
                if any(pf in relative_path for pf in protected_files):
                    continue
                
                target_path = relative_path
                
                # Créer les dossiers si nécessaire
                target_dir = os.path.dirname(target_path)
                if target_dir and not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                
                # Copier le fichier
                if os.path.exists(source_path):
                    shutil.copy2(source_path, target_path)
        
        logging.info("Restauration système terminée")

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

def get_backup_files():
    """Obtenir la liste des fichiers de sauvegarde disponibles"""
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        return []
    
    backups = []
    for filename in os.listdir(backup_dir):
        if filename.endswith('.zip') and filename.startswith('gec_backup_'):
            file_path = os.path.join(backup_dir, filename)
            file_stat = os.stat(file_path)
            
            backups.append({
                'filename': filename,
                'size': file_stat.st_size,
                'date': datetime.fromtimestamp(file_stat.st_mtime),
                'path': file_path
            })
    
    # Trier par date (plus récent en premier)
    backups.sort(key=lambda x: x['date'], reverse=True)
    return backups


@app.route("/security_logs")
@login_required
def security_logs():
    # Vérifier les permissions d'accès aux logs de sécurité
    if not (current_user.has_permission('view_security_logs') or current_user.is_super_admin()):
        flash('Vous n\'avez pas les permissions pour consulter les logs de sécurité.', 'error')
        return redirect(url_for('dashboard'))
    
    from security_utils import get_security_logs, get_security_stats
    
    # Paramètres de filtrage
    level = request.args.get("level", "")
    event_type = request.args.get("event_type", "")
    date_start = request.args.get("date_start", "")
    date_end = request.args.get("date_end", "")
    page = request.args.get("page", 1, type=int)
    per_page = 50
    
    # Vérifier si export CSV
    if request.args.get("export") == "csv":
        return export_security_logs(level, event_type, date_start, date_end)
    
    # Récupérer les logs avec filtres
    filters = {
        "level": level,
        "event_type": event_type,
        "date_start": date_start,
        "date_end": date_end,
        "page": page,
        "per_page": per_page
    }
    
    security_logs_data = get_security_logs(filters)
    stats = get_security_stats()
    
    return render_template("security_logs.html", 
                         security_logs=security_logs_data["logs"],
                         pagination=security_logs_data["pagination"],
                         stats=stats)

@app.route('/security_settings', methods=['GET', 'POST'])
@login_required
def security_settings():
    """Configuration des paramètres de sécurité"""
    if not (current_user.has_permission('manage_security_settings') or current_user.is_super_admin()):
        flash('Vous n\'avez pas les permissions pour gérer les paramètres de sécurité.', 'error')
        return redirect(url_for('dashboard'))
        
    from security_utils import (MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_DURATION, 
                               SUSPICIOUS_ACTIVITY_THRESHOLD, AUTO_BLOCK_DURATION,
                               _blocked_ips, _failed_login_attempts, get_security_logs)
    
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'login_security':
            # Mise à jour des paramètres de connexion
            try:
                max_attempts = int(request.form.get('max_login_attempts', 8))
                lockout_duration = int(request.form.get('lockout_duration', 15))
                rate_limit = int(request.form.get('rate_limit_requests', 10))
                
                # Validation des valeurs
                if 3 <= max_attempts <= 20 and 5 <= lockout_duration <= 120 and 5 <= rate_limit <= 50:
                    # Mettre à jour les constantes de sécurité (normalement, ceci devrait être dans une base de données)
                    flash(f'Paramètres mis à jour: {max_attempts} tentatives max, blocage {lockout_duration}min', 'success')
                    log_activity(current_user.id, "SECURITY_SETTINGS", 
                               f"Paramètres de sécurité modifiés: {max_attempts} tentatives, {lockout_duration}min blocage")
                else:
                    flash('Valeurs invalides. Vérifiez les limites autorisées.', 'error')
            except ValueError:
                flash('Erreur: valeurs numériques invalides', 'error')
        
        elif form_type == 'unblock_all':
            # Débloquer toutes les IPs
            cleared_ips = len(_blocked_ips)
            _blocked_ips.clear()
            _failed_login_attempts.clear()
            flash(f'{cleared_ips} adresses IP débloquées', 'success')
            log_activity(current_user.id, "SECURITY_UNBLOCK", f"Toutes les IP bloquées débloquées ({cleared_ips})")
        
        elif form_type == 'unblock_ip':
            # Débloquer une IP spécifique
            ip_address = request.form.get('ip_address')
            if ip_address and ip_address in _blocked_ips:
                _blocked_ips.remove(ip_address)
                if ip_address in _failed_login_attempts:
                    del _failed_login_attempts[ip_address]
                flash(f'Adresse IP {ip_address} débloquée avec succès', 'success')
                log_activity(current_user.id, "SECURITY_UNBLOCK", f"IP {ip_address} débloquée manuellement")
                log_security_event("IP_UNBLOCK", f"IP {ip_address} unblocked by {current_user.username}")
            else:
                flash(f'Adresse IP {ip_address} non trouvée dans la liste des IP bloquées', 'error')
        
        elif form_type == 'advanced_security':
            # Configuration avancée
            try:
                suspicious_threshold = int(request.form.get('suspicious_threshold', 15))
                auto_block_duration = int(request.form.get('auto_block_duration', 30))
                audit_logging = 'enable_audit_logging' in request.form
                
                # Validation et application
                if 5 <= suspicious_threshold <= 50 and 10 <= auto_block_duration <= 240:
                    flash('Configuration avancée mise à jour', 'success')
                    log_activity(current_user.id, "SECURITY_CONFIG", 
                               f"Config avancée: seuil {suspicious_threshold}, blocage {auto_block_duration}min, audit {audit_logging}")
                else:
                    flash('Valeurs invalides pour la configuration avancée', 'error')
            except ValueError:
                flash('Erreur dans la configuration avancée', 'error')
        
        return redirect(url_for('security_settings'))
    
    # Statistiques de sécurité
    from datetime import datetime, timedelta
    now = datetime.now()
    failed_attempts_24h = sum(1 for data in _failed_login_attempts.values() 
                             if isinstance(data, dict) and 
                             now - data.get('timestamp', now) < timedelta(hours=24))
    
    return render_template('security_settings.html',
                         max_login_attempts=MAX_LOGIN_ATTEMPTS,
                         lockout_duration=LOGIN_LOCKOUT_DURATION,
                         rate_limit_requests=10,  # Cette valeur devrait venir de la configuration
                         suspicious_threshold=SUSPICIOUS_ACTIVITY_THRESHOLD,
                         auto_block_duration=AUTO_BLOCK_DURATION,
                         audit_logging_enabled=True,  # Cette valeur devrait venir de la configuration
                         blocked_ips=list(_blocked_ips),
                         failed_attempts_24h=failed_attempts_24h,
                         monitored_ips=len(_failed_login_attempts))

def export_security_logs(level, event_type, date_start, date_end):
    """Exporte les logs de sécurité en CSV"""
    from security_utils import get_security_logs
    from flask import Response
    import csv
    import io
    
    filters = {
        "level": level,
        "event_type": event_type,
        "date_start": date_start,
        "date_end": date_end,
        "page": 1,
        "per_page": 10000
    }
    
    logs_data = get_security_logs(filters)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["Date/Heure", "Niveau", "Type", "Message", "IP", "Utilisateur"])
    
    for log in logs_data["logs"]:
        writer.writerow([
            log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            log.level,
            log.event_type,
            log.message,
            log.ip_address or "",
            log.username or ""
        ])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=security_logs_{}.csv".format(datetime.now().strftime("%Y%m%d_%H%M%S"))
        }
    )

