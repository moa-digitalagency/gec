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
from utils import allowed_file, generate_accuse_reception, log_activity, export_courrier_pdf, export_mail_list_pdf, get_current_language, set_language, t, get_available_languages, get_all_languages, toggle_language_status, download_language_file, upload_language_file, delete_language_file, validate_backup_integrity, create_pre_update_backup, get_backup_files, sign_courrier_action, generate_numero_suivi, qr_data_uri
from services.email import send_new_mail_notification, send_mail_forwarded_notification, send_comment_notification
from routes.auth import apply_mail_access_filter
from security import rate_limit, sanitize_input, validate_file_upload, log_security_event, record_failed_login, is_login_locked, reset_failed_login_attempts, get_client_ip, validate_password_strength, audit_log, encrypt_uploaded_file, decrypt_file_for_download
from utils.performance import cache_result, get_dashboard_statistics, optimize_search_query, PerformanceMonitor, clear_cache

STATUT_INITIAL = 'RECU'  # Évolution DPEM #1 : statut imposé à l'enregistrement

@app.route('/register_mail', methods=['GET', 'POST'])
@login_required
@rate_limit(max_requests=50, per_minutes=15)  # Prevent spam registration
def register_mail():
    # RÈGLE INVIOLABLE : super_admin ne peut pas créer de courriers
    if current_user.is_super_admin():
        log_activity(current_user.id, "ACCES_REFUSE",
                     "Tentative de création de courrier par un super_admin — refusé")
        flash('Les super administrateurs ne peuvent pas créer de courriers. '
              'Cette action est réservée aux administrateurs et utilisateurs.', 'error')
        return redirect(url_for('dashboard'))

    # Import TypeCourrierSortant
    from models import TypeCourrierSortant

    if request.method == 'POST':
        # Récupération des données du formulaire
        numero_reference = request.form.get('numero_reference', '').strip()
        objet = request.form['objet'].strip()
        type_courrier = request.form.get('type_courrier', 'ENTRANT')
        type_courrier_sortant_id = request.form.get('type_courrier_sortant_id', '')
        # Évolution DPEM #1 : le statut n'est plus choisi à l'enregistrement.
        statut = STATUT_INITIAL
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
        
        # Validation sécurisée : extension + magic bytes + taille
        is_valid, validation_msg = validate_file_upload(file)
        if not is_valid:
            flash(f'Fichier rejeté : {validation_msg}', 'error')
            statuts_disponibles = StatutCourrier.get_statuts_actifs()
            types_courrier_sortant = TypeCourrierSortant.get_types_actifs()
            return render_template('register_mail.html', statuts_disponibles=statuts_disponibles,
                                 types_courrier_sortant=types_courrier_sortant)

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

        # Chiffrement du fichier au repos
        fichier_is_encrypted = False
        try:
            encrypted_path = encrypt_uploaded_file(fichier_chemin)
            if encrypted_path:
                fichier_chemin = encrypted_path
                fichier_is_encrypted = True
        except Exception as e_enc:
            logging.warning(f"Chiffrement fichier principal ignoré : {e_enc}")

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
            fichier_encrypted=fichier_is_encrypted,
            utilisateur_id=current_user.id,
            secretaire_general_copie=secretaire_general_copie,
            autres_informations=autres_informations if type_courrier == 'SORTANT' else None,
            numero_suivi=generate_numero_suivi(),
        )

        # Évolution DPEM #4 : courrier sortant adossé (lié) à un courrier entrant parent.
        # Garde anti-IDOR : on ne lie le courrier qu'au parent que l'utilisateur a le droit de voir.
        # Garde métier : le parent doit être un courrier ENTRANT (empêche un POST forgé
        # de lier des paires incohérentes, ex. SORTANT->SORTANT).
        parent_id = request.form.get('parent_id', '').strip()
        if parent_id and parent_id.isdigit():
            parent = Courrier.query.get(int(parent_id))
            if parent and current_user.can_view_courrier(parent) and parent.type_courrier == 'ENTRANT':
                courrier.courrier_parent_id = parent.id

        try:
            db.session.add(courrier)
            db.session.commit()

            sign_courrier_action(courrier.id, current_user, 'CREATION', {
                'numero_accuse': numero_accuse,
                'type': type_courrier,
                'objet': objet,
            })

            # Signature de l'action côté parent : trace la génération du courrier sortant lié
            if courrier.courrier_parent_id:
                sign_courrier_action(courrier.courrier_parent_id, current_user, 'GEN_SORTANT', {
                    'courrier_lie_id': courrier.id,
                    'numero': numero_accuse,
                })
                db.session.commit()

            # Log de l'activité
            log_activity(current_user.id, "ENREGISTREMENT_COURRIER",
                        f"Enregistrement du courrier {numero_accuse}", courrier.id)
            
            # Notification SG en copie : notifier le(s) super_admin si le SG doit être informé
            if type_courrier == 'ENTRANT' and secretaire_general_copie:
                try:
                    titre_responsable = ParametresSysteme.get_valeur('titre_responsable_structure', 'Secrétaire Général')
                    sg_users = User.query.filter_by(role='super_admin', actif=True).all()
                    for sg_user in sg_users:
                        Notification.create_notification(
                            user_id=sg_user.id,
                            type_notification='sg_copie',
                            titre=f'[Copie {titre_responsable}] {numero_accuse}',
                            message=f'Le courrier "{objet}" (de : {expediteur}) vous a été mis en copie.',
                            courrier_id=courrier.id
                        )
                        if sg_user.email:
                            courrier_sg_data = {
                                'numero_accuse_reception': numero_accuse,
                                'type_courrier': type_courrier,
                                'objet': objet,
                                'expediteur': expediteur,
                                'created_by': current_user.nom_complet
                            }
                            send_new_mail_notification([sg_user.email], courrier_sg_data)
                except Exception as e:
                    logging.error(f"Erreur notification SG en copie: {e}")

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
            
            # Pièces jointes supplémentaires
            extra_files = request.files.getlist('fichiers_supplementaires')
            extra_saved = []
            for extra_file in extra_files:
                if extra_file and extra_file.filename and extra_file.filename != '':
                    try:
                        is_valid_extra, msg_extra = validate_file_upload(extra_file)
                        if is_valid_extra:
                            extra_filename = secure_filename(extra_file.filename)
                            extra_ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                            extra_filename = f"{extra_ts}_{extra_filename}"
                            extra_path = os.path.join('uploads', extra_filename)
                            extra_file.seek(0)
                            extra_file.save(extra_path)
                            # Chiffrement pièce jointe supplémentaire
                            extra_is_encrypted = False
                            try:
                                enc_extra = encrypt_uploaded_file(extra_path)
                                if enc_extra:
                                    extra_path = enc_extra
                                    extra_is_encrypted = True
                            except Exception as e_enc2:
                                logging.warning(f"Chiffrement pièce jointe ignoré : {e_enc2}")
                            attachment = CourrierAttachment(
                                courrier_id=courrier.id,
                                fichier_nom=extra_file.filename,
                                fichier_chemin=extra_path,
                                fichier_type=extra_filename.rsplit('.', 1)[-1].lower(),
                                fichier_taille=os.path.getsize(extra_path),
                                uploaded_by_id=current_user.id,
                                fichier_encrypted=extra_is_encrypted
                            )
                            db.session.add(attachment)
                            extra_saved.append(extra_file.filename)
                        else:
                            logging.warning(f"Pièce jointe supplémentaire rejetée : {msg_extra}")
                    except Exception as e_att:
                        logging.error(f"Erreur sauvegarde pièce jointe supplémentaire: {e_att}")
            db.session.commit()

            # Log pièces jointes supplémentaires
            if extra_saved:
                log_activity(current_user.id, "UPLOAD_PIECES_JOINTES",
                             f"{len(extra_saved)} pièce(s) jointe(s) ajoutée(s) au courrier "
                             f"{numero_accuse} : {', '.join(extra_saved[:5])}"
                             + (" ..." if len(extra_saved) > 5 else ""),
                             courrier.id)

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

    # Évolution DPEM #4 : pré-remplissage du formulaire depuis un courrier entrant parent
    # (bouton « Générer un courrier sortant lié »). Garde anti-IDOR identique au POST.
    prefill = {}
    parent_id = request.args.get('parent_id', '')
    if parent_id.isdigit():
        parent = Courrier.query.get(int(parent_id))
        if parent and current_user.can_view_courrier(parent):
            prefill = {
                'parent_id': parent.id,
                'type_courrier': 'SORTANT',
                'destinataire': parent.get_decrypted_expediteur() or parent.expediteur,
                'numero_reference': f"Réf. {parent.numero_accuse_reception}",
                'objet': f"Réponse à : {parent.objet}",
            }

    return render_template('register_mail.html', statuts_disponibles=statuts_disponibles,
                         departements=departements, parametres=parametres,
                         types_courrier_sortant=types_courrier_sortant, prefill=prefill)

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
    tag_filter = request.args.get('tag', '')      # Filtre par tag (nom)
    sort_by = request.args.get('sort_by', 'date_enregistrement')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Construction de la requête avec restrictions selon le rôle (incluant courriers transmis)
    query = Courrier.query
    query = apply_mail_access_filter(query, current_user)
    
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
    
    # Filtre par tag
    if tag_filter:
        query = query.join(CourrierTag, CourrierTag.courrier_id == Courrier.id)\
                     .join(Tag, Tag.id == CourrierTag.tag_id)\
                     .filter(Tag.nom == tag_filter)

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

    # Log navigation liste courriers (avec filtres actifs si présents)
    filters_active = [f for f in [
        f"recherche='{search}'" if search else None,
        f"statut={statut}" if statut else None,
        f"type={type_courrier}" if type_courrier else None,
        f"du={date_from}" if date_from else None,
        f"au={date_to}" if date_to else None,
    ] if f]
    log_activity(current_user.id, "NAVIGATION_LISTE_COURRIERS",
                 f"Consultation liste courriers — page {page}, {courriers_paginated.total} résultats"
                 + (f" [filtres: {', '.join(filters_active)}]" if filters_active else ""))

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

