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
from routes.auth import apply_mail_access_filter
from security import rate_limit, sanitize_input, validate_file_upload, log_security_event, record_failed_login, is_login_locked, reset_failed_login_attempts, get_client_ip, validate_password_strength, audit_log
from utils.performance import cache_result, get_dashboard_statistics, optimize_search_query, PerformanceMonitor, clear_cache

@app.route('/search')
@login_required
def search():
    from models import TypeCourrierSortant

    # Récupérer les statuts disponibles pour le formulaire
    statuts_disponibles = StatutCourrier.get_statuts_actifs()
    # Récupérer les types de courrier sortant pour le formulaire
    types_courrier_sortant = TypeCourrierSortant.get_types_actifs()

    # Logguer l'accès à la recherche (avec termes si déjà soumis)
    q = request.args.get('q') or request.args.get('search', '')
    if q:
        log_activity(current_user.id, "RECHERCHE_COURRIER",
                     f"Recherche avancée : \"{q[:120]}\"")
    else:
        log_activity(current_user.id, "NAVIGATION_RECHERCHE",
                     "Accès à la page de recherche avancée")

    return render_template('search.html',
                           statuts_disponibles=statuts_disponibles,
                           types_courrier_sortant=types_courrier_sortant)

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
        
        # Construire la requête avec restrictions selon le rôle (incluant transmissions)
        query = Courrier.query
        query = apply_mail_access_filter(query, current_user)
        
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

        # Rechercher dans les numéros de suivi (Évolution DPEM #6)
        results = query.filter(Courrier.numero_suivi.ilike(f'%{q}%')).limit(5).all()
        for r in results:
            if r.numero_suivi:
                suggestions.add(r.numero_suivi)
        
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

