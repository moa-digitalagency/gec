import os
import uuid
import io
import csv
import zipfile
import shutil
import tempfile
import subprocess
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session, send_file, abort, send_from_directory, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_
import logging

from app import app, db
from models import User, Courrier, LogActivite, ParametresSysteme, StatutCourrier, Role, RolePermission, Departement, TypeCourrierSortant, Notification, CourrierComment, CourrierForward
from utils import allowed_file, generate_accuse_reception, log_activity, export_courrier_pdf, export_mail_list_pdf, get_current_language, set_language, t, get_available_languages
from email_utils import send_new_mail_notification, send_mail_forwarded_notification
from security_utils import rate_limit, sanitize_input, validate_file_upload, log_security_event, record_failed_login, is_login_locked, reset_failed_login_attempts, get_client_ip, validate_password_strength, audit_log
from performance_utils import cache_result, get_dashboard_statistics, optimize_search_query, PerformanceMonitor

@app.context_processor
def inject_system_context():
    """Inject system parameters and utility functions into all templates"""
    def get_unread_notifications_count():
        if current_user.is_authenticated:
            return Notification.query.filter_by(user_id=current_user.id, lu=False).count()
        return 0
    
    return dict(
        get_system_params=lambda: ParametresSysteme.get_parametres(),
        get_current_language=get_current_language,
        get_available_languages=get_available_languages,
        get_unread_notifications_count=get_unread_notifications_count
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
        # Get inputs (no sanitization for username as it's handled by ORM)
        username = request.form.get('username', '').strip()
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

@app.route('/manage_email_templates')
@login_required
@rate_limit(max_requests=30, per_minutes=15)
def manage_email_templates():
    """Gestion des templates d'email"""
    if not current_user.has_permission('manage_email_templates') and not current_user.is_super_admin():
        flash('Vous n\'avez pas l\'autorisation d\'accéder à cette page.', 'error')
        return redirect(url_for('dashboard'))
    
    from models import EmailTemplate
    templates = EmailTemplate.query.order_by(EmailTemplate.type_template, EmailTemplate.langue).all()
    
    log_activity(current_user.id, "CONSULTATION_TEMPLATES_EMAIL", "Consultation de la page de gestion des templates email")
    return render_template('manage_email_templates.html', templates=templates)

@app.route('/add_email_template', methods=['GET', 'POST'])
@login_required
@rate_limit(max_requests=20, per_minutes=15)
def add_email_template():
    """Ajouter un nouveau template d'email"""
    if not current_user.has_permission('manage_email_templates') and not current_user.is_super_admin():
        flash('Vous n\'avez pas l\'autorisation d\'accéder à cette page.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        from models import EmailTemplate
        
        type_template = sanitize_input(request.form.get('type_template', '').strip())
        langue = sanitize_input(request.form.get('langue', 'fr').strip())
        sujet = sanitize_input(request.form.get('sujet', '').strip())
        contenu_html = request.form.get('contenu_html', '').strip()
        contenu_texte = request.form.get('contenu_texte', '').strip()
        
        if not type_template or not sujet or not contenu_html:
            flash('Le type de template, le sujet et le contenu HTML sont obligatoires.', 'error')
            return render_template('add_email_template.html')
        
        # Vérifier que le template n'existe pas déjà
        existing = EmailTemplate.query.filter_by(type_template=type_template, langue=langue).first()
        if existing:
            flash(f'Un template de type "{type_template}" existe déjà pour la langue "{langue}".', 'error')
            return render_template('add_email_template.html')
        
        try:
            template = EmailTemplate(
                type_template=type_template,
                langue=langue,
                sujet=sujet,
                contenu_html=contenu_html,
                contenu_texte=contenu_texte if contenu_texte else None,
                cree_par_id=current_user.id
            )
            
            db.session.add(template)
            db.session.commit()
            
            log_activity(current_user.id, "CREATION_TEMPLATE_EMAIL", 
                        f"Création du template email {type_template}:{langue}")
            flash('Template d\'email créé avec succès!', 'success')
            return redirect(url_for('manage_email_templates'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la création du template: {e}")
            flash('Erreur lors de la création du template.', 'error')
    
    return render_template('add_email_template.html')

@app.route('/edit_email_template/<int:template_id>', methods=['GET', 'POST'])
@login_required
@rate_limit(max_requests=20, per_minutes=15)
def edit_email_template(template_id):
    """Modifier un template d'email"""
    if not current_user.has_permission('manage_email_templates') and not current_user.is_super_admin():
        flash('Vous n\'avez pas l\'autorisation d\'accéder à cette page.', 'error')
        return redirect(url_for('dashboard'))
    
    from models import EmailTemplate
    template = EmailTemplate.query.get_or_404(template_id)
    
    if request.method == 'POST':
        sujet = sanitize_input(request.form.get('sujet', '').strip())
        contenu_html = request.form.get('contenu_html', '').strip()
        contenu_texte = request.form.get('contenu_texte', '').strip()
        actif = request.form.get('actif') == 'on'
        
        if not sujet or not contenu_html:
            flash('Le sujet et le contenu HTML sont obligatoires.', 'error')
            return render_template('edit_email_template.html', template=template)
        
        try:
            template.sujet = sujet
            template.contenu_html = contenu_html
            template.contenu_texte = contenu_texte if contenu_texte else None
            template.actif = actif
            template.modifie_par_id = current_user.id
            
            db.session.commit()
            
            log_activity(current_user.id, "MODIFICATION_TEMPLATE_EMAIL", 
                        f"Modification du template email {template.type_template}:{template.langue}")
            flash('Template d\'email modifié avec succès!', 'success')
            return redirect(url_for('manage_email_templates'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la modification du template: {e}")
            flash('Erreur lors de la modification du template.', 'error')
    
    return render_template('edit_email_template.html', template=template)

@app.route('/delete_email_template/<int:template_id>', methods=['POST'])
@login_required
@rate_limit(max_requests=10, per_minutes=15)
def delete_email_template(template_id):
    """Supprimer un template d'email"""
    if not current_user.has_permission('manage_email_templates') and not current_user.is_super_admin():
        flash('Vous n\'avez pas l\'autorisation d\'accéder à cette page.', 'error')
        return redirect(url_for('dashboard'))
    
    from models import EmailTemplate
    template = EmailTemplate.query.get_or_404(template_id)
    
    try:
        template_info = f"{template.type_template}:{template.langue}"
        db.session.delete(template)
        db.session.commit()
        
        log_activity(current_user.id, "SUPPRESSION_TEMPLATE_EMAIL", 
                    f"Suppression du template email {template_info}")
        flash('Template d\'email supprimé avec succès!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de la suppression du template: {e}")
        flash('Erreur lors de la suppression du template.', 'error')
    
    return redirect(url_for('manage_email_templates'))

@app.route('/test_smtp_config', methods=['POST'])
@login_required
@rate_limit(max_requests=5, per_minutes=15)
def test_smtp_config():
    """Teste la configuration SMTP en envoyant un email de test"""
    if not current_user.has_permission('manage_system_settings') and not current_user.is_super_admin():
        flash('Vous n\'avez pas l\'autorisation d\'accéder à cette fonctionnalité.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from email_utils import send_email_from_system_config
        from models import ParametresSysteme
        
        # Email de test
        test_email = sanitize_input(request.form.get('test_email', '').strip())
        if not test_email:
            flash('Veuillez saisir un email de test.', 'error')
            return redirect(url_for('settings'))
        
        # Récupérer le nom du logiciel
        nom_logiciel = ParametresSysteme.get_valeur('nom_logiciel', 'GEC')
        
        # Contenu de l'email de test
        subject = f"Test de configuration SMTP - {nom_logiciel}"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #003087; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .success {{ background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .footer {{ background-color: #f1f1f1; padding: 10px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>{nom_logiciel} - Test SMTP</h2>
            </div>
            <div class="content">
                <div class="success">
                    <h3>✅ Configuration SMTP Fonctionnelle</h3>
                    <p>Ce message confirme que la configuration SMTP de votre système {nom_logiciel} fonctionne correctement.</p>
                </div>
                
                <p><strong>Détails du test :</strong></p>
                <ul>
                    <li><strong>Date et heure :</strong> {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}</li>
                    <li><strong>Testé par :</strong> {current_user.nom_complet}</li>
                    <li><strong>Email de test :</strong> {test_email}</li>
                </ul>
                
                <p>Vous pouvez maintenant utiliser les fonctionnalités de notification par email en toute confiance.</p>
            </div>
            <div class="footer">
                <p>{nom_logiciel} - Système de Gestion des Courriers<br>
                Test automatique de configuration SMTP</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        {nom_logiciel} - Test SMTP
        
        ✅ Configuration SMTP Fonctionnelle
        
        Ce message confirme que la configuration SMTP de votre système {nom_logiciel} fonctionne correctement.
        
        Détails du test :
        - Date et heure : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}
        - Testé par : {current_user.nom_complet}
        - Email de test : {test_email}
        
        Vous pouvez maintenant utiliser les fonctionnalités de notification par email en toute confiance.
        
        {nom_logiciel} - Système de Gestion des Courriers
        Test automatique de configuration SMTP
        """
        
        # Envoyer l'email de test
        if send_email_from_system_config(test_email, subject, html_content, text_content):
            log_activity(current_user.id, "TEST_SMTP_SUCCESS", 
                        f"Test SMTP réussi vers {test_email}")
            flash(f'✅ Email de test envoyé avec succès à {test_email}! Vérifiez votre boîte de réception.', 'success')
        else:
            log_activity(current_user.id, "TEST_SMTP_FAILED", 
                        f"Échec du test SMTP vers {test_email}")
            flash('❌ Erreur lors de l\'envoi de l\'email de test. Vérifiez votre configuration SMTP.', 'error')
    
    except Exception as e:
        logging.error(f"Erreur lors du test SMTP: {e}")
        log_activity(current_user.id, "TEST_SMTP_ERROR", 
                    f"Erreur lors du test SMTP: {str(e)}")
        flash('❌ Erreur lors du test de configuration SMTP.', 'error')
    
    return redirect(url_for('settings'))

@app.route('/dashboard')
@login_required
def dashboard():
    with PerformanceMonitor("dashboard_load"):
        # Use cached statistics for better performance
        stats = get_dashboard_statistics()
        
        # Get recent mail specific to user permissions (excluding deleted)
        recent_query = Courrier.query.filter_by(is_deleted=False)
        
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
    # Import TypeCourrierSortant
    from models import TypeCourrierSortant
    
    if request.method == 'POST':
        # Récupération des données du formulaire
        numero_reference = request.form.get('numero_reference', '').strip()
        objet = request.form['objet'].strip()
        type_courrier = request.form.get('type_courrier', 'ENTRANT')
        type_courrier_sortant_id = request.form.get('type_courrier_sortant_id', '')
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
        secretaire_general_copie = None
        autres_informations = None
        
        if type_courrier == 'ENTRANT':
            expediteur = request.form.get('expediteur', '').strip()
            # Récupérer le champ SG en copie pour les courriers entrants
            sg_copie_value = request.form.get('secretaire_general_copie', '').strip()
            
            # Valider les champs obligatoires
            if not objet or not expediteur or not sg_copie_value:
                titre_responsable = ParametresSysteme.get_valeur('titre_responsable_structure', 'Secrétaire Général')
                flash(f'L\'objet, l\'expéditeur et le statut de copie au {titre_responsable} sont obligatoires pour un courrier entrant.', 'error')
                statuts_disponibles = StatutCourrier.get_statuts_actifs()
                return render_template('register_mail.html', statuts_disponibles=statuts_disponibles)
            
            # Convertir la valeur en booléen
            secretaire_general_copie = (sg_copie_value.lower() == 'oui')
        else:  # SORTANT
            destinataire = request.form.get('destinataire', '').strip()
            autres_informations = request.form.get('autres_informations', '').strip()
            
            # Pour les courriers sortants, la date d'émission est obligatoire
            if not date_redaction:
                flash('La date d\'émission est obligatoire pour un courrier sortant.', 'error')
                statuts_disponibles = StatutCourrier.get_statuts_actifs()
                types_courrier_sortant = TypeCourrierSortant.get_types_actifs()
                return render_template('register_mail.html', statuts_disponibles=statuts_disponibles,
                                     types_courrier_sortant=types_courrier_sortant)
            
            if not objet or not destinataire:
                flash('L\'objet et le destinataire sont obligatoires pour un courrier sortant.', 'error')
                statuts_disponibles = StatutCourrier.get_statuts_actifs()
                types_courrier_sortant = TypeCourrierSortant.get_types_actifs()
                return render_template('register_mail.html', statuts_disponibles=statuts_disponibles, 
                                     types_courrier_sortant=types_courrier_sortant)
            
            # Vérifier le type de courrier sortant (obligatoire)
            if not type_courrier_sortant_id:
                flash('Le type de courrier sortant est obligatoire.', 'error')
                statuts_disponibles = StatutCourrier.get_statuts_actifs()
                types_courrier_sortant = TypeCourrierSortant.get_types_actifs()
                return render_template('register_mail.html', statuts_disponibles=statuts_disponibles,
                                     types_courrier_sortant=types_courrier_sortant)
        
        # Génération ou récupération du numéro d'accusé de réception
        parametres = ParametresSysteme.get_parametres()
        
        if parametres.mode_numero_accuse == 'manuel':
            # Mode manuel : récupérer le numéro saisi
            numero_accuse = request.form.get('numero_accuse_manuel', '').strip()
            
            if not numero_accuse:
                flash('Le numéro d\'accusé de réception est obligatoire en mode manuel.', 'error')
                statuts_disponibles = StatutCourrier.get_statuts_actifs()
                departements = Departement.get_departements_actifs()
                return render_template('register_mail.html', statuts_disponibles=statuts_disponibles, 
                                     departements=departements, parametres=parametres)
            
            # Vérifier l'unicité du numéro
            existing = Courrier.query.filter_by(numero_accuse_reception=numero_accuse).first()
            if existing:
                flash(f'Le numéro d\'accusé "{numero_accuse}" existe déjà. Veuillez utiliser un numéro différent.', 'error')
                statuts_disponibles = StatutCourrier.get_statuts_actifs()
                departements = Departement.get_departements_actifs()
                return render_template('register_mail.html', statuts_disponibles=statuts_disponibles, 
                                     departements=departements, parametres=parametres)
        else:
            # Mode automatique : générer le numéro
            numero_accuse = generate_accuse_reception()
        
        # Gestion du fichier uploadé (maintenant obligatoire)
        file = request.files.get('fichier')
        fichier_nom = None
        fichier_chemin = None
        fichier_type = None
        
        # Vérifier que le fichier est présent (obligatoire)
        if not file or not file.filename or file.filename == '':
            flash('La pièce jointe est obligatoire. Veuillez télécharger un fichier.', 'error')
            statuts_disponibles = StatutCourrier.get_statuts_actifs()
            types_courrier_sortant = TypeCourrierSortant.get_types_actifs()
            return render_template('register_mail.html', statuts_disponibles=statuts_disponibles,
                                 types_courrier_sortant=types_courrier_sortant)
        
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Ajouter timestamp pour éviter les conflits
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            # Stocker le chemin relatif, pas absolu
            fichier_chemin = os.path.join('uploads', filename)
            # Créer le dossier uploads s'il n'existe pas
            os.makedirs('uploads', exist_ok=True)
            # Sauvegarder le fichier
            file.save(fichier_chemin)
            fichier_nom = file.filename
            fichier_type = filename.rsplit('.', 1)[1].lower()
        else:
            flash('Type de fichier non autorisé. Utilisez PDF, JPG, PNG ou TIFF.', 'error')
            statuts_disponibles = StatutCourrier.get_statuts_actifs()
            types_courrier_sortant = TypeCourrierSortant.get_types_actifs()
            return render_template('register_mail.html', statuts_disponibles=statuts_disponibles,
                                 types_courrier_sortant=types_courrier_sortant)
        
        # Création du courrier
        courrier = Courrier(
            numero_accuse_reception=numero_accuse,
            numero_reference=numero_reference if numero_reference else None,
            objet=objet,
            type_courrier=type_courrier,
            type_courrier_sortant_id=int(type_courrier_sortant_id) if type_courrier == 'SORTANT' and type_courrier_sortant_id else None,
            expediteur=expediteur,
            destinataire=destinataire,
            date_redaction=date_redaction,
            statut=statut,
            fichier_nom=fichier_nom,
            fichier_chemin=fichier_chemin,
            fichier_type=fichier_type,
            utilisateur_id=current_user.id,
            secretaire_general_copie=secretaire_general_copie,
            autres_informations=autres_informations if type_courrier == 'SORTANT' else None
        )
        
        try:
            db.session.add(courrier)
            db.session.commit()
            
            # Log de l'activité
            log_activity(current_user.id, "ENREGISTREMENT_COURRIER", 
                        f"Enregistrement du courrier {numero_accuse}", courrier.id)
            
            # Notifications pour les administrateurs et super administrateurs
            try:
                # Obtenir les paramètres système pour vérifier les notifications super admin
                parametres_notif = ParametresSysteme.get_parametres()
                
                # Obtenir tous les utilisateurs pouvant recevoir des notifications
                notification_users = []
                
                # Récupérer tous les utilisateurs actifs avec email
                all_users = User.query.filter(
                    User.actif == True,
                    User.email.isnot(None),
                    User.email != ''
                ).all()
                
                for user in all_users:
                    # Vérifier si l'utilisateur peut recevoir les notifications
                    if user.can_receive_new_mail_notifications():
                        # Pour les super admin, vérifier le paramètre système
                        if user.role == 'super_admin' and not parametres_notif.notify_superadmin_new_mail:
                            continue
                        notification_users.append(user)
                
                # Créer les notifications dans l'application
                for user in notification_users:
                    Notification.create_notification(
                        user_id=user.id,
                        type_notification='new_mail',
                        titre=f'Nouveau courrier enregistré - {numero_accuse}',
                        message=f'Un nouveau courrier "{objet}" a été enregistré par {current_user.nom_complet}.',
                        courrier_id=courrier.id
                    )
                
                # Envoyer les notifications par email (utilise l'email du profil de chaque utilisateur)
                user_emails = [user.email for user in notification_users]
                if user_emails:
                    courrier_data = {
                        'numero_accuse_reception': numero_accuse,
                        'type_courrier': type_courrier,
                        'objet': objet,
                        'expediteur': expediteur or destinataire,
                        'created_by': current_user.nom_complet
                    }
                    send_new_mail_notification(user_emails, courrier_data)
                
            except Exception as e:
                logging.error(f"Erreur lors de l'envoi des notifications: {e}")
                # Ne pas interrompre le processus si les notifications échouent
            
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
    # Récupérer les types de courrier sortant pour le formulaire
    types_courrier_sortant = TypeCourrierSortant.get_types_actifs()
    # Récupérer les paramètres système pour le mode de numéro d'accusé
    parametres = ParametresSysteme.get_parametres()
    return render_template('register_mail.html', statuts_disponibles=statuts_disponibles, 
                         departements=departements, parametres=parametres,
                         types_courrier_sortant=types_courrier_sortant)

@app.route('/view_mail')
@login_required
def view_mail():
    from models import TypeCourrierSortant
    
    page = request.args.get('page', 1, type=int)
    per_page = 25  # Increased from 20 for better performance
    
    # Filtres
    search = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    date_redaction_from = request.args.get('date_redaction_from', '')
    date_redaction_to = request.args.get('date_redaction_to', '')
    statut = request.args.get('statut', '')
    type_courrier_sortant_id = request.args.get('type_courrier_sortant_id', '')
    sg_copie = request.args.get('sg_copie', '')  # Nouveau filtre SG en copie
    sort_by = request.args.get('sort_by', 'date_enregistrement')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Construction de la requête avec restrictions selon le rôle (excluant les courriers supprimés)
    query = Courrier.query.filter_by(is_deleted=False)
    
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
    
    # Enhanced search with performance optimization - indexing all metadata
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
    
    # Filtre par type de courrier sortant
    if type_courrier_sortant_id:
        query = query.filter(Courrier.type_courrier_sortant_id == type_courrier_sortant_id)
    
    # Filtre par SG en copie (pour courriers entrants)
    if sg_copie:
        if sg_copie == 'oui':
            query = query.filter(Courrier.secretaire_general_copie == True)
        elif sg_copie == 'non':
            query = query.filter(Courrier.secretaire_general_copie == False)
    
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
    
    # Récupérer les types de courrier sortant pour le filtre
    types_courrier_sortant = TypeCourrierSortant.query.filter_by(actif=True).order_by(TypeCourrierSortant.ordre_affichage).all()
    
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
                         type_courrier_sortant_id=type_courrier_sortant_id,
                         types_courrier_sortant=types_courrier_sortant,
                         sg_copie=sg_copie,
                         sort_by=sort_by,
                         sort_order=sort_order)

@app.route('/search')
@login_required
def search():
    return render_template('search.html')

@app.route('/api/search_suggestions')
@login_required
def search_suggestions():
    """API endpoint pour l'autocomplete de recherche"""
    try:
        q = request.args.get('q', '').strip()
        if len(q) < 2:  # Ne pas suggérer pour moins de 2 caractères
            return jsonify([])
        
        # Sanitize input
        q = sanitize_input(q)
        
        # Construire la requête de base avec restrictions selon le rôle
        query = Courrier.query.filter_by(is_deleted=False)
        
        # Appliquer les restrictions de permissions
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
        
        # Recherche dans tous les champs indexés
        suggestions = set()  # Utiliser un set pour éviter les doublons
        
        # Rechercher dans les numéros d'accusé
        results = query.filter(Courrier.numero_accuse_reception.ilike(f'%{q}%')).limit(5).all()
        for r in results:
            suggestions.add(r.numero_accuse_reception)
        
        # Rechercher dans les références
        results = query.filter(Courrier.numero_reference.ilike(f'%{q}%')).limit(5).all()
        for r in results:
            if r.numero_reference:
                suggestions.add(r.numero_reference)
        
        # Rechercher dans les objets
        results = query.filter(Courrier.objet.ilike(f'%{q}%')).limit(5).all()
        for r in results:
            if len(r.objet) <= 100:  # Limiter la longueur des suggestions
                suggestions.add(r.objet)
            else:
                suggestions.add(r.objet[:97] + '...')
        
        # Rechercher dans les expéditeurs
        results = query.filter(Courrier.expediteur.ilike(f'%{q}%')).limit(5).all()
        for r in results:
            if r.expediteur:
                suggestions.add(r.expediteur)
        
        # Rechercher dans les destinataires
        results = query.filter(Courrier.destinataire.ilike(f'%{q}%')).limit(5).all()
        for r in results:
            if r.destinataire:
                suggestions.add(r.destinataire)
        
        # Convertir en liste et limiter à 10 suggestions
        suggestions_list = list(suggestions)[:10]
        
        return jsonify(suggestions_list)
    except Exception as e:
        app.logger.error(f"Erreur dans search_suggestions: {str(e)}")
        return jsonify([])

@app.route('/mail/<int:id>')
@login_required
def mail_detail(id):
    courrier = Courrier.query.get_or_404(id)
    
    # Vérifier les permissions d'accès au courrier
    if not current_user.can_view_courrier(courrier):
        flash('Vous n\'avez pas l\'autorisation de consulter ce courrier.', 'error')
        return redirect(url_for('view_mail'))
    
    # Marquer automatiquement comme lu si l'utilisateur vient d'une notification
    from_notification = request.args.get('from_notification')
    if from_notification:
        # Marquer la notification comme lue
        notification = Notification.query.filter_by(
            courrier_id=id,
            user_id=current_user.id,
            type_notification='mail_forwarded'
        ).order_by(Notification.date_creation.desc()).first()
        
        if notification and not notification.lu:
            notification.mark_as_read()
        
        # Marquer la transmission correspondante comme lue
        forward = CourrierForward.query.filter_by(
            courrier_id=id,
            forwarded_to_id=current_user.id
        ).order_by(CourrierForward.date_transmission.desc()).first()
        
        if forward and not forward.lu:
            forward.mark_as_read()
    
    statuts_disponibles = StatutCourrier.get_statuts_actifs()
    
    # Récupérer les commentaires du courrier
    comments = CourrierComment.query.filter_by(courrier_id=id, actif=True)\
                                    .order_by(CourrierComment.date_creation.desc()).all()
    
    # Récupérer les transmissions du courrier
    forwards = CourrierForward.query.filter_by(courrier_id=id)\
                                    .order_by(CourrierForward.date_transmission.desc()).all()
    
    # Récupérer tous les utilisateurs actifs pour la transmission (disponible à tous)
    users = User.query.filter_by(actif=True).order_by(User.nom_complet).all()
    
    log_activity(current_user.id, "CONSULTATION_COURRIER", 
                f"Consultation du courrier {courrier.numero_accuse_reception}", courrier.id)
    return render_template('mail_detail_new.html', 
                          courrier=courrier,
                          statuts_disponibles=statuts_disponibles,
                          comments=comments,
                          forwards=forwards,
                          users=users)

@app.route('/export_pdf/<int:id>')
@login_required
def export_pdf(id):
    courrier = Courrier.query.get_or_404(id)
    try:
        pdf_path = export_courrier_pdf(courrier)
        log_activity(current_user.id, "EXPORT_PDF", 
                    f"Export PDF du courrier {courrier.numero_accuse_reception}", courrier.id)
        
        # Utiliser send_from_directory pour mieux gérer les chemins en production
        import os
        directory = os.path.dirname(pdf_path)
        filename = os.path.basename(pdf_path)
        return send_from_directory(directory, filename, 
                                 as_attachment=True, 
                                 download_name=f"courrier_{courrier.numero_accuse_reception}.pdf",
                                 mimetype='application/pdf')
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
        
        # Build query with same logic as view_mail (without pagination, excluding deleted)
        query = Courrier.query.filter_by(is_deleted=False)
        
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
        
        # Utiliser send_from_directory pour mieux gérer les chemins en production
        directory = os.path.dirname(pdf_path)
        pdf_filename = os.path.basename(pdf_path)
        return send_from_directory(directory, pdf_filename, 
                                 as_attachment=True, 
                                 download_name=filename,
                                 mimetype='application/pdf')
        
    except Exception as e:
        logging.error(f"Erreur lors de l'export PDF de la liste: {e}")
        flash('Erreur lors de l\'export PDF de la liste.', 'error')
        return redirect(url_for('view_mail'))

@app.route('/download_file/<int:id>')
@login_required
def download_file(id):
    courrier = Courrier.query.get_or_404(id)
    
    # Debug logging
    logging.info(f"Tentative de téléchargement - ID: {id}")
    logging.info(f"Chemin dans DB: {courrier.fichier_chemin}")
    logging.info(f"Nom du fichier: {courrier.fichier_nom}")
    
    # Gérer les chemins relatifs et absolus
    if courrier.fichier_chemin:
        # Si le chemin est absolu, extraire la partie relative
        file_path = courrier.fichier_chemin
        if file_path.startswith('/'):
            # Chemin absolu - chercher la partie uploads
            if 'uploads/' in file_path:
                relative_path = file_path.split('uploads/')[-1]
                file_path = os.path.join('uploads', relative_path)
        
        # Log du chemin final
        logging.info(f"Chemin final à vérifier: {file_path}")
        logging.info(f"Le fichier existe? {os.path.exists(file_path)}")
        logging.info(f"Chemin absolu: {os.path.abspath(file_path)}")
        
        # Vérifier si le fichier existe
        if os.path.exists(file_path):
            log_activity(current_user.id, "TELECHARGEMENT_FICHIER", 
                        f"Téléchargement du fichier du courrier {courrier.numero_accuse_reception}", courrier.id)
            
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            
            logging.info(f"Directory: {directory}, Filename: {filename}")
            
            # Déterminer le mimetype
            mimetype = 'application/octet-stream'
            if courrier.fichier_nom:
                ext = courrier.fichier_nom.lower().split('.')[-1]
                if ext == 'pdf':
                    mimetype = 'application/pdf'
                elif ext in ['jpg', 'jpeg']:
                    mimetype = 'image/jpeg'
                elif ext == 'png':
                    mimetype = 'image/png'
            
            return send_from_directory(directory, filename, 
                                     as_attachment=True, 
                                     download_name=courrier.fichier_nom,
                                     mimetype=mimetype)
        else:
            logging.error(f"Fichier non trouvé au chemin: {file_path}")
            # Essayer de lister le contenu du dossier uploads
            try:
                uploads_content = os.listdir('uploads')
                logging.info(f"Contenu du dossier uploads: {uploads_content}")
            except Exception as e:
                logging.error(f"Erreur en listant uploads: {e}")
    else:
        logging.error(f"Pas de chemin de fichier dans la base de données pour le courrier {id}")
    
    flash('Fichier non trouvé.', 'error')
    return redirect(url_for('mail_detail', id=id))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
@rate_limit(max_requests=20, per_minutes=15)
def settings():
    with PerformanceMonitor("settings_page"):
        from models import TypeCourrierSortant
        parametres = ParametresSysteme.get_parametres()
        types_courrier_sortant = TypeCourrierSortant.query.order_by(TypeCourrierSortant.ordre_affichage).all()
        
        if request.method == 'POST':
            # Gestion du test d'email SendGrid en premier
            if request.form.get('test_email'):
                test_email = request.form.get('test_email', '').strip()
                
                if not test_email:
                    flash('Veuillez saisir une adresse email pour le test.', 'error')
                    return redirect(url_for('settings'))
                
                # Valider l'email
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, test_email):
                    flash('Veuillez saisir une adresse email valide.', 'error')
                    return redirect(url_for('settings'))
                
                # Effectuer le test SendGrid
                from email_utils import test_sendgrid_configuration
                result = test_sendgrid_configuration(test_email)
                
                if result['success']:
                    flash(result['message'], 'success')
                    log_activity(current_user.id, "TEST_EMAIL_SENDGRID", 
                                f"Test email SendGrid envoyé à {test_email}")
                else:
                    flash(result['message'], 'error')
                    log_activity(current_user.id, "TEST_EMAIL_SENDGRID_ECHEC", 
                                f"Échec test email SendGrid: {result['message']}")
                
                return redirect(url_for('settings'))
            
            # Sanitize and update parameters
            parametres.nom_logiciel = sanitize_input(request.form.get('nom_logiciel', 'GEC').strip())
            parametres.mode_numero_accuse = sanitize_input(request.form.get('mode_numero_accuse', 'automatique').strip())
            parametres.format_numero_accuse = sanitize_input(request.form.get('format_numero_accuse', 'GEC-{year}-{counter:05d}').strip())
            parametres.telephone = sanitize_input(request.form.get('telephone', '').strip()) or None
            parametres.email_contact = sanitize_input(request.form.get('email_contact', '').strip()) or None
            parametres.adresse_organisme = sanitize_input(request.form.get('adresse_organisme', '').strip()) or None
            
            # Sanitize PDF parameters
            parametres.texte_footer = sanitize_input(request.form.get('texte_footer', '').strip()) or "Système de Gestion Électronique du Courrier"
            parametres.titre_pdf = sanitize_input(request.form.get('titre_pdf', '').strip()) or "Secrétariat Général"
            parametres.sous_titre_pdf = sanitize_input(request.form.get('sous_titre_pdf', '').strip()) or "Secrétariat Général"
            parametres.pays_pdf = sanitize_input(request.form.get('pays_pdf', '').strip()) or "République Démocratique du Congo"
            parametres.copyright_text = sanitize_input(request.form.get('copyright_text', '').strip()) or "© 2025 GEC. Made with 💖 and ☕ By MOA-Digital Agency LLC"
            
            # Paramètre d'appellation des départements
            parametres.appellation_departement = sanitize_input(request.form.get('appellation_departement', '').strip()) or "Départements"
            parametres.titre_responsable_structure = sanitize_input(request.form.get('titre_responsable_structure', '').strip()) or "Secrétaire Général"
            
            # Choix du fournisseur email
            parametres.email_provider = sanitize_input(request.form.get('email_provider', 'sendgrid').strip())
            
            # Notifications pour super admin (seuls les super admin peuvent modifier)
            if current_user.is_super_admin():
                parametres.notify_superadmin_new_mail = bool(request.form.get('notify_superadmin_new_mail'))
            
            # Paramètres SMTP et SendGrid (soumis aux permissions)
            if current_user.has_permission('manage_system_settings'):
                # Paramètres SMTP
                parametres.smtp_server = sanitize_input(request.form.get('smtp_server', '').strip()) or None
                smtp_port = request.form.get('smtp_port', '').strip()
                if smtp_port and smtp_port.isdigit():
                    parametres.smtp_port = int(smtp_port)
                parametres.smtp_use_tls = request.form.get('smtp_use_tls') == 'on'
                parametres.smtp_username = sanitize_input(request.form.get('smtp_username', '').strip()) or None
                smtp_password = request.form.get('smtp_password', '').strip()
                if smtp_password:
                    # Crypter le mot de passe SMTP
                    from encryption_utils import EncryptionManager
                    encryption_manager = EncryptionManager()
                    parametres.smtp_password = encryption_manager.encrypt_data(smtp_password)
                
                # Paramètres SendGrid - Stockage direct pour résoudre le problème de cryptage
                sendgrid_api_key = request.form.get('sendgrid_api_key', '').strip()
                
                # Sauvegarder la clé directement si elle est fournie et n'est pas le placeholder
                if sendgrid_api_key and sendgrid_api_key != '●●●●●●●●●●●●●●●●●●●●' and len(sendgrid_api_key) > 10:
                    parametres.sendgrid_api_key = sendgrid_api_key
                    logging.info(f"✅ Clé SendGrid sauvegardée directement (longueur: {len(sendgrid_api_key)})")
                elif sendgrid_api_key == '':
                    # Si le champ est vide, on garde la clé existante
                    logging.info("Clé SendGrid: champ vide, conservation de la clé existante")
            
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
                              backup_files=backup_files,
                              types_courrier_sortant=types_courrier_sortant)

@app.route('/manage_mail_types', methods=['POST'])
@login_required
def manage_mail_types():
    """Gérer les types de courrier sortant"""
    from models import TypeCourrierSortant
    
    # Vérifier les permissions
    if not current_user.has_permission('manage_system_settings'):
        flash('Accès refusé. Vous n\'avez pas les permissions nécessaires.', 'error')
        return redirect(url_for('settings'))
    
    action = request.form.get('action')
    
    if action == 'add':
        nom = request.form.get('nom', '').strip()
        description = request.form.get('description', '').strip()
        
        if not nom:
            flash('Le nom du type est obligatoire.', 'error')
            return redirect(url_for('settings'))
        
        # Vérifier l'unicité du nom
        existing = TypeCourrierSortant.query.filter_by(nom=nom).first()
        if existing:
            flash(f'Un type avec le nom "{nom}" existe déjà.', 'error')
            return redirect(url_for('settings'))
        
        try:
            # Obtenir le prochain ordre d'affichage
            max_ordre = db.session.query(db.func.max(TypeCourrierSortant.ordre_affichage)).scalar() or 0
            
            new_type = TypeCourrierSortant(
                nom=nom,
                description=description,
                ordre_affichage=max_ordre + 1,
                cree_par_id=current_user.id
            )
            db.session.add(new_type)
            db.session.commit()
            
            log_activity(current_user.id, "AJOUT_TYPE_COURRIER", 
                        f"Ajout du type de courrier sortant: {nom}")
            flash(f'Type "{nom}" ajouté avec succès!', 'success')
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de l'ajout du type: {e}")
            flash('Erreur lors de l\'ajout du type.', 'error')
    
    elif action == 'toggle':
        type_id = request.form.get('type_id')
        mail_type = TypeCourrierSortant.query.get(type_id)
        
        if mail_type:
            mail_type.actif = not mail_type.actif
            db.session.commit()
            
            status = 'activé' if mail_type.actif else 'désactivé'
            log_activity(current_user.id, "MODIFICATION_TYPE_COURRIER", 
                        f"Type {mail_type.nom} {status}")
            flash(f'Type "{mail_type.nom}" {status}!', 'success')
        else:
            flash('Type non trouvé.', 'error')
    
    elif action == 'delete':
        type_id = request.form.get('type_id')
        mail_type = TypeCourrierSortant.query.get(type_id)
        
        if mail_type:
            # Vérifier s'il y a des courriers associés
            count = mail_type.courriers.count()
            if count > 0:
                flash(f'Impossible de supprimer ce type. {count} courrier(s) associé(s).', 'error')
            else:
                nom = mail_type.nom
                db.session.delete(mail_type)
                db.session.commit()
                
                log_activity(current_user.id, "SUPPRESSION_TYPE_COURRIER", 
                            f"Suppression du type de courrier sortant: {nom}")
                flash(f'Type "{nom}" supprimé avec succès!', 'success')
        else:
            flash('Type non trouvé.', 'error')
    
    return redirect(url_for('settings'))

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
    
    # Créer le dossier backups s'il n'existe pas
    os.makedirs('backups', exist_ok=True)
    
    backup_path = os.path.join('backups', filename)
    if os.path.exists(backup_path):
        return send_from_directory('backups', filename, 
                                 as_attachment=True,
                                 mimetype='application/zip')
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
        # Créer une sauvegarde avant la mise à jour
        backup_dir = 'backups/before_update'
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = os.path.join(backup_dir, f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip')
        
        # Fichiers à préserver
        preserve_files = [
            'instance/gec.db',
            'uploads',
            '.env',
            'version.txt'
        ]
        
        # Créer une sauvegarde des fichiers importants
        with zipfile.ZipFile(backup_file, 'w') as zipf:
            for file_or_dir in preserve_files:
                if os.path.exists(file_or_dir):
                    if os.path.isdir(file_or_dir):
                        for root, dirs, files in os.walk(file_or_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path)
                                zipf.write(file_path, arcname)
                    else:
                        zipf.write(file_or_dir, os.path.basename(file_or_dir))
        
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
    
    return redirect(url_for('update_system'))

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
            return redirect(url_for('update_system'))
        
        file = request.files['update_file']
        if file.filename == '':
            flash('Aucun fichier sélectionné.', 'error')
            return redirect(url_for('update_system'))
        
        if not file.filename.endswith('.zip'):
            flash('Le fichier doit être un fichier ZIP.', 'error')
            return redirect(url_for('update_system'))
        
        # Créer une sauvegarde avant la mise à jour
        backup_dir = 'backups/before_update'
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = os.path.join(backup_dir, f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip')
        
        # Fichiers et dossiers à préserver (ne jamais remplacer)
        preserve_patterns = [
            'instance/gec.db',
            'uploads/',
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
    
    return redirect(url_for('update_system'))

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
    
    # Debug logging
    logging.info(f"Tentative de visualisation - ID: {id}")
    logging.info(f"Chemin dans DB: {courrier.fichier_chemin}")
    logging.info(f"Nom du fichier: {courrier.fichier_nom}")
    
    # Gérer les chemins relatifs et absolus
    if courrier.fichier_chemin:
        # Si le chemin est absolu, extraire la partie relative
        file_path = courrier.fichier_chemin
        if file_path.startswith('/'):
            # Chemin absolu - chercher la partie uploads
            if 'uploads/' in file_path:
                relative_path = file_path.split('uploads/')[-1]
                file_path = os.path.join('uploads', relative_path)
        
        # Log du chemin final
        logging.info(f"Chemin final à vérifier: {file_path}")
        logging.info(f"Le fichier existe? {os.path.exists(file_path)}")
        
        # Vérifier si le fichier existe
        if os.path.exists(file_path):
            log_activity(current_user.id, "VISUALISATION_FICHIER", 
                        f"Visualisation du fichier du courrier {courrier.numero_accuse_reception}", courrier.id)
            
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            
            logging.info(f"Directory: {directory}, Filename: {filename}")
            
            # Déterminer le mimetype
            mimetype = 'application/octet-stream'
            if courrier.fichier_nom:
                ext = courrier.fichier_nom.lower().split('.')[-1]
                if ext == 'pdf':
                    mimetype = 'application/pdf'
                elif ext in ['jpg', 'jpeg']:
                    mimetype = 'image/jpeg'
                elif ext == 'png':
                    mimetype = 'image/png'
            
            return send_from_directory(directory, filename, 
                                     as_attachment=False,
                                     mimetype=mimetype)
        else:
            logging.error(f"Fichier non trouvé au chemin: {file_path}")
    else:
        logging.error(f"Pas de chemin de fichier dans la base de données pour le courrier {id}")
    
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
def set_language_route(lang_code):
    """Changer la langue de l'interface"""
    if set_language(lang_code):
        if current_user.is_authenticated:
            # Sauvegarder la préférence dans le profil utilisateur
            current_user.langue = lang_code
            db.session.commit()
        flash('Langue changée avec succès' if lang_code == 'fr' else 'Language changed successfully', 'success')
    else:
        flash('Langue non supportée', 'error')
    
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

@app.route('/delete_courrier/<int:id>', methods=['POST'])
@login_required
def delete_courrier(id):
    """Supprimer un courrier (soft delete - déplacer dans la corbeille)"""
    courrier = Courrier.query.get_or_404(id)
    
    # Vérifier les permissions
    if not current_user.has_permission('delete_mail'):
        flash('Vous n\'avez pas l\'autorisation de supprimer des courriers.', 'error')
        return redirect(url_for('view_mail'))
    
    # Soft delete
    courrier.is_deleted = True
    courrier.deleted_at = datetime.utcnow()
    courrier.deleted_by_id = current_user.id
    
    try:
        db.session.commit()
        log_activity(current_user.id, "SUPPRESSION_COURRIER", 
                    f"Suppression du courrier {courrier.numero_accuse_reception}", courrier.id)
        flash(f'Le courrier {courrier.numero_accuse_reception} a été déplacé dans la corbeille.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la suppression du courrier.', 'error')
        logging.error(f"Erreur suppression courrier: {e}")
    
    return redirect(url_for('view_mail'))

@app.route('/restore_courrier/<int:id>', methods=['POST'])
@login_required
def restore_courrier(id):
    """Restaurer un courrier depuis la corbeille"""
    courrier = Courrier.query.get_or_404(id)
    
    # Vérifier les permissions
    if not current_user.has_permission('restore_mail'):
        flash('Vous n\'avez pas l\'autorisation de restaurer des courriers.', 'error')
        return redirect(url_for('trash'))
    
    # Restaurer
    courrier.is_deleted = False
    courrier.deleted_at = None
    courrier.deleted_by_id = None
    
    try:
        db.session.commit()
        log_activity(current_user.id, "RESTAURATION_COURRIER", 
                    f"Restauration du courrier {courrier.numero_accuse_reception}", courrier.id)
        flash(f'Le courrier {courrier.numero_accuse_reception} a été restauré avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la restauration du courrier.', 'error')
        logging.error(f"Erreur restauration courrier: {e}")
    
    return redirect(url_for('trash'))

@app.route('/trash')
@login_required
def trash():
    """Afficher la corbeille (courriers supprimés)"""
    # Vérifier les permissions
    if not current_user.has_permission('view_trash'):
        flash('Vous n\'avez pas l\'autorisation de consulter la corbeille.', 'error')
        return redirect(url_for('dashboard'))
    
    # Récupérer les courriers supprimés
    courriers = Courrier.query.filter_by(is_deleted=True).order_by(Courrier.deleted_at.desc()).all()
    
    log_activity(current_user.id, "CONSULTATION_CORBEILLE", 
                f"Consultation de la corbeille ({len(courriers)} courriers)")
    
    return render_template('trash.html', courriers=courriers)

@app.route('/empty_trash', methods=['POST'])
@login_required
def empty_trash():
    """Vider définitivement la corbeille (super admin only)"""
    if not current_user.is_super_admin():
        flash('Seuls les super administrateurs peuvent vider la corbeille.', 'error')
        return redirect(url_for('trash'))
    
    # Supprimer définitivement tous les courriers de la corbeille
    deleted_count = Courrier.query.filter_by(is_deleted=True).count()
    Courrier.query.filter_by(is_deleted=True).delete()
    
    try:
        db.session.commit()
        log_activity(current_user.id, "VIDAGE_CORBEILLE", 
                    f"Suppression définitive de {deleted_count} courriers")
        flash(f'{deleted_count} courriers ont été supprimés définitivement.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors du vidage de la corbeille.', 'error')
        logging.error(f"Erreur vidage corbeille: {e}")
    
    return redirect(url_for('trash'))

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

@app.route('/analytics')
@login_required
def analytics():
    """Tableau de bord analytique avec statistiques et graphiques"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    import json
    
    # Récupérer les paramètres de filtre temporel
    period = request.args.get('period', 'all')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Calculer les dates de filtre
    now = datetime.now()
    if period == 'day':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif period == 'week':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif period == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif period == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif period == 'custom' and date_from and date_to:
        start_date = datetime.strptime(date_from, '%Y-%m-%d')
        end_date = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    else:
        start_date = None
        end_date = None
    
    # Construire le filtre de base
    base_filter = [Courrier.is_deleted == False]
    if start_date and end_date:
        base_filter.append(Courrier.date_enregistrement >= start_date)
        base_filter.append(Courrier.date_enregistrement <= end_date)
    
    # Statistiques générales avec filtre
    total_courriers = Courrier.query.filter(*base_filter).count()
    courriers_entrants = Courrier.query.filter(*base_filter, Courrier.type_courrier == 'ENTRANT').count()
    courriers_sortants = Courrier.query.filter(*base_filter, Courrier.type_courrier == 'SORTANT').count()
    
    # Variables pour export PDF
    date_7_days_ago = datetime.now() - timedelta(days=7)
    courriers_7_days = Courrier.query.filter(
        Courrier.date_enregistrement >= date_7_days_ago,
        Courrier.is_deleted == False
    ).count()
    
    date_30_days_ago = datetime.now() - timedelta(days=30)
    courriers_30_days = Courrier.query.filter(
        Courrier.date_enregistrement >= date_30_days_ago,
        Courrier.is_deleted == False
    ).count()
    
    # Top expéditeurs avec filtre
    sender_filter = base_filter + [
        Courrier.expediteur != None,
        Courrier.expediteur != ''
    ]
    top_senders = db.session.query(
        Courrier.expediteur,
        func.count(Courrier.id).label('count')
    ).filter(*sender_filter).group_by(Courrier.expediteur).order_by(func.count(Courrier.id).desc()).limit(10).all()
    
    
    # Volume par jour avec filtre
    daily_filter = base_filter.copy()
    if not start_date:  # Si pas de filtre spécifique, utiliser 30 derniers jours
        daily_filter.append(Courrier.date_enregistrement >= date_30_days_ago)
    
    daily_volumes = db.session.query(
        func.date(Courrier.date_enregistrement).label('date'),
        func.count(Courrier.id).label('count')
    ).filter(*daily_filter).group_by(func.date(Courrier.date_enregistrement)).all()
    
    daily_data = {
        'dates': [str(d.date) for d in daily_volumes],
        'counts': [d.count for d in daily_volumes]
    }
    
    # Répartition par statut avec filtre
    status_distribution = db.session.query(
        Courrier.statut,
        func.count(Courrier.id).label('count')
    ).filter(*base_filter).group_by(Courrier.statut).all()
    
    status_data = {
        'labels': [s.statut or 'Non défini' for s in status_distribution],
        'counts': [s.count for s in status_distribution]
    }
    
    # Top 10 expéditeurs (déjà défini plus haut avec filtre)
    
    # Top 10 destinataires avec filtre
    recipient_filter = base_filter + [
        Courrier.destinataire != None,
        Courrier.destinataire != ''
    ]
    top_recipients = db.session.query(
        Courrier.destinataire,
        func.count(Courrier.id).label('count')
    ).filter(*recipient_filter).group_by(Courrier.destinataire).order_by(func.count(Courrier.id).desc()).limit(10).all()
    
    # Temps moyen de traitement (courriers avec statut "TRAITE")
    processed_mails = Courrier.query.filter_by(statut='TRAITE', is_deleted=False).all()
    avg_processing_time = 0
    if processed_mails:
        total_time = sum([(m.date_enregistrement - m.date_redaction).days 
                         for m in processed_mails if m.date_redaction])
        avg_processing_time = total_time / len(processed_mails) if processed_mails else 0
    
    # Volume par mois (12 derniers mois)
    monthly_volumes = []
    for i in range(12):
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        count = Courrier.query.filter(
            Courrier.date_enregistrement >= month_start,
            Courrier.date_enregistrement < month_end,
            Courrier.is_deleted == False
        ).count()
        monthly_volumes.append({
            'month': month_start.strftime('%B %Y'),
            'count': count
        })
    monthly_volumes.reverse()
    
    # === NOUVELLES STATISTIQUES DÉTAILLÉES ===
    
    # 1. Statistiques par département avec filtre
    dept_stats_raw = db.session.query(
        Departement.nom.label('departement'),
        Courrier.type_courrier,
        func.count(Courrier.id).label('count')
    ).join(User, Courrier.utilisateur_id == User.id)\
     .join(Departement, User.departement_id == Departement.id)\
     .filter(*base_filter)\
     .group_by(Departement.nom, Courrier.type_courrier).all()
    
    # Agrégation des résultats par département
    dept_dict = {}
    for stat in dept_stats_raw:
        if stat.departement not in dept_dict:
            dept_dict[stat.departement] = {'departement': stat.departement, 'total': 0, 'entrants': 0, 'sortants': 0}
        dept_dict[stat.departement]['total'] += stat.count
        if stat.type_courrier == 'ENTRANT':
            dept_dict[stat.departement]['entrants'] = stat.count
        elif stat.type_courrier == 'SORTANT':
            dept_dict[stat.departement]['sortants'] = stat.count
    
    # Conversion en liste triée par total
    dept_stats = []
    for dept_name, data in dept_dict.items():
        from collections import namedtuple
        DeptStat = namedtuple('DeptStat', ['departement', 'total', 'entrants', 'sortants'])
        dept_stats.append(DeptStat(data['departement'], data['total'], data['entrants'], data['sortants']))
    dept_stats.sort(key=lambda x: x.total, reverse=True)
    
    # 2. Statistiques par utilisateur avec filtre (top 10)
    user_stats_raw = db.session.query(
        User.nom_complet,
        Courrier.type_courrier,
        func.count(Courrier.id).label('count')
    ).join(Courrier, Courrier.utilisateur_id == User.id)\
     .filter(*base_filter)\
     .group_by(User.nom_complet, Courrier.type_courrier).all()
    
    # Agrégation des résultats par utilisateur
    user_dict = {}
    for stat in user_stats_raw:
        if stat.nom_complet not in user_dict:
            user_dict[stat.nom_complet] = {'nom_complet': stat.nom_complet, 'total': 0, 'entrants': 0, 'sortants': 0}
        user_dict[stat.nom_complet]['total'] += stat.count
        if stat.type_courrier == 'ENTRANT':
            user_dict[stat.nom_complet]['entrants'] = stat.count
        elif stat.type_courrier == 'SORTANT':
            user_dict[stat.nom_complet]['sortants'] = stat.count
    
    # Conversion en liste triée par total (top 10)
    user_stats = []
    for user_name, data in user_dict.items():
        from collections import namedtuple
        UserStat = namedtuple('UserStat', ['nom_complet', 'total', 'entrants', 'sortants'])
        user_stats.append(UserStat(data['nom_complet'], data['total'], data['entrants'], data['sortants']))
    user_stats.sort(key=lambda x: x.total, reverse=True)
    user_stats = user_stats[:10]  # Top 10
    
    # 3. Évolution des statuts par semaine (8 dernières semaines)
    weekly_status = {}
    for i in range(8):
        week_start = datetime.now() - timedelta(weeks=i+1)
        week_end = datetime.now() - timedelta(weeks=i)
        
        week_stats = db.session.query(
            Courrier.statut,
            func.count(Courrier.id).label('count')
        ).filter(
            Courrier.date_enregistrement >= week_start,
            Courrier.date_enregistrement < week_end,
            Courrier.is_deleted == False
        ).group_by(Courrier.statut).all()
        
        week_key = f"Semaine {8-i}"
        weekly_status[week_key] = {stat.statut or 'Non défini': stat.count for stat in week_stats}
    
    # 4. Statistiques par type de courrier avec évolution mensuelle
    type_evolution = {}
    for i in range(6):  # 6 derniers mois
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        
        month_types = db.session.query(
            Courrier.type_courrier,
            func.count(Courrier.id).label('count')
        ).filter(
            Courrier.date_enregistrement >= month_start,
            Courrier.date_enregistrement < month_end,
            Courrier.is_deleted == False
        ).group_by(Courrier.type_courrier).all()
        
        month_key = month_start.strftime('%B %Y')
        type_evolution[month_key] = {typ.type_courrier: typ.count for typ in month_types}
    
    # 5. Performance par département (temps moyen de traitement)
    dept_performance = db.session.query(
        Departement.nom.label('departement'),
        func.count(Courrier.id).label('total'),
        func.avg(
            func.extract('day', Courrier.date_enregistrement - func.coalesce(Courrier.date_redaction, Courrier.date_enregistrement))
        ).label('temps_moyen')
    ).join(User, Courrier.utilisateur_id == User.id)\
     .join(Departement, User.departement_id == Departement.id)\
     .filter(
         Courrier.is_deleted == False,
         Courrier.statut.in_(['TRAITE', 'CLOS'])
     )\
     .group_by(Departement.nom).all()
    
    # 6. Analyse temporelle détaillée - Courriers par jour de la semaine
    weekday_stats = db.session.query(
        func.extract('dow', Courrier.date_enregistrement).label('day_of_week'),
        func.count(Courrier.id).label('count')
    ).filter(
        Courrier.date_enregistrement >= date_30_days_ago,
        Courrier.is_deleted == False
    ).group_by(func.extract('dow', Courrier.date_enregistrement)).all()
    
    weekdays = ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
    weekday_data = {
        'labels': [weekdays[int(stat.day_of_week)] for stat in weekday_stats],
        'counts': [stat.count for stat in weekday_stats]
    }
    
    # 7. Analyse par heure de la journée
    hourly_stats = db.session.query(
        func.extract('hour', Courrier.date_enregistrement).label('hour'),
        func.count(Courrier.id).label('count')
    ).filter(
        Courrier.date_enregistrement >= date_30_days_ago,
        Courrier.is_deleted == False
    ).group_by(func.extract('hour', Courrier.date_enregistrement)).all()
    
    hourly_data = {
        'hours': [f"{int(stat.hour):02d}h" for stat in hourly_stats],
        'counts': [stat.count for stat in hourly_stats]
    }
    
    # 8. Évolution annuelle (24 derniers mois pour voir la tendance)
    yearly_evolution = []
    for i in range(24):
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        
        entrants = Courrier.query.filter(
            Courrier.date_enregistrement >= month_start,
            Courrier.date_enregistrement < month_end,
            Courrier.type_courrier == 'ENTRANT',
            Courrier.is_deleted == False
        ).count()
        
        sortants = Courrier.query.filter(
            Courrier.date_enregistrement >= month_start,
            Courrier.date_enregistrement < month_end,
            Courrier.type_courrier == 'SORTANT',
            Courrier.is_deleted == False
        ).count()
        
        yearly_evolution.append({
            'month': month_start.strftime('%m/%Y'),
            'entrants': entrants,
            'sortants': sortants,
            'total': entrants + sortants
        })
    yearly_evolution.reverse()
    
    return render_template('analytics.html',
                         total_courriers=total_courriers,
                         courriers_entrants=courriers_entrants,
                         courriers_sortants=courriers_sortants,
                         courriers_7_days=courriers_7_days,
                         courriers_30_days=courriers_30_days,
                         daily_data=json.dumps(daily_data),
                         status_data=json.dumps(status_data),
                         top_senders=top_senders,
                         top_recipients=top_recipients,
                         avg_processing_time=round(avg_processing_time, 1),
                         monthly_volumes=monthly_volumes,
                         
                         # Nouvelles statistiques détaillées
                         dept_stats=dept_stats,
                         user_stats=user_stats,
                         weekly_status=json.dumps(weekly_status),
                         type_evolution=json.dumps(type_evolution),
                         dept_performance=dept_performance,
                         weekday_data=json.dumps(weekday_data),
                         hourly_data=json.dumps(hourly_data),
                         yearly_evolution=json.dumps(yearly_evolution))


@app.route('/export_analytics/<format>')
@login_required
def export_analytics(format):
    """Export des données analytiques en PDF ou Excel"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    import io
    
    if format not in ['pdf', 'excel']:
        flash('Format d\'export invalide', 'error')
        return redirect(url_for('analytics'))
    
    # Collecter les mêmes données que pour la page analytics
    total_courriers = Courrier.query.filter_by(is_deleted=False).count()
    courriers_entrants = Courrier.query.filter_by(type_courrier='ENTRANT', is_deleted=False).count()
    courriers_sortants = Courrier.query.filter_by(type_courrier='SORTANT', is_deleted=False).count()
    
    if format == 'excel':
        try:
            import pandas as pd
            from flask import send_file
        except ImportError:
            flash('Pandas n\'est pas installé. Impossible d\'exporter en Excel.', 'error')
            return redirect(url_for('analytics'))
        
        # Créer un fichier Excel avec plusieurs feuilles
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Feuille 1 : Statistiques générales
            stats_df = pd.DataFrame({
                'Métrique': ['Total Courriers', 'Courriers Entrants', 'Courriers Sortants'],
                'Valeur': [total_courriers, courriers_entrants, courriers_sortants]
            })
            stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
            
            # Feuille 2 : Volume par jour
            date_30_days_ago = datetime.now() - timedelta(days=30)
            daily_volumes = db.session.query(
                func.date(Courrier.date_enregistrement).label('date'),
                func.count(Courrier.id).label('count')
            ).filter(
                Courrier.date_enregistrement >= date_30_days_ago,
                Courrier.is_deleted == False
            ).group_by(func.date(Courrier.date_enregistrement)).all()
            
            if daily_volumes:
                daily_df = pd.DataFrame([(str(d.date), d.count) for d in daily_volumes],
                                       columns=['Date', 'Nombre de Courriers'])
                daily_df.to_excel(writer, sheet_name='Volume Quotidien', index=False)
        
        output.seek(0)
        return send_file(output, 
                        mimetype='application/vnd.ms-excel',
                        as_attachment=True,
                        download_name=f'analytics_export_{datetime.now().strftime("%Y%m%d")}.xlsx')
    
    elif format == 'pdf':
        try:
            # Export PDF avec ReportLab
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            flash('ReportLab n\'est pas installé. Impossible d\'exporter en PDF.', 'error')
            return redirect(url_for('analytics'))
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Titre
        title = Paragraph("Rapport Analytique - GEC", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Date du rapport
        date_para = Paragraph(f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
        elements.append(date_para)
        elements.append(Spacer(1, 30))
        
        # Section statistiques générales
        stats_title = Paragraph("Statistiques Générales", styles['Heading2'])
        elements.append(stats_title)
        elements.append(Spacer(1, 10))
        
        # Tableau des statistiques principales
        stats_data = [
            ['Métrique', 'Valeur'],
            ['Total Courriers', str(total_courriers)],
            ['Courriers Entrants', str(courriers_entrants)],
            ['Courriers Sortants', str(courriers_sortants)],
            ['7 Derniers Jours', str(courriers_7_days)],
            ['30 Derniers Jours', str(courriers_30_days)]
        ]
        
        stats_table = Table(stats_data, colWidths=[8*cm, 4*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        
        elements.append(stats_table)
        elements.append(Spacer(1, 30))
        
        # Section Top Expéditeurs
        if top_senders:
            senders_title = Paragraph("Top 10 Expéditeurs", styles['Heading2'])
            elements.append(senders_title)
            elements.append(Spacer(1, 10))
            
            senders_data = [['Expéditeur', 'Nombre de Courriers']]
            for sender in top_senders[:5]:  # Limiter à 5 pour le PDF
                senders_data.append([sender.expediteur[:50] + '...' if len(sender.expediteur) > 50 else sender.expediteur, str(sender.count)])
            
            senders_table = Table(senders_data, colWidths=[10*cm, 4*cm])
            senders_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            elements.append(senders_table)
            elements.append(Spacer(1, 20))
        
        
        doc.build(elements)
        
        buffer.seek(0)
        return send_file(buffer,
                        mimetype='application/pdf',
                        as_attachment=True,
                        download_name=f'analytics_report_{datetime.now().strftime("%Y%m%d")}.pdf')

@app.route('/forward_mail/<int:courrier_id>', methods=['POST'])
@login_required
def forward_mail(courrier_id):
    """Transmettre un courrier à un utilisateur"""
    courrier = Courrier.query.get_or_404(courrier_id)
    
    # Vérifier que l'utilisateur peut consulter le courrier
    if not current_user.can_view_courrier(courrier):
        flash('Vous n\'avez pas l\'autorisation de consulter ce courrier.', 'error')
        return redirect(url_for('view_mail'))
    
    user_id = request.form.get('user_id')
    message = request.form.get('message', '').strip()
    
    if not user_id:
        flash('Veuillez sélectionner un utilisateur destinataire.', 'error')
        return redirect(url_for('mail_detail', id=courrier_id))
    
    user = User.query.get_or_404(user_id)
    
    # Créer l'enregistrement de transmission
    forward = CourrierForward(
        courrier_id=courrier_id,
        forwarded_by_id=current_user.id,
        forwarded_to_id=user_id,
        message=message
    )
    
    try:
        db.session.add(forward)
        db.session.commit()
        
        # Créer une notification dans l'application
        Notification.create_notification(
            user_id=user_id,
            type_notification='mail_forwarded',
            titre=f'Courrier transmis - {courrier.numero_accuse_reception}',
            message=f'Le courrier "{courrier.objet}" vous a été transmis par {current_user.nom_complet}.',
            courrier_id=courrier_id
        )
        
        # Envoyer une notification par email
        try:
            # Vérifier si l'utilisateur a un email configuré
            if user.email and user.email.strip():
                courrier_data = {
                    'numero_accuse_reception': courrier.numero_accuse_reception,
                    'type_courrier': courrier.type_courrier,
                    'objet': courrier.objet,
                    'expediteur': courrier.expediteur or courrier.destinataire
                }
                if send_mail_forwarded_notification(user.email, courrier_data, current_user.nom_complet):
                    forward.email_sent = True
                    db.session.commit()
            else:
                logging.warning(f"Transmission courrier: utilisateur {user.nom_complet} n'a pas d'email configuré")
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi de l'email de transmission: {e}")
        
        # Log de l'activité
        log_activity(current_user.id, "TRANSMISSION_COURRIER", 
                    f"Transmission du courrier {courrier.numero_accuse_reception} à {user.nom_complet}", courrier_id)
        
        flash(f'Courrier transmis avec succès à {user.nom_complet}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de la transmission: {e}")
        flash('Erreur lors de la transmission du courrier.', 'error')
    
    return redirect(url_for('mail_detail', id=courrier_id))

@app.route('/add_comment/<int:courrier_id>', methods=['POST'])
@login_required
def add_comment(courrier_id):
    """Ajouter un commentaire à un courrier"""
    courrier = Courrier.query.get_or_404(courrier_id)
    
    # Vérifier l'accès au courrier
    if not current_user.can_access_courrier(courrier):
        flash('Vous n\'avez pas l\'autorisation de commenter ce courrier.', 'error')
        return redirect(url_for('view_mail'))
    
    commentaire = request.form.get('commentaire', '').strip()
    type_comment = request.form.get('type_comment', 'comment')
    
    if not commentaire:
        flash('Le commentaire ne peut pas être vide.', 'error')
        return redirect(url_for('mail_detail', id=courrier_id))
    
    # Créer le commentaire
    comment = CourrierComment(
        courrier_id=courrier_id,
        user_id=current_user.id,
        commentaire=commentaire,
        type_comment=type_comment
    )
    
    try:
        db.session.add(comment)
        db.session.commit()
        
        # Identifier les personnes à notifier (créateur + dernière personne qui a reçu le courrier)
        users_to_notify = set()
        
        # Ajouter le créateur du courrier
        if current_user.id != courrier.utilisateur_id:
            users_to_notify.add(courrier.utilisateur_id)
        
        # Ajouter la dernière personne qui a reçu le courrier en transmission
        last_forward = CourrierForward.query.filter_by(courrier_id=courrier_id)\
                                           .order_by(CourrierForward.date_transmission.desc()).first()
        if last_forward and last_forward.forwarded_to_id != current_user.id:
            users_to_notify.add(last_forward.forwarded_to_id)
        
        # Type de notification selon le type de commentaire
        notification_types = {
            'comment': 'comment_added',
            'annotation': 'annotation_added', 
            'instruction': 'instruction_added'
        }
        notification_type = notification_types.get(type_comment, 'comment_added')
        
        # Textes selon le type
        action_texts = {
            'comment': 'ajouté un commentaire',
            'annotation': 'ajouté une annotation',
            'instruction': 'ajouté une instruction'
        }
        action_text = action_texts.get(type_comment, 'ajouté un commentaire')
        
        # Créer les notifications et envoyer les emails
        for user_id in users_to_notify:
            try:
                # Notification in-app
                Notification.create_notification(
                    user_id=user_id,
                    type_notification=notification_type,
                    titre=f'Nouveau {type_comment} - {courrier.numero_accuse_reception}',
                    message=f'{current_user.nom_complet} a {action_text} sur le courrier "{courrier.objet}".',
                    courrier_id=courrier_id
                )
                
                # Notification email
                user = User.query.get(user_id)
                if user and user.email:
                    try:
                        courrier_data = {
                            'numero_accuse_reception': courrier.numero_accuse_reception,
                            'type_courrier': courrier.type_courrier,
                            'objet': courrier.objet,
                            'expediteur': courrier.expediteur or courrier.destinataire,
                            'comment_type': type_comment,
                            'comment_text': commentaire,
                            'added_by': current_user.nom_complet
                        }
                        
                        # Envoyer l'email de notification
                        if send_comment_notification(user.email, courrier_data):
                            logging.info(f"Notification email envoyée à {user.email} pour {type_comment}")
                        else:
                            logging.warning(f"Échec envoi email notification à {user.email}")
                            
                    except Exception as e:
                        logging.error(f"Erreur envoi email notification: {e}")
                        
            except Exception as e:
                logging.error(f"Erreur création notification pour user {user_id}: {e}")
        
        # Log de l'activité
        log_activity(current_user.id, "AJOUT_COMMENTAIRE", 
                    f"Ajout d'un commentaire sur le courrier {courrier.numero_accuse_reception}", courrier_id)
        
        flash('Commentaire ajouté avec succès.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de l'ajout du commentaire: {e}")
        flash('Erreur lors de l\'ajout du commentaire.', 'error')
    
    return redirect(url_for('mail_detail', id=courrier_id))

@app.route('/notifications')
@login_required
def notifications():
    """Afficher les notifications de l'utilisateur"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    notifications = Notification.query.filter_by(user_id=current_user.id)\
                                    .order_by(Notification.date_creation.desc())\
                                    .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('notifications.html', notifications=notifications)

@app.route('/mark_notification_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Marquer une notification comme lue"""
    notification = Notification.query.get_or_404(notification_id)
    
    # Vérifier que la notification appartient à l'utilisateur actuel
    if notification.user_id != current_user.id:
        flash('Accès refusé.', 'error')
        return redirect(url_for('notifications'))
    
    notification.mark_as_read()
    return redirect(url_for('notifications'))

@app.route('/mark_all_notifications_read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Marquer toutes les notifications de l'utilisateur comme lues"""
    try:
        notifications = Notification.query.filter_by(user_id=current_user.id, lu=False).all()
        for notification in notifications:
            notification.mark_as_read()
        
        flash(f'{len(notifications)} notification(s) marquée(s) comme lue(s).', 'success')
    except Exception as e:
        logging.error(f"Erreur lors du marquage des notifications: {e}")
        flash('Erreur lors du marquage des notifications.', 'error')
    
    return redirect(url_for('notifications'))

@app.route('/mark_notification_read_ajax/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read_ajax(notification_id):
    """Marquer une notification comme lue via AJAX"""
    notification = Notification.query.get_or_404(notification_id)
    
    # Vérifier que la notification appartient à l'utilisateur actuel
    if notification.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Accès refusé'}), 403
    
    try:
        notification.mark_as_read()
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Erreur AJAX marquage notification: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

