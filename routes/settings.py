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
        from services.email import send_email_from_system_config
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

@app.route('/settings', methods=['GET', 'POST'])
@login_required
@rate_limit(max_requests=20, per_minutes=15)
def settings():
    # Vérification des permissions
    if not current_user.is_super_admin():
        flash('Accès refusé. Seuls les super administrateurs peuvent accéder aux paramètres.', 'error')
        return redirect(url_for('dashboard'))
    
    with PerformanceMonitor("settings_page"):
        parametres = ParametresSysteme.get_parametres()
        # Types de courrier sortant maintenant gérés dans une page dédiée
        
        if request.method == 'POST':
            # Test email Resend
            if request.form.get('test_email'):
                test_email = request.form.get('test_email', '').strip()

                if not test_email:
                    flash('Veuillez saisir une adresse email pour le test.', 'error')
                    return redirect(url_for('settings'))

                import re
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', test_email):
                    flash('Adresse email invalide.', 'error')
                    return redirect(url_for('settings'))

                from services.email import test_resend_configuration
                result = test_resend_configuration(test_email)

                if result['success']:
                    flash(result['message'], 'success')
                    log_activity(current_user.id, "TEST_EMAIL_RESEND",
                                 f"Test email Resend envoyé à {test_email}")
                else:
                    flash(result['message'], 'error')
                    log_activity(current_user.id, "TEST_EMAIL_RESEND_ECHEC",
                                 f"Échec test Resend : {result['message']}")

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
            parametres.email_provider = sanitize_input(request.form.get('email_provider', 'resend').strip())
            
            # Numéro WhatsApp
            parametres.whatsapp_number = sanitize_input(request.form.get('whatsapp_number', '243860493345').strip())

            # Notifications pour super admin (seuls les super admin peuvent modifier)
            if current_user.is_super_admin():
                parametres.notify_superadmin_new_mail = bool(request.form.get('notify_superadmin_new_mail'))
            
            # Paramètres SMTP et Resend (soumis aux permissions)
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
                    from security.encryption import EncryptionManager
                    encryption_manager = EncryptionManager()
                    parametres.smtp_password = encryption_manager.encrypt_data(smtp_password)
                
                # Clé API Resend
                resend_api_key = request.form.get('resend_api_key', '').strip()
                if resend_api_key and resend_api_key != '●●●●●●●●●●●●●●●●●●●●' and len(resend_api_key) > 5:
                    parametres.resend_api_key = resend_api_key
                    logging.info(f"✅ Clé Resend sauvegardée (longueur: {len(resend_api_key)})")
                elif resend_api_key == '':
                    logging.info("Clé Resend: champ vide, conservation de la clé existante")
            
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
                        parametres.logo_url = f'/static/uploads/{logo_filename}'
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
                        parametres.logo_pdf = f'/static/uploads/{logo_pdf_filename}'
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
        
        # Backup files maintenant gérés dans la page dédiée
        
        return render_template('settings.html', 
                              parametres=parametres,
                              format_preview=format_preview)