@app.route('/set_due_date/<int:id>', methods=['POST'])
@login_required
def set_due_date(id):
    courrier = Courrier.query.get_or_404(id)
    if not current_user.can_view_courrier(courrier):
        abort(403)
    due_str = request.form.get('due_date', '').strip()
    if due_str:
        try:
            courrier.due_date = datetime.strptime(due_str, '%Y-%m-%d').date()
            courrier.reminder_sent_at = None  # Réinitialiser le rappel
        except ValueError:
            flash('Format de date invalide.', 'error')
            return redirect(url_for('mail_detail', id=id))
    else:
        courrier.due_date = None
    db.session.commit()
    log_activity(current_user.id, "SET_DUE_DATE",
                 f"Échéance du courrier {courrier.numero_accuse_reception} fixée au {courrier.due_date}", id)
    flash('Échéance mise à jour.', 'success')
    return redirect(url_for('mail_detail', id=id))


@app.route('/admin/send_reminders', methods=['POST'])
@login_required
def send_reminders_manual():
    if not current_user.has_permission('manage_system_settings'):
        abort(403)
    count = _send_overdue_reminders()
    flash(f'Rappels envoyés : {count} courrier(s) notifié(s).', 'success')
    return redirect(url_for('dashboard'))


def _send_overdue_reminders():
    """Envoie des rappels email pour les courriers EN_COURS dépassant leur échéance."""
    from datetime import date as date_type
    from models import Notification
    today = date_type.today()
    overdue = Courrier.query.filter(
        Courrier.is_deleted == False,
        Courrier.statut.in_(['RECU', 'EN_COURS']),
        Courrier.due_date < today,
        Courrier.due_date.isnot(None),
        Courrier.reminder_sent_at.is_(None)
    ).all()
    count = 0
    for c in overdue:
        try:
            creator = User.query.get(c.utilisateur_id)
            if creator and creator.email:
                send_new_mail_notification([creator.email], {
                    'numero_accuse_reception': c.numero_accuse_reception,
                    'type_courrier': c.type_courrier,
                    'objet': f'[RAPPEL ÉCHÉANCE] {c.objet}',
                    'expediteur': c.expediteur or c.destinataire or '',
                    'created_by': 'Système GEC'
                })
            Notification.create_notification(
                user_id=c.utilisateur_id,
                type_notification='reminder',
                titre=f'Échéance dépassée — {c.numero_accuse_reception}',
                message=f'Le courrier "{c.objet}" était dû le {c.due_date.strftime("%d/%m/%Y")}.',
                courrier_id=c.id
            )
            c.reminder_sent_at = datetime.utcnow()
            count += 1
        except Exception as exc:
            logging.error(f"Erreur rappel courrier {c.id}: {exc}")
    if count:
        db.session.commit()
    return count


