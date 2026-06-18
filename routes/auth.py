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

SESSION_INACTIVITY_TIMEOUT = 900  # Valeur de repli (15 min) — la vraie valeur vient de Paramètres → Sécurité

@app.before_request
def enforce_session_expiry():
    """
    Force la déconnexion automatique après 1h d'inactivité.
    Le timer se réinitialise à chaque requête — seule une absence d'activité pendant 1h déclenche la déconnexion.
    """
    if not current_user.is_authenticated:
        return

    import time
    last_activity = session.get('last_activity')
    if last_activity is None:
        # Session sans horodatage (ancienne session) → déconnexion
        logout_user()
        session.clear()
        flash('Votre session a expiré. Veuillez vous reconnecter.', 'info')
        return redirect(url_for('login'))

    elapsed = time.time() - last_activity
    # Délai d'inactivité configurable (Paramètres → Sécurité), repli 15 min
    try:
        from models import ParametresSysteme
        timeout = (ParametresSysteme.get_parametres().session_idle_timeout_min or 15) * 60
    except Exception:
        timeout = SESSION_INACTIVITY_TIMEOUT
    if elapsed > timeout:
        user_id = current_user.id
        username = current_user.username
        logout_user()
        session.clear()
        log_activity(user_id, "AUTO_DECONNEXION",
                     f"Déconnexion automatique de {username} après {int(elapsed // 60)} min d'inactivité")
        flash(f"Votre session a expiré après {int(timeout // 60)} min d'inactivité. Veuillez vous reconnecter.", 'info')
        return redirect(url_for('login'))

    # Mettre à jour le timestamp d'activité à chaque requête
    session['last_activity'] = time.time()


@app.context_processor
def inject_system_context():
    """Inject system parameters and utility functions into all templates"""
    def get_unread_notifications_count():
        if current_user.is_authenticated:
            return Notification.query.filter_by(user_id=current_user.id, lu=False).count()
        return 0
    
    # Import des utilitaires de formatage pour les templates
    from utils import format_date, get_titre_responsable
    
    def get_appellation_entites():
        """Récupérer l'appellation des entités organisationnelles"""
        try:
            parametres = ParametresSysteme.get_parametres()
            appellation = getattr(parametres, 'appellation_departement', 'Départements') or 'Départements'
            return appellation
        except:
            return 'Départements'
    
    return dict(
        get_system_params=lambda: ParametresSysteme.get_parametres(),
        get_current_language=get_current_language,
        get_available_languages=get_available_languages,
        get_unread_notifications_count=get_unread_notifications_count,
        t=t,
        format_date=format_date,
        get_titre_responsable=get_titre_responsable,
        get_appellation_entites=get_appellation_entites,
        now=datetime.utcnow,
    )

def apply_mail_access_filter(query, user):
    """
    Applique les restrictions d'accès aux courriers selon les rôles avec exception pour les transmissions.
    Un courrier transmis à un utilisateur devient accessible même si son rôle ne le permet pas normalement.

    RÈGLE INVIOLABLE : super_admin ne peut voir AUCUN courrier (retourne 0 résultats).
    """
    from sqlalchemy import exists

    # Base condition : courriers non supprimés
    query = query.filter(Courrier.is_deleted == False)

    # RÈGLE INVIOLABLE : super_admin bloqué de tous les courriers
    if user.role == 'super_admin':
        return query.filter(False)  # Résultat toujours vide

    # Condition pour courriers transmis à l'utilisateur
    forwarded_condition = exists().where(
        and_(
            CourrierForward.courrier_id == Courrier.id,
            CourrierForward.forwarded_to_id == user.id
        )
    )

    # Conditions normales selon les permissions
    if user.has_permission('read_all_mail'):
        return query
    elif user.has_permission('read_department_mail'):
        # Peut voir les courriers de son département OU les courriers qui lui sont transmis
        if user.departement_id:
            department_condition = exists().where(
                and_(
                    User.id == Courrier.utilisateur_id,
                    User.departement_id == user.departement_id
                )
            )
            return query.filter(or_(department_condition, forwarded_condition))
        else:
            # Pas de département assigné : voir ses propres courriers OU ceux transmis
            own_mail_condition = (Courrier.utilisateur_id == user.id)
            return query.filter(or_(own_mail_condition, forwarded_condition))
    elif user.has_permission('read_own_mail'):
        # Peut voir ses propres courriers OU ceux transmis
        own_mail_condition = (Courrier.utilisateur_id == user.id)
        return query.filter(or_(own_mail_condition, forwarded_condition))
    else:
        # Aucune action read_* assignée au rôle : restreint à ses propres courriers
        # OU ceux qui lui ont été transmis (plus de raccourci codé en dur par rôle).
        own_mail_condition = (Courrier.utilisateur_id == user.id)
        return query.filter(or_(own_mail_condition, forwarded_condition))

