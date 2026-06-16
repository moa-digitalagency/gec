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

@app.route('/delete_notification/<int:notification_id>', methods=['POST'])
@login_required
def delete_notification(notification_id):
    """Supprimer une notification de l'utilisateur"""
    notification = Notification.query.get_or_404(notification_id)

    # Vérifier que la notification appartient à l'utilisateur actuel
    if notification.user_id != current_user.id:
        flash('Accès refusé.', 'error')
        return redirect(url_for('notifications'))

    try:
        db.session.delete(notification)
        db.session.commit()
        flash('Notification supprimée.', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de la suppression de la notification: {e}")
        flash('Erreur lors de la suppression de la notification.', 'error')

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

# ===== GESTION DES LANGUES =====

