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
from routes.auth import apply_mail_access_filter
from utils.performance import cache_result, get_dashboard_statistics, optimize_search_query, PerformanceMonitor, clear_cache

KANBAN_COLUMNS = ['RECU', 'EN_COURS', 'TRAITE', 'ARCHIVE', 'REJETE']

@app.route('/kanban')
@login_required
def kanban_view():
    """Board Kanban — colonnes par statut avec drag & drop"""
    query = Courrier.query.filter(Courrier.is_deleted == False)
    query = apply_mail_access_filter(query, current_user)

    # Filtre optionnel par type
    type_courrier = request.args.get('type_courrier', '')
    if type_courrier:
        query = query.filter(Courrier.type_courrier == type_courrier)

    courriers = query.order_by(Courrier.date_enregistrement.desc()).all()

    columns = {s: [] for s in KANBAN_COLUMNS}
    for c in courriers:
        if c.statut in columns:
            columns[c.statut].append(c)
        else:
            columns.setdefault(c.statut, []).append(c)

    today = datetime.utcnow().date()
    return render_template(
        'kanban.html',
        columns=columns,
        kanban_columns=KANBAN_COLUMNS,
        today=today,
        type_courrier=type_courrier,
    )


@app.route('/api/courrier/<int:id>/move', methods=['PATCH'])
@login_required
def kanban_move_card(id):
    """Drag & drop — déplace un courrier vers un nouveau statut"""
    courrier = Courrier.query.get_or_404(id)
    if not current_user.can_view_courrier(courrier):
        return jsonify({'error': 'Accès refusé'}), 403

    data = request.get_json(silent=True) or {}
    new_statut = data.get('statut', '').strip().upper()
    if new_statut not in KANBAN_COLUMNS:
        return jsonify({'error': 'Statut invalide'}), 400

    old_statut = courrier.statut
    if old_statut == new_statut:
        return jsonify({'ok': True, 'statut': new_statut})

    courrier.statut = new_statut
    courrier.modifie_par_id = current_user.id

    from models import CourrierModification
    db.session.add(CourrierModification(
        courrier_id=courrier.id,
        utilisateur_id=current_user.id,
        champ_modifie='statut',
        ancienne_valeur=old_statut,
        nouvelle_valeur=new_statut,
        ip_address=get_client_ip()
    ))

    try:
        db.session.commit()
        log_activity(current_user.id, "KANBAN_MOVE",
                     f"Courrier {courrier.numero_accuse_reception} déplacé : {old_statut} → {new_statut}",
                     courrier.id)
        return jsonify({'ok': True, 'statut': new_statut})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur kanban_move_card: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================ #
#  C1 — Circuit de signature hiérarchique
# ============================================================ #