@app.route('/')
def index():
    # Application strictement B2B/Interne : redirection directe vers login ou dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
@rate_limit(max_requests=30, per_minutes=15)  # Prevent brute force attacks - Increased to allow legitimate retries
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
                reset_failed_login_attempts(client_ip)

                # 2FA check — if enabled, redirect to TOTP step
                if user.totp_enabled and user.totp_secret:
                    session['2fa_pending_user_id'] = user.id
                    session['2fa_next'] = request.args.get('next', '')
                    return redirect(url_for('verify_2fa'))

                # Successful login (no 2FA)
                login_user(user)
                import time
                session['last_activity'] = time.time()  # Horodatage pour expiration après inactivité
                audit_log("LOGIN_SUCCESS", f"Successful login for user: {username}")
                log_activity(user.id, "CONNEXION", f"Connexion réussie pour {username}")
                flash('Connexion réussie!', 'success')

                next_page = request.args.get('next')
                if next_page:
                    from security import secure_redirect
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

# ============================================================ #
#  C3 — 2FA TOTP (super_admin uniquement)
# ============================================================ #

@app.route('/verify_2fa', methods=['GET', 'POST'])
def verify_2fa():
    """Étape de vérification TOTP après le mot de passe"""
    pending_id = session.get('2fa_pending_user_id')
    if not pending_id:
        return redirect(url_for('login'))

    user = User.query.get(pending_id)
    if not user:
        session.pop('2fa_pending_user_id', None)
        return redirect(url_for('login'))

    error = None
    if request.method == 'POST':
        token = request.form.get('token', '').strip().replace(' ', '')
        if user.verify_totp(token):
            session.pop('2fa_pending_user_id', None)
            next_url = session.pop('2fa_next', '')
            login_user(user)
            import time
            session['last_activity'] = time.time()  # Horodatage pour expiration après inactivité
            audit_log("LOGIN_2FA_SUCCESS", f"2FA réussi pour {user.username}")
            log_activity(user.id, "CONNEXION_2FA", f"Connexion avec 2FA réussie pour {user.username}")
            flash('Connexion réussie!', 'success')
            if next_url:
                from security import secure_redirect
                return redirect(secure_redirect(next_url))
            return redirect(url_for('dashboard'))
        else:
            audit_log("LOGIN_2FA_FAILED", f"Code 2FA invalide pour {user.username}", "WARNING")
            error = 'Code invalide. Réessayez.'

    return render_template('verify_2fa.html', error=error)


