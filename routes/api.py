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

@app.route('/api/tags', methods=['GET'])
@login_required
def api_tags_list():
    q = request.args.get('q', '').strip()
    query = Tag.query
    if q:
        query = query.filter(Tag.nom.ilike(f'%{q}%'))
    tags = query.order_by(Tag.nom).limit(20).all()
    return jsonify([{'id': t.id, 'nom': t.nom, 'couleur': t.couleur} for t in tags])


@app.route('/api/tags', methods=['POST'])
@login_required
def api_tag_create():
    data = request.get_json(silent=True) or {}
    nom = sanitize_input(data.get('nom', '').strip())[:50]
    couleur = data.get('couleur', '#6B7280')
    if not nom:
        return jsonify({'error': 'Nom requis'}), 400
    existing = Tag.query.filter_by(nom=nom).first()
    if existing:
        return jsonify({'id': existing.id, 'nom': existing.nom, 'couleur': existing.couleur})
    tag = Tag(nom=nom, couleur=couleur, created_by_id=current_user.id)
    db.session.add(tag)
    db.session.commit()
    return jsonify({'id': tag.id, 'nom': tag.nom, 'couleur': tag.couleur}), 201


@app.route('/api/courrier/<int:id>/tags', methods=['POST'])
@login_required
def api_courrier_update_tags(id):
    courrier = Courrier.query.get_or_404(id)
    if not current_user.can_view_courrier(courrier):
        abort(403)
    data = request.get_json(silent=True) or {}
    tag_ids = [int(x) for x in data.get('tag_ids', []) if str(x).isdigit()]

    # Supprimer les liaisons existantes
    CourrierTag.query.filter_by(courrier_id=id).delete()
    # Recréer
    for tid in tag_ids:
        tag = Tag.query.get(tid)
        if tag:
            ct = CourrierTag(courrier_id=id, tag_id=tid, added_by_id=current_user.id)
            db.session.add(ct)
    db.session.commit()
    log_activity(current_user.id, "UPDATE_TAGS",
                 f"Tags mis à jour sur courrier {courrier.numero_accuse_reception}", id)
    return jsonify({'ok': True, 'count': len(tag_ids)})


@app.route('/api/courrier/<int:id>/timeline')
@login_required
def courrier_timeline(id):
    courrier = Courrier.query.get_or_404(id)
    if not current_user.can_view_courrier(courrier):
        abort(403)

    from models import CourrierModification, CourrierComment, CourrierForward

    events = []

    # Enregistrement initial
    events.append({
        'type': 'creation',
        'icon': 'fa-plus-circle',
        'color': 'green',
        'title': 'Courrier enregistré',
        'detail': f'N° {courrier.numero_accuse_reception} — statut initial : {courrier.statut}',
        'user': courrier.utilisateur_enregistrement.nom_complet if courrier.utilisateur_enregistrement else 'Système',
        'date': courrier.date_enregistrement.strftime('%d/%m/%Y %H:%M') if courrier.date_enregistrement else '',
        'ts': courrier.date_enregistrement.timestamp() if courrier.date_enregistrement else 0,
    })

    # Changements de statut
    mods = CourrierModification.query.filter_by(
        courrier_id=id, champ_modifie='statut'
    ).order_by(CourrierModification.date_modification.asc()).all()
    for m in mods:
        events.append({
            'type': 'statut',
            'icon': 'fa-exchange-alt',
            'color': 'blue',
            'title': f'Statut → {m.nouvelle_valeur}',
            'detail': f'Précédent : {m.ancienne_valeur}',
            'user': m.utilisateur.nom_complet if m.utilisateur else '?',
            'date': m.date_modification.strftime('%d/%m/%Y %H:%M') if m.date_modification else '',
            'ts': m.date_modification.timestamp() if m.date_modification else 0,
        })

    # Transmissions
    forwards = CourrierForward.query.filter_by(courrier_id=id).order_by(CourrierForward.date_envoi.asc()).all()
    for f in forwards:
        dest_name = f.forwarded_to.nom_complet if f.forwarded_to else '?'
        src_name = f.forwarded_by.nom_complet if f.forwarded_by else '?'
        events.append({
            'type': 'transmission',
            'icon': 'fa-share',
            'color': 'purple',
            'title': f'Transmis à {dest_name}',
            'detail': f.message[:80] + '…' if f.message and len(f.message) > 80 else (f.message or ''),
            'user': src_name,
            'date': f.date_transmission.strftime('%d/%m/%Y %H:%M') if f.date_transmission else '',
            'ts': f.date_transmission.timestamp() if f.date_transmission else 0,
        })

    # Commentaires
    comments = CourrierComment.query.filter_by(courrier_id=id).order_by(CourrierComment.date_creation.asc()).all()
    for c in comments:
        events.append({
            'type': 'comment',
            'icon': 'fa-comment',
            'color': 'yellow',
            'title': 'Commentaire ajouté',
            'detail': c.contenu[:80] + '…' if c.contenu and len(c.contenu) > 80 else (c.contenu or ''),
            'user': c.auteur.nom_complet if c.auteur else '?',
            'date': c.date_creation.strftime('%d/%m/%Y %H:%M') if c.date_creation else '',
            'ts': c.date_creation.timestamp() if c.date_creation else 0,
        })

    events.sort(key=lambda e: e['ts'])
    return jsonify(events)


@app.route('/api/courrier/<int:id>/verify_signatures')
@login_required
def verify_signatures(id):
    """Revalide toute la chaîne de hashes pour un courrier.
    Retourne { valid: bool, entries: int, broken_at: int|null }
    """
    import hashlib
    from models.courrier import CourrierActionSignature

    courrier = Courrier.query.get_or_404(id)
    if not current_user.can_view_courrier(courrier):
        abort(403)

    entries = (CourrierActionSignature.query
               .filter_by(courrier_id=id)
               .order_by(CourrierActionSignature.timestamp.asc())
               .all())

    if not entries:
        return jsonify({'valid': True, 'entries': 0, 'broken_at': None})

    expected_prev = '0' * 64
    for entry in entries:
        if entry.previous_hash != expected_prev:
            return jsonify({'valid': False, 'entries': len(entries), 'broken_at': entry.id})

        payload = (f"{entry.timestamp.isoformat()}|{entry.user_id}|{entry.action_type}|"
                   f"{entry.courrier_id}|{entry.details or ''}|{entry.previous_hash}")
        computed = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        if computed != entry.hash_signature:
            return jsonify({'valid': False, 'entries': len(entries), 'broken_at': entry.id})

        expected_prev = entry.hash_signature

    return jsonify({'valid': True, 'entries': len(entries), 'broken_at': None})