@app.route('/bulk_action', methods=['POST'])
@login_required
def bulk_action():
    action = request.form.get('action', '').strip()
    ids_raw = request.form.getlist('ids')

    # Valider les IDs
    try:
        ids = [int(i) for i in ids_raw if i.isdigit()]
    except (ValueError, AttributeError):
        flash('Sélection invalide.', 'error')
        return redirect(url_for('view_mail'))

    if not ids:
        flash('Aucun courrier sélectionné.', 'error')
        return redirect(url_for('view_mail'))

    if len(ids) > 200:
        flash('Maximum 200 courriers par action groupée.', 'error')
        return redirect(url_for('view_mail'))

    # Récupérer les courriers accessibles par cet utilisateur
    courriers = Courrier.query.filter(
        Courrier.id.in_(ids),
        Courrier.is_deleted == False
    ).all()

    # Filtrer par accès utilisateur
    accessible = [c for c in courriers if current_user.can_view_courrier(c)]

    if not accessible:
        audit_log("BULK_ACTION_UNAUTHORIZED", f"Tentative d'action groupée non autorisée sur {ids}")
        abort(403)

    statut_map = {
        'statut_recu': 'RECU',
        'statut_en_cours': 'EN_COURS',
        'statut_traite': 'TRAITE',
        'statut_archive': 'ARCHIVE',
    }

    if action in statut_map:
        new_statut = statut_map[action]
        for c in accessible:
            c.statut = new_statut
        db.session.commit()
        log_activity(current_user.id, "BULK_STATUT",
                     f"Statut → {new_statut} sur {len(accessible)} courrier(s)")
        flash(f'Statut mis à jour pour {len(accessible)} courrier(s).', 'success')

    elif action == 'delete':
        if not current_user.has_permission('delete_mail'):
            abort(403)
        for c in accessible:
            c.is_deleted = True
            c.deleted_at = datetime.utcnow()
            c.deleted_by_id = current_user.id
        db.session.commit()
        log_activity(current_user.id, "BULK_DELETE",
                     f"Suppression groupée de {len(accessible)} courrier(s)")
        flash(f'{len(accessible)} courrier(s) supprimé(s).', 'success')

    elif action == 'export_pdf':
        filters = {'search': '', 'date_from': '', 'date_to': '', 'statut': '',
                   'type_courrier': '', 'sort_by': 'date_enregistrement', 'sort_order': 'desc'}
        pdf_path = export_mail_list_pdf(accessible, filters)
        log_activity(current_user.id, "BULK_EXPORT_PDF",
                     f"Export PDF de {len(accessible)} courrier(s) sélectionné(s)")
        return send_from_directory(
            os.path.dirname(pdf_path), os.path.basename(pdf_path),
            as_attachment=True,
            download_name=f"selection_courriers_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mimetype='application/pdf')

    else:
        flash('Action inconnue.', 'error')

    return redirect(url_for('view_mail'))


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

    # Récupérer les signatures d'actions pour la timeline signée
    from models.courrier import CourrierActionSignature
    action_signatures = (CourrierActionSignature.query
                         .filter_by(courrier_id=id)
                         .order_by(CourrierActionSignature.timestamp.asc())
                         .all())

    log_activity(current_user.id, "CONSULTATION_COURRIER",
                f"Consultation du courrier {courrier.numero_accuse_reception}", courrier.id)
    return render_template('mail_detail_new.html',
                          courrier=courrier,
                          statuts_disponibles=statuts_disponibles,
                          comments=comments,
                          forwards=forwards,
                          users=users,
                          action_signatures=action_signatures)

@app.route('/courrier/<int:id>/etiquette')
@login_required
def etiquette_courrier(id):
    """Étiquette imprimable (numéro de suivi + QR code) à apposer sur le document."""
    courrier = Courrier.query.get_or_404(id)
    if not current_user.can_view_courrier(courrier):
        abort(403)
    if not courrier.numero_suivi:
        # Filet de sécurité : si le backfill (migration) n'a pas posé le numéro,
        # on l'attribue ici — action signée pour préserver la chaîne de non-répudiation.
        courrier.numero_suivi = generate_numero_suivi()
        sign_courrier_action(courrier.id, current_user, 'MODIF_CHAMP', {
            'champ': 'numero_suivi',
            'motif': 'attribution du numéro de suivi (génération étiquette)',
        })
        db.session.commit()
    qr = qr_data_uri(courrier.numero_suivi)  # QR = numéro de suivi en clair
    log_activity(current_user.id, "GENERATION_ETIQUETTE",
                 f"Étiquette générée pour {courrier.numero_accuse_reception}", courrier.id)
    parametres = ParametresSysteme.get_parametres()
    return render_template('etiquette_courrier.html', courrier=courrier, qr=qr, parametres=parametres)

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
        # 'statut' est NOT NULL en base : un formulaire qui ne le soumet pas
        # (champ non requis dans ce contexte) ne doit pas l'écraser à NULL.
        new_statut = request.form.get('statut') or old_values['statut']
        
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

            # Évolution DPEM #5 : modification manuelle de la date d'enregistrement (RBAC)
            if current_user.has_permission('edit_registration_date'):
                raw_date = request.form.get('date_enregistrement', '').strip()
                if raw_date:
                    parsed = None
                    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
                        try:
                            parsed = datetime.strptime(raw_date, fmt)
                            break
                        except ValueError:
                            continue
                    if parsed and parsed != courrier.date_enregistrement:
                        log_courrier_modification(courrier.id, current_user.id, 'date_enregistrement',
                                                  str(courrier.date_enregistrement), str(parsed))
                        courrier.date_enregistrement = parsed
                        sign_courrier_action(courrier.id, current_user, 'MODIF_DATE_ENREG',
                                             {'nouvelle_date': str(parsed)})
                        changes.append("date d'enregistrement")

            # Mettre à jour le modifieur et la date
            courrier.modifie_par_id = current_user.id

            if changes:
                sign_courrier_action(courrier.id, current_user, 'MODIF_CHAMP', {
                    'champs': changes,
                })

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

@app.route('/download_file/<int:id>')
@login_required
def download_file(id):
    courrier = Courrier.query.get_or_404(id)

    # Vérification d'accès : l'utilisateur doit avoir le droit de voir ce courrier
    if not current_user.can_view_courrier(courrier):
        audit_log("UNAUTHORIZED_DOWNLOAD", f"Tentative d'accès non autorisé au fichier du courrier {id}")
        abort(403)

    # Gérer les chemins relatifs et absolus
    if courrier.fichier_chemin:
        # Si le chemin est absolu, extraire la partie relative
        file_path = courrier.fichier_chemin
        if file_path.startswith('/'):
            # Chemin absolu - chercher la partie uploads
            if 'static/uploads/' in file_path:
                relative_path = file_path.split('static/uploads/')[-1]
                file_path = os.path.join('uploads', relative_path)

        # Protection path traversal : vérifier que le chemin reste dans uploads/
        uploads_dir = os.path.realpath('uploads')
        real_path = os.path.realpath(file_path)
        if not real_path.startswith(uploads_dir + os.sep) and real_path != uploads_dir:
            audit_log("PATH_TRAVERSAL_ATTEMPT", f"Tentative de path traversal détectée pour le courrier {id}")
            abort(403)
        
        # Log du chemin final
        logging.info(f"Chemin final à vérifier: {file_path}")
        logging.info(f"Le fichier existe? {os.path.exists(file_path)}")
        logging.info(f"Chemin absolu: {os.path.abspath(file_path)}")
        
        # Vérifier si le fichier existe
        if os.path.exists(file_path):
            log_activity(current_user.id, "TELECHARGEMENT_FICHIER",
                        f"Téléchargement du fichier du courrier {courrier.numero_accuse_reception}", courrier.id)
            try:
                sign_courrier_action(courrier.id, current_user, 'TELECHARGEMENT',
                                     {'fichier': courrier.fichier_nom})
                db.session.commit()
            except Exception as _se:
                db.session.rollback()
                logging.warning(f"Signature téléchargement ignorée: {_se}")

            # Déchiffrement si nécessaire avant envoi
            send_path = file_path
            temp_decrypted = None
            if getattr(courrier, 'fichier_encrypted', False):
                try:
                    temp_decrypted = decrypt_file_for_download(file_path)
                    if temp_decrypted:
                        send_path = temp_decrypted
                except Exception as e_dec:
                    logging.warning(f"Déchiffrement ignoré pour téléchargement : {e_dec}")

            directory = os.path.dirname(send_path)
            filename = os.path.basename(send_path)

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

            try:
                return send_from_directory(directory, filename,
                                         as_attachment=True,
                                         download_name=courrier.fichier_nom,
                                         mimetype=mimetype)
            finally:
                if temp_decrypted and os.path.exists(temp_decrypted):
                    try:
                        os.remove(temp_decrypted)
                    except Exception:
                        pass
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

@app.route('/download_attachment/<int:attachment_id>')
@login_required
def download_attachment(attachment_id):
    attachment = CourrierAttachment.query.get_or_404(attachment_id)
    courrier = Courrier.query.get_or_404(attachment.courrier_id)

    if not current_user.can_view_courrier(courrier):
        audit_log("UNAUTHORIZED_DOWNLOAD", f"Tentative d'accès non autorisé à la pièce jointe {attachment_id}")
        abort(403)

    file_path = attachment.fichier_chemin
    uploads_dir = os.path.realpath('uploads')
    real_path = os.path.realpath(file_path)
    if not real_path.startswith(uploads_dir + os.sep) and real_path != uploads_dir:
        audit_log("PATH_TRAVERSAL_ATTEMPT", f"Tentative de path traversal sur pièce jointe {attachment_id}")
        abort(403)

    if not os.path.exists(file_path):
        flash('Fichier non trouvé.', 'error')
        return redirect(url_for('mail_detail', id=courrier.id))

    log_activity(current_user.id, "TELECHARGEMENT_PIECE_JOINTE",
                 f"Téléchargement de la pièce jointe {attachment.fichier_nom} du courrier {courrier.numero_accuse_reception}",
                 courrier.id)

    # Déchiffrement si nécessaire avant envoi
    send_path = file_path
    temp_dec = None
    if getattr(attachment, 'fichier_encrypted', False):
        try:
            temp_dec = decrypt_file_for_download(file_path)
            if temp_dec:
                send_path = temp_dec
        except Exception as e_dec:
            logging.warning(f"Déchiffrement pièce jointe ignoré : {e_dec}")

    ext = attachment.fichier_nom.lower().rsplit('.', 1)[-1] if '.' in attachment.fichier_nom else ''
    mimetype_map = {'pdf': 'application/pdf', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png'}
    mimetype = mimetype_map.get(ext, 'application/octet-stream')

    try:
        return send_from_directory(
            os.path.dirname(send_path),
            os.path.basename(send_path),
            as_attachment=True,
            download_name=attachment.fichier_nom,
            mimetype=mimetype
        )
    finally:
        if temp_dec and os.path.exists(temp_dec):
            try:
                os.remove(temp_dec)
            except Exception:
                pass


@app.route('/change_status/<int:id>', methods=['POST'])
@login_required
def change_status(id):
    courrier = Courrier.query.get_or_404(id)
    new_status = request.form.get('nouveau_statut')
    
    if new_status:
        old_status = courrier.statut
        courrier.statut = new_status
        courrier.modifie_par_id = current_user.id

        # Enregistrer dans l'historique pour la timeline
        from models import CourrierModification
        mod = CourrierModification(
            courrier_id=courrier.id,
            utilisateur_id=current_user.id,
            champ_modifie='statut',
            ancienne_valeur=old_status,
            nouvelle_valeur=new_status,
            ip_address=get_client_ip()
        )
        db.session.add(mod)
        sign_courrier_action(courrier.id, current_user, 'MODIF_STATUT', {
            'ancien_statut': old_status,
            'nouveau_statut': new_status,
        })

        try:
            db.session.commit()
            log_activity(current_user.id, "CHANGEMENT_STATUT",
                        f"Statut du courrier {courrier.numero_accuse_reception} changé de {old_status} à {new_status}", courrier.id)
            flash(f'Statut mis à jour vers "{new_status}"', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour: {str(e)}', 'error')

    return redirect(url_for('mail_detail', id=id))


# ============================================================ #
#  A3 — Vue Kanban avec drag & drop
# ============================================================ #
KANBAN_COLUMNS = ['RECU', 'EN_COURS', 'TRAITE', 'ARCHIVE', 'REJETE']

@app.route('/courrier/<int:id>/circuit_signature', methods=['GET', 'POST'])
@login_required
def circuit_signature(id):
    """Initier ou consulter le circuit de signature d'un courrier"""
    courrier = Courrier.query.get_or_404(id)
    if not current_user.can_view_courrier(courrier):
        abort(403)

    if request.method == 'POST':
        # Initier un circuit de signature = action d'édition de courrier : la permission DOIT être
        # scopée à CE courrier (edit_department → même département, edit_own → propriétaire),
        # sinon un user avec edit_own_mail pourrait agir sur un courrier qu'il ne fait que consulter (IDOR).
        if not current_user.can_edit_courrier(courrier):
            return jsonify({'error': 'Permission refusée'}), 403

        data = request.get_json(silent=True) or {}
        signataire_ids = data.get('signataires', [])
        if not signataire_ids or not isinstance(signataire_ids, list):
            return jsonify({'error': 'Liste de signataires invalide'}), 400

        # Supprimer un circuit existant si on le réinitialise
        CourrierSignature.query.filter_by(courrier_id=courrier.id).delete()

        for ordre, uid in enumerate(signataire_ids, start=1):
            user = User.query.get(uid)
            if not user:
                continue
            sig = CourrierSignature(
                courrier_id=courrier.id,
                signataire_id=int(uid),
                ordre=ordre,
                statut='PENDING',
                initiated_by_id=current_user.id,
            )
            db.session.add(sig)

        sign_courrier_action(courrier.id, current_user, 'CIRCUIT_INIT', {
            'signataires': signataire_ids,
        })

        try:
            db.session.commit()
            log_activity(current_user.id, "CIRCUIT_SIGNATURE_INIT",
                         f"Circuit de signature initié pour courrier {courrier.numero_accuse_reception}",
                         courrier.id)
            # Notification au premier signataire
            _notify_next_signataire(courrier)
            return jsonify({'ok': True, 'message': 'Circuit initié avec succès'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    # GET — renvoyer l'état du circuit
    sigs = CourrierSignature.query.filter_by(courrier_id=courrier.id).order_by(CourrierSignature.ordre).all()
    return jsonify({
        'courrier_id': courrier.id,
        'circuit': [
            {
                'id': s.id,
                'ordre': s.ordre,
                'signataire': {'id': s.signataire_id, 'nom': s.signataire.nom_complet},
                'statut': s.statut,
                'commentaire': s.commentaire,
                'signed_at': s.signed_at.isoformat() if s.signed_at else None,
            }
            for s in sigs
        ]
    })


@app.route('/api/signature/<int:sig_id>/action', methods=['POST'])
@login_required
def signature_action(sig_id):
    """Signer ou rejeter une étape du circuit"""
    sig = CourrierSignature.query.get_or_404(sig_id)

    # Seul le signataire désigné peut agir
    if sig.signataire_id != current_user.id:
        return jsonify({'error': 'Action réservée au signataire désigné'}), 403

    if sig.statut != 'PENDING':
        return jsonify({'error': 'Cette étape a déjà été traitée'}), 400

    # Vérifier que l'étape précédente est signée (ordre séquentiel strict)
    if sig.ordre > 1:
        prev = CourrierSignature.query.filter_by(
            courrier_id=sig.courrier_id, ordre=sig.ordre - 1
        ).first()
        if prev and prev.statut == 'PENDING':
            return jsonify({'error': 'L\'étape précédente n\'a pas encore été traitée'}), 400

    data = request.get_json(silent=True) or {}
    action = data.get('action', '').upper()  # SIGNED | REJECTED
    commentaire = (data.get('commentaire') or '').strip()

    if action not in ('SIGNED', 'REJECTED'):
        return jsonify({'error': 'Action invalide (SIGNED ou REJECTED)'}), 400

    sig.statut = action
    sig.commentaire = commentaire or None
    sig.signed_at = datetime.utcnow()

    courrier = sig.courrier
    action_label = 'signé' if action == 'SIGNED' else 'rejeté'

    # Log
    from models import CourrierModification
    db.session.add(CourrierModification(
        courrier_id=courrier.id,
        utilisateur_id=current_user.id,
        champ_modifie='signature',
        ancienne_valeur='PENDING',
        nouvelle_valeur=action,
        ip_address=get_client_ip()
    ))
    sign_courrier_action(courrier.id, current_user,
                         'SIGNATURE' if action == 'SIGNED' else 'REJET', {
                             'commentaire': commentaire or None,
                             'ordre': sig.ordre,
                         })

    try:
        db.session.commit()
        log_activity(current_user.id, f"SIGNATURE_{action}",
                     f"Courrier {courrier.numero_accuse_reception} {action_label} par {current_user.nom_complet}",
                     courrier.id)

        if action == 'SIGNED':
            _notify_next_signataire(courrier)
        elif action == 'REJECTED':
            _notify_circuit_rejected(courrier, sig)

        return jsonify({'ok': True, 'statut': action})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


def _notify_next_signataire(courrier):
    """Notifie le prochain signataire PENDING dans le circuit"""
    next_sig = CourrierSignature.query.filter_by(
        courrier_id=courrier.id, statut='PENDING'
    ).order_by(CourrierSignature.ordre).first()

    if next_sig:
        notif = Notification(
            user_id=next_sig.signataire_id,
            type_notification='signature_demandee',
            message=f'Votre signature est requise pour le courrier {courrier.numero_accuse_reception}',
            courrier_id=courrier.id,
            date_creation=datetime.utcnow(),
        )
        db.session.add(notif)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


def _notify_circuit_rejected(courrier, sig):
    """Notifie l'initiateur du circuit en cas de rejet"""
    initiator_sig = CourrierSignature.query.filter_by(
        courrier_id=courrier.id
    ).order_by(CourrierSignature.ordre).first()

    if initiator_sig and initiator_sig.initiated_by_id:
        notif = Notification(
            user_id=initiator_sig.initiated_by_id,
            type_notification='signature_rejetee',
            message=(f'Le circuit de signature du courrier {courrier.numero_accuse_reception} '
                     f'a été rejeté par {sig.signataire.nom_complet}'),
            courrier_id=courrier.id,
            date_creation=datetime.utcnow(),
        )
        db.session.add(notif)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


@app.route('/view_file/<int:id>')
@login_required
def view_file(id):
    courrier = Courrier.query.get_or_404(id)

    if not current_user.can_view_courrier(courrier):
        audit_log("UNAUTHORIZED_VIEW", f"Tentative d'accès non autorisé au fichier du courrier {id}")
        abort(403)

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
            if 'static/uploads/' in file_path:
                relative_path = file_path.split('static/uploads/')[-1]
                file_path = os.path.join('uploads', relative_path)
        
        # Log du chemin final
        logging.info(f"Chemin final à vérifier: {file_path}")
        logging.info(f"Le fichier existe? {os.path.exists(file_path)}")
        
        # Vérifier si le fichier existe
        if os.path.exists(file_path):
            log_activity(current_user.id, "VISUALISATION_FICHIER",
                        f"Visualisation du fichier du courrier {courrier.numero_accuse_reception}", courrier.id)
            try:
                sign_courrier_action(courrier.id, current_user, 'VISUALISATION',
                                     {'fichier': courrier.fichier_nom})
                db.session.commit()
            except Exception as _se:
                db.session.rollback()
                logging.warning(f"Signature visualisation ignorée: {_se}")

            # Déchiffrement si nécessaire avant affichage
            send_path = file_path
            temp_dec_view = None
            if getattr(courrier, 'fichier_encrypted', False):
                try:
                    temp_dec_view = decrypt_file_for_download(file_path)
                    if temp_dec_view:
                        send_path = temp_dec_view
                except Exception as e_dec:
                    logging.warning(f"Déchiffrement visualisation ignoré : {e_dec}")

            directory = os.path.dirname(send_path)
            filename = os.path.basename(send_path)

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

            try:
                return send_from_directory(directory, filename,
                                         as_attachment=False,
                                         mimetype=mimetype)
            finally:
                if temp_dec_view and os.path.exists(temp_dec_view):
                    try:
                        os.remove(temp_dec_view)
                    except Exception:
                        pass
        else:
            logging.error(f"Fichier non trouvé au chemin: {file_path}")
    else:
        logging.error(f"Pas de chemin de fichier dans la base de données pour le courrier {id}")
    
    flash('Fichier non trouvé.', 'error')
    return redirect(url_for('mail_detail', id=id))

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

    sign_courrier_action(courrier.id, current_user, 'SUPPRESSION', {
        'numero_accuse': courrier.numero_accuse_reception,
    })

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

    sign_courrier_action(courrier.id, current_user, 'RESTAURATION', {
        'numero_accuse': courrier.numero_accuse_reception,
    })

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
    """Vider définitivement la corbeille"""
    if not current_user.has_permission('permanent_delete'):
        flash('Vous n\'avez pas la permission de vider la corbeille définitivement.', 'error')
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

@app.route('/static/uploads/profiles/<filename>')
def profile_photo(filename):
    """Servir les photos de profil.

    Cette règle est plus spécifique que la route statique de Flask : elle la
    masque donc pour cette URL. Elle doit lire le dossier où les photos sont
    réellement écrites (static/uploads/profiles, cf. routes/users.py et
    edit_profile), et répondre 404 — non 500 — si le fichier a disparu.
    """
    profile_folder = os.path.join('static', 'uploads', 'profiles')
    chemin = os.path.join(profile_folder, secure_filename(filename))
    if not os.path.isfile(chemin):
        abort(404)
    return send_file(chemin)

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    """Servir les fichiers uploadés (logos, etc.)"""
    try:
        upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        return send_from_directory(upload_folder, filename)
    except Exception as e:
        logging.error(f"Erreur lors du service du fichier {filename}: {e}")
        abort(404)

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
    
    # Gérer le fichier joint (optionnel)
    attachment_filename = None
    attachment_original_name = None
    attachment_size = None
    
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename:
            # Valider le fichier
            is_valid_fwd, _ = validate_file_upload(file)
            if is_valid_fwd:
                # Créer le répertoire s'il n'existe pas
                forward_uploads_dir = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'forwards')
                os.makedirs(forward_uploads_dir, exist_ok=True)
                
                # Générer un nom unique pour le fichier
                file_extension = os.path.splitext(file.filename)[1].lower()
                unique_filename = f"forward_{courrier_id}_{current_user.id}_{uuid.uuid4().hex[:8]}{file_extension}"
                file_path = os.path.join(forward_uploads_dir, unique_filename)
                
                try:
                    # Sauvegarder le fichier
                    file.save(file_path)
                    
                    # Enregistrer les informations du fichier
                    attachment_filename = unique_filename
                    attachment_original_name = file.filename
                    attachment_size = os.path.getsize(file_path)
                    
                    log_activity(current_user.id, "UPLOAD_TRANSMISSION_FILE", 
                               f"Fichier joint ajouté à la transmission: {file.filename}", courrier_id)
                    
                except Exception as e:
                    logging.error(f"Erreur lors de la sauvegarde du fichier de transmission: {e}")
                    flash('Erreur lors de la sauvegarde du fichier joint.', 'error')
            else:
                flash('Format de fichier non autorisé ou fichier trop volumineux (16MB max).', 'error')
                return redirect(url_for('mail_detail', id=courrier_id))
    
    # Créer l'enregistrement de transmission
    forward = CourrierForward(
        courrier_id=courrier_id,
        forwarded_by_id=current_user.id,
        forwarded_to_id=user_id,
        message=message,
        attached_file=attachment_filename,
        attached_file_original_name=attachment_original_name,
        attached_file_size=attachment_size
    )
    
    try:
        db.session.add(forward)
        sign_courrier_action(courrier_id, current_user, 'TRANSMISSION', {
            'destinataire_id': int(user_id),
            'destinataire_nom': user.nom_complet,
            'message': message or None,
            'fichier_joint': attachment_original_name or None,
        })
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
                    'expediteur': courrier.expediteur or courrier.destinataire,
                    'message': message,
                    'attachment_info': f"Pièce jointe: {attachment_original_name}" if attachment_original_name else None
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

@app.route('/download_forward_attachment/<int:forward_id>')
@login_required  
def download_forward_attachment(forward_id):
    """Télécharger un fichier joint d'une transmission"""
    forward = CourrierForward.query.get_or_404(forward_id)
    
    # Vérifier que l'utilisateur peut accéder à cette transmission
    if not (current_user.id == forward.forwarded_to_id or 
            current_user.id == forward.forwarded_by_id or
            current_user.can_view_courrier(forward.courrier)):
        flash('Vous n\'avez pas l\'autorisation d\'accéder à ce fichier.', 'error')
        return redirect(url_for('view_mail'))
    
    if not forward.attached_file:
        flash('Aucun fichier joint trouvé pour cette transmission.', 'error')
        return redirect(url_for('mail_detail', id=forward.courrier_id))
    
    # Chemin vers le fichier
    forward_uploads_dir = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'forwards')
    file_path = os.path.join(forward_uploads_dir, forward.attached_file)
    
    if not os.path.exists(file_path):
        flash('Le fichier joint n\'existe plus sur le serveur.', 'error')
        return redirect(url_for('mail_detail', id=forward.courrier_id))
    
    # Log de l'activité
    log_activity(current_user.id, "DOWNLOAD_TRANSMISSION_FILE", 
                f"Téléchargement du fichier joint: {forward.attached_file_original_name}", 
                forward.courrier_id)
    
    return send_file(file_path, 
                    as_attachment=True, 
                    download_name=forward.attached_file_original_name)

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

    # Évolution DPEM #2 : Annotation du Directeur — permission dédiée + unicité
    if type_comment == 'annotation_directeur':
        if not current_user.has_permission('add_director_annotation'):
            flash("Vous n'êtes pas autorisé à poser l'annotation du Directeur.", 'error')
            return redirect(url_for('mail_detail', id=courrier_id))
        existante = CourrierComment.query.filter_by(
            courrier_id=courrier_id, type_comment='annotation_directeur', actif=True
        ).first()
        if existante:
            existante.commentaire = commentaire
            existante.date_modification = datetime.utcnow()
            existante.modifie_par_id = current_user.id
            sign_courrier_action(courrier_id, current_user, 'ANNOTATION_DIRECTEUR',
                                 {'maj': True, 'extrait': commentaire[:200]})
            db.session.commit()
            log_activity(current_user.id, "ANNOTATION_DIRECTEUR",
                         f"Mise à jour de l'annotation du Directeur — {courrier.numero_accuse_reception}", courrier_id)
            flash("Annotation du Directeur mise à jour.", 'success')
            return redirect(url_for('mail_detail', id=courrier_id))

    # Créer le commentaire
    comment = CourrierComment(
        courrier_id=courrier_id,
        user_id=current_user.id,
        commentaire=commentaire,
        type_comment=type_comment
    )

    # Évolution DPEM #3 : pièce jointe (PDF/image) sur commentaire/annotation
    pj = request.files.get('piece_jointe')
    if pj and pj.filename:
        ext = pj.filename.rsplit('.', 1)[-1].lower() if '.' in pj.filename else ''
        if ext not in {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif'}:
            flash('Pièce jointe refusée : seuls les fichiers PDF ou image sont acceptés.', 'error')
            return redirect(url_for('mail_detail', id=courrier_id))
        is_valid_pj, msg_pj = validate_file_upload(pj)
        if not is_valid_pj:
            flash(f'Pièce jointe refusée : {msg_pj}', 'error')
            return redirect(url_for('mail_detail', id=courrier_id))
        pj_name = secure_filename(pj.filename)
        pj_ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        pj_stored = f"{pj_ts}_{pj_name}"
        pj_path = os.path.join('uploads', pj_stored)
        os.makedirs('uploads', exist_ok=True)
        pj.seek(0)
        pj.save(pj_path)
        plaintext_source = pj_path
        pj_encrypted = False
        try:
            enc = encrypt_uploaded_file(pj_path)
            if enc:
                pj_path = enc
                pj_encrypted = True
                try:
                    if os.path.exists(plaintext_source):
                        os.remove(plaintext_source)   # ne pas laisser le clair au repos
                except OSError as e_rm:
                    logging.warning(f"Suppression du clair PJ commentaire échouée: {e_rm}")
        except Exception as e_pj:
            logging.warning(f"Chiffrement PJ commentaire ignoré : {e_pj}")
        comment.fichier_nom = pj.filename
        comment.fichier_chemin = pj_path
        comment.fichier_type = pj_stored.rsplit('.', 1)[-1].lower()
        comment.fichier_taille = os.path.getsize(pj_path)
        comment.fichier_encrypted = pj_encrypted

    action_type_map = {
        'comment': 'COMMENTAIRE',
        'annotation': 'ANNOTATION',
        'instruction': 'INSTRUCTION',
        'annotation_directeur': 'ANNOTATION_DIRECTEUR',
    }

    try:
        db.session.add(comment)
        sign_courrier_action(courrier_id, current_user,
                             action_type_map.get(type_comment, 'COMMENTAIRE'), {
                                 'type': type_comment,
                                 'extrait': commentaire[:200],
                             })
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

@app.route('/download_comment_attachment/<int:comment_id>')
@login_required
def download_comment_attachment(comment_id):
    """Télécharger la pièce jointe d'un commentaire/annotation (déchiffrée à la volée)."""
    comment = CourrierComment.query.get_or_404(comment_id)
    courrier = Courrier.query.get_or_404(comment.courrier_id)
    if not current_user.can_view_courrier(courrier):
        abort(403)
    if not comment.fichier_chemin:
        flash('Aucune pièce jointe pour ce commentaire.', 'error')
        return redirect(url_for('mail_detail', id=comment.courrier_id))
    log_activity(current_user.id, "DOWNLOAD_PJ_COMMENTAIRE",
                 f"Téléchargement PJ commentaire {comment_id}", comment.courrier_id)
    if comment.fichier_encrypted:
        try:
            temp_path = decrypt_file_for_download(comment.fichier_chemin)
        except Exception as e_dec:
            logging.warning(f"Déchiffrement PJ commentaire échoué : {e_dec}")
            flash('Erreur lors du déchiffrement de la pièce jointe.', 'error')
            return redirect(url_for('mail_detail', id=comment.courrier_id))
        try:
            return send_file(temp_path, as_attachment=True, download_name=comment.fichier_nom)
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    return send_file(comment.fichier_chemin, as_attachment=True, download_name=comment.fichier_nom)