@app.route('/clear_cache', methods=['POST'])
@login_required
def clear_cache_route():
    """Route pour vider le cache système"""
    if not current_user.is_super_admin():
        return jsonify({
            'success': False,
            'message': 'Accès non autorisé'
        }), 403
    
    try:
        # Import et appel de la fonction clear_cache depuis performance_utils
        from utils.performance import clear_cache
        clear_cache()
        
        # Log de l'action
        log_activity(
            current_user.id,
            "clear_cache",
            f"Cache système vidé par {current_user.username}"
        )
        
        return jsonify({
            'success': True,
            'message': 'Cache vidé avec succès'
        })
    except Exception as e:
        logging.error(f"Erreur lors du vidage du cache: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

# Route manage_mail_types supprimée - maintenant gérée par manage_outgoing_types

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

@app.route('/set_language/<lang_code>')
def set_language_route(lang_code):
    """Changer la langue de l'interface"""
    # Vérifier que la langue est supportée
    available_languages = get_available_languages()
    if lang_code not in available_languages:
        flash('Langue non supportée', 'error')
        return redirect(request.referrer or url_for('dashboard'))
    
    # Définir la langue dans la session
    session['language'] = lang_code
    session.permanent = True  # Rendre la session permanente
    
    # Si l'utilisateur est connecté, sauvegarder dans son profil
    if current_user.is_authenticated:
        try:
            current_user.langue = lang_code
            db.session.commit()
            log_activity(current_user.id, "LANGUAGE_CHANGE", f"Langue changée vers {lang_code}")
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la langue: {e}")
            db.session.rollback()
    
    # Message de confirmation dans la nouvelle langue
    if lang_code == 'fr':
        flash('Langue changée avec succès vers le français', 'success')
    else:
        flash('Language successfully changed to English', 'success')
    
    # Rediriger vers la page précédente ou le dashboard
    response = redirect(request.referrer or url_for('dashboard'))
    # Définir un cookie persistant pour la langue (1 an)
    response.set_cookie('language', lang_code, max_age=365*24*60*60, secure=False, httponly=False)
    return response

@app.route('/manage_languages')
@login_required
def manage_languages():
    """Gestion des langues - accessible uniquement aux super admins"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    all_languages = get_all_languages()
    return render_template('manage_languages.html', languages=all_languages)

@app.route('/toggle_language/<lang_code>', methods=['POST'])
@login_required
def toggle_language(lang_code):
    """Activer/désactiver une langue"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    enabled = request.json.get('enabled', False)
    
    if toggle_language_status(lang_code, enabled):
        status = "activée" if enabled else "désactivée"
        log_activity(current_user.id, "LANGUAGE_TOGGLE", 
                    f"Langue {lang_code} {status}")
        return jsonify({'success': True, 'message': f'Langue {status} avec succès'})
    else:
        return jsonify({'success': False, 'message': 'Erreur lors de la modification'}), 400

@app.route('/download_language/<lang_code>')
@login_required
def download_language(lang_code):
    """Télécharger un fichier de langue JSON"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    file_path = download_language_file(lang_code)
    if file_path:
        log_activity(current_user.id, "LANGUAGE_DOWNLOAD", 
                    f"Téléchargement du fichier de langue {lang_code}")
        return send_file(file_path, as_attachment=True, 
                        download_name=f'{lang_code}.json',
                        mimetype='application/json')
    else:
        flash('Fichier de langue non trouvé.', 'error')
        return redirect(url_for('manage_languages'))

@app.route('/upload_language', methods=['POST'])
@login_required
def upload_language():
    """Upload un nouveau fichier de langue JSON"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    if 'language_file' not in request.files:
        flash('Aucun fichier sélectionné.', 'error')
        return redirect(url_for('manage_languages'))
    
    file = request.files['language_file']
    lang_code = request.form.get('lang_code', '').lower().strip()
    
    if file.filename == '' or not lang_code:
        flash('Fichier et code de langue requis.', 'error')
        return redirect(url_for('manage_languages'))
    
    if not lang_code or len(lang_code) != 2:
        flash('Le code de langue doit faire exactement 2 caractères.', 'error')
        return redirect(url_for('manage_languages'))
    
    if file and file.filename.endswith('.json'):
        try:
            file_content = file.read().decode('utf-8')
            
            if upload_language_file(lang_code, file_content):
                log_activity(current_user.id, "LANGUAGE_UPLOAD", 
                            f"Upload du fichier de langue {lang_code}")
                flash(f'Fichier de langue {lang_code} uploadé avec succès!', 'success')
            else:
                flash('Erreur lors de l\'upload du fichier. Vérifiez le format JSON.', 'error')
        except Exception as e:
            flash(f'Erreur lors de l\'upload: {str(e)}', 'error')
    else:
        flash('Seuls les fichiers JSON sont acceptés.', 'error')
    
    return redirect(url_for('manage_languages'))

@app.route('/delete_language/<lang_code>', methods=['POST'])
@login_required
def delete_language(lang_code):
    """Supprimer un fichier de langue"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    if lang_code == 'fr':
        flash('Impossible de supprimer le fichier français (langue de référence).', 'error')
        return redirect(url_for('manage_languages'))
    
    if delete_language_file(lang_code):
        log_activity(current_user.id, "LANGUAGE_DELETE", 
                    f"Suppression du fichier de langue {lang_code}")
        flash(f'Fichier de langue {lang_code} supprimé avec succès!', 'success')
    else:
        flash('Erreur lors de la suppression du fichier.', 'error')
    
    return redirect(url_for('manage_languages'))

# ===== GESTION DES TYPES DE COURRIER SORTANT =====