@app.route('/profile/2fa/setup', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    """Activation de la 2FA — disponible pour tout utilisateur connecté (sur son propre compte)"""

    import pyotp, qrcode, io, base64

    if request.method == 'POST':
        token = request.form.get('token', '').strip().replace(' ', '')
        pending = current_user.totp_pending_secret
        if not pending:
            flash('Session expirée, recommencez.', 'error')
            return redirect(url_for('setup_2fa'))

        totp = pyotp.TOTP(pending)
        if totp.verify(token, valid_window=4):
            current_user.totp_secret = pending
            current_user.totp_pending_secret = None
            current_user.totp_enabled = True
            db.session.commit()
            log_activity(current_user.id, "2FA_ENABLED", "Double authentification activée")
            flash('Double authentification activée avec succès.', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Code incorrect. Réessayez.', 'error')
            return redirect(url_for('setup_2fa'))

    # GET — générer un nouveau secret pending
    secret = pyotp.random_base32()
    current_user.totp_pending_secret = secret
    db.session.commit()

    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email, issuer_name='GEC-Courrier'
    )

    # QR code en base64
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return render_template('setup_2fa.html', qr_b64=qr_b64, secret=secret)


@app.route('/profile/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    """Désactiver la 2FA"""
    if current_user.role != 'super_admin':
        abort(403)

    token = request.form.get('token', '').strip().replace(' ', '')
    if not current_user.verify_totp(token):
        flash('Code incorrect. La 2FA n\'a pas été désactivée.', 'error')
        return redirect(url_for('profile'))

    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.totp_pending_secret = None
    db.session.commit()
    log_activity(current_user.id, "2FA_DISABLED", "Double authentification désactivée")
    flash('Double authentification désactivée.', 'info')
    return redirect(url_for('profile'))


@app.route('/dashboard')
@login_required
def dashboard():
    with PerformanceMonitor("dashboard_load"):
        stats = get_dashboard_statistics()

        recent_query = Courrier.query
        recent_query = apply_mail_access_filter(recent_query, current_user)
        recent_courriers = recent_query.order_by(
            Courrier.date_enregistrement.desc()
        ).limit(5).all()

        role_data = _get_role_dashboard_data(current_user)

        log_activity(current_user.id, "NAVIGATION_DASHBOARD",
                     f"Consultation du tableau de bord")

        return render_template('dashboard.html',
                             total_courriers=stats['total_courriers'],
                             courriers_today=stats['courriers_today'],
                             courriers_this_week=stats['courriers_this_week'],
                             total_users=stats['total_users'],
                             recent_courriers=recent_courriers,
                             recent_activities=stats['recent_activities'],
                             role_data=role_data)


def _get_role_dashboard_data(user):
    """Retourne des données spécifiques au rôle de l'utilisateur."""
    from datetime import datetime, timedelta
    from models import CourrierForward, Departement
    from sqlalchemy import func

    data = {}

    if user.role == 'super_admin':
        # Stats par statut
        statut_counts = db.session.query(
            Courrier.statut, func.count(Courrier.id)
        ).filter(Courrier.is_deleted == False).group_by(Courrier.statut).all()
        data['statut_counts'] = {s: c for s, c in statut_counts}

        # Top 5 départements par volume
        top_depts = db.session.query(
            Departement.nom, func.count(Courrier.id).label('nb')
        ).join(User, User.departement_id == Departement.id)\
         .join(Courrier, Courrier.utilisateur_id == User.id)\
         .filter(Courrier.is_deleted == False)\
         .group_by(Departement.nom)\
         .order_by(func.count(Courrier.id).desc())\
         .limit(5).all()
        data['top_depts'] = [{'nom': d, 'nb': n} for d, n in top_depts]

        # Courriers EN_COURS > 7 jours
        cutoff = datetime.utcnow() - timedelta(days=7)
        data['en_cours_retard'] = Courrier.query.filter(
            Courrier.is_deleted == False,
            Courrier.statut == 'EN_COURS',
            Courrier.date_modification_statut <= cutoff
        ).count()

    elif user.role == 'admin':
        dept_id = user.departement_id
        # Courriers du département
        dept_query = Courrier.query.join(User, Courrier.utilisateur_id == User.id)\
            .filter(User.departement_id == dept_id, Courrier.is_deleted == False)
        data['dept_total'] = dept_query.count()
        data['dept_non_traites'] = dept_query.filter(
            Courrier.statut.in_(['RECU', 'EN_COURS'])
        ).count()

        # Top utilisateurs actifs dans le département
        from models import LogActivite
        top_users = db.session.query(
            User.nom_complet, func.count(LogActivite.id).label('nb')
        ).join(LogActivite, LogActivite.utilisateur_id == User.id)\
         .filter(User.departement_id == dept_id)\
         .filter(LogActivite.date_action >= datetime.utcnow() - timedelta(days=30))\
         .group_by(User.nom_complet)\
         .order_by(func.count(LogActivite.id).desc())\
         .limit(5).all()
        data['top_users'] = [{'nom': n, 'nb': c} for n, c in top_users]

    else:  # user
        # Mes courriers en attente
        data['mes_en_attente'] = Courrier.query.filter(
            Courrier.utilisateur_id == user.id,
            Courrier.is_deleted == False,
            Courrier.statut.in_(['RECU', 'EN_COURS'])
        ).count()
        data['mes_total'] = Courrier.query.filter(
            Courrier.utilisateur_id == user.id,
            Courrier.is_deleted == False
        ).count()

        # Transmissions reçues récentes
        data['transmissions_recentes'] = CourrierForward.query.filter_by(
            forwarded_to_id=user.id
        ).order_by(CourrierForward.date_transmission.desc()).limit(5).all()

    return data

