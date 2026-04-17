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

@app.route("/security_logs")
@login_required
def security_logs():
    # Vérifier les permissions d'accès aux logs de sécurité
    if not (current_user.has_permission('view_security_logs') or current_user.is_super_admin()):
        flash('Vous n\'avez pas les permissions pour consulter les logs de sécurité.', 'error')
        return redirect(url_for('dashboard'))
    
    from security import get_security_logs, get_security_stats
    
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
        
    from security import (MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_DURATION, 
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
            from models import IPBlock
            cleared_ips = IPBlock.unblock_all_ips()
            _blocked_ips.clear()
            _failed_login_attempts.clear()
            flash(f'{cleared_ips} adresses IP débloquées', 'success')
            log_activity(current_user.id, "SECURITY_UNBLOCK", f"Toutes les IP bloquées débloquées ({cleared_ips})")
        
        elif form_type == 'unblock_ip':
            # Débloquer une IP spécifique
            from models import IPBlock
            ip_address = request.form.get('ip_address')
            if ip_address:
                success = IPBlock.unblock_ip(ip_address)
                if ip_address in _blocked_ips:
                    _blocked_ips.remove(ip_address)
                if ip_address in _failed_login_attempts:
                    del _failed_login_attempts[ip_address]
                
                if success:
                    flash(f'Adresse IP {ip_address} débloquée avec succès', 'success')
                    log_activity(current_user.id, "SECURITY_UNBLOCK", f"IP {ip_address} débloquée manuellement")
                    log_security_event("IP_UNBLOCK", f"IP {ip_address} unblocked by {current_user.username}")
                else:
                    flash(f'Adresse IP {ip_address} non trouvée dans la liste des IP bloquées', 'error')
                    
        elif form_type == 'add_whitelist':
            # Ajouter une IP à la whitelist
            from models import IPWhitelist
            ip_address = request.form.get('whitelist_ip', '').strip()
            description = request.form.get('whitelist_description', '').strip()
            
            if ip_address:
                success = IPWhitelist.add_to_whitelist(ip_address, description, current_user.username)
                if success:
                    flash(f'IP {ip_address} ajoutée à la whitelist avec succès', 'success')
                    log_activity(current_user.id, "SECURITY_WHITELIST", f"IP {ip_address} ajoutée à la whitelist")
                else:
                    flash(f'Erreur lors de l\'ajout de l\'IP {ip_address} à la whitelist', 'error')
            else:
                flash('Veuillez saisir une adresse IP valide', 'error')
                
        elif form_type == 'remove_whitelist':
            # Retirer une IP de la whitelist
            from models import IPWhitelist
            ip_address = request.form.get('ip_address')
            if ip_address:
                success = IPWhitelist.remove_from_whitelist(ip_address)
                if success:
                    flash(f'IP {ip_address} retirée de la whitelist', 'success')
                    log_activity(current_user.id, "SECURITY_WHITELIST", f"IP {ip_address} retirée de la whitelist")
                else:
                    flash(f'Erreur lors de la suppression de l\'IP {ip_address}', 'error')
        
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
    
    # Récupérer les listes d'IPs bloquées et en whitelist
    from models import IPBlock, IPWhitelist
    blocked_ips = [block.ip_address for block in IPBlock.get_blocked_ips()]
    whitelisted_ips = IPWhitelist.get_whitelisted_ips()
    
    return render_template('security_settings.html',
                         max_login_attempts=MAX_LOGIN_ATTEMPTS,
                         lockout_duration=LOGIN_LOCKOUT_DURATION,
                         rate_limit_requests=10,  # Cette valeur devrait venir de la configuration
                         suspicious_threshold=SUSPICIOUS_ACTIVITY_THRESHOLD,
                         auto_block_duration=AUTO_BLOCK_DURATION,
                         audit_logging_enabled=True,  # Cette valeur devrait venir de la configuration
                         blocked_ips=list(set(blocked_ips + list(_blocked_ips))),  # Combine et déduplique
                         whitelisted_ips=whitelisted_ips,
                         failed_attempts_24h=failed_attempts_24h,
                         monitored_ips=len(_failed_login_attempts))

def export_security_logs(level, event_type, date_start, date_end):
    """Exporte les logs de sécurité en CSV"""
    from security import get_security_logs
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
    # Vérification des permissions
    if not current_user.is_super_admin():
        flash('Accès refusé. Seuls les super administrateurs peuvent accéder aux analyses.', 'error')
        return redirect(url_for('dashboard'))
    
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

    log_activity(current_user.id, "NAVIGATION_ANALYTIQUE",
                 f"Consultation tableau analytique (période: {period}, total: {total_courriers} courriers)")

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


