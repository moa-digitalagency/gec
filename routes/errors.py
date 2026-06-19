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

def _error_page(code, title, message, icon='fa-triangle-exclamation', status=None):
    """Rend la page d'erreur autonome (URL concernée + bouton contextuel :
    tableau de bord si connecté, sinon retour à la connexion)."""
    try:
        authed = bool(current_user.is_authenticated)
    except Exception:
        authed = False
    return render_template('error.html', code=code, title=title, message=message,
                           icon=icon, error_url=request.url, authed=authed), (status or code)


@app.errorhandler(400)
def bad_request_error(error):
    return _error_page(400, 'Requête invalide',
                       "La requête n'a pas pu être traitée. Elle est peut-être malformée, "
                       "ou votre session a expiré. Reconnectez-vous puis réessayez.",
                       icon='fa-circle-exclamation')

@app.errorhandler(403)
def forbidden_error(error):
    from security import audit_log
    try:
        audit_log("ACCESS_DENIED", f"403 error for URL: {request.url}")
    except Exception:
        pass
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(429)
def rate_limit_error(error):
    from security import audit_log
    try:
        audit_log("RATE_LIMIT_EXCEEDED", f"Rate limit exceeded from IP: {request.remote_addr}")
    except Exception:
        pass
    return _error_page(429, 'Trop de requêtes',
                       "Vous avez effectué trop de requêtes en peu de temps. "
                       "Patientez un instant avant de réessayer.",
                       icon='fa-gauge-high')

@app.errorhandler(451)
def unavailable_for_legal_reasons_error(error):
    return _error_page(451, 'Indisponible pour raisons légales',
                       "Cette ressource est indisponible pour des raisons légales.",
                       icon='fa-scale-balanced')

@app.errorhandler(500)
def internal_error(error):
    try:
        db.session.rollback()
    except Exception:
        pass
    return _error_page(500, 'Erreur interne',
                       "Une erreur inattendue est survenue de notre côté. Réessayez dans un instant — "
                       "si le problème persiste, contactez le support.",
                       icon='fa-bug')

# Jeton CSRF expiré/invalide (formulaire resté ouvert trop longtemps → timeout de sécurité)
try:
    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        return _error_page(400, 'Session de sécurité expirée',
                           "Votre jeton de sécurité a expiré ou est invalide (page restée ouverte "
                           "trop longtemps). Reconnectez-vous puis renvoyez le formulaire.",
                           icon='fa-shield-halved')
except Exception:
    pass

