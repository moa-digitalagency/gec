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
        
        # Build query with same logic as view_mail (incluant transmissions)
        query = Courrier.query
        query = apply_mail_access_filter(query, current_user)
        
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

@app.route('/export_mail_list_excel')
@login_required
def export_mail_list_excel():
    """Export filtered mail list to Excel (.xlsx)"""
    try:
        import io
        import xlsxwriter

        # Reuse the same filters as export_mail_list / view_mail
        search       = request.args.get('search', '')
        date_from    = request.args.get('date_from', '')
        date_to      = request.args.get('date_to', '')
        statut       = request.args.get('statut', '')
        type_courrier = request.args.get('type_courrier', '')
        sort_by      = request.args.get('sort_by', 'date_enregistrement')
        sort_order   = request.args.get('sort_order', 'desc')

        query = Courrier.query
        query = apply_mail_access_filter(query, current_user)

        if search:
            cond = optimize_search_query(search, Courrier)
            if cond is not None:
                query = query.filter(cond)
            else:
                query = query.filter(
                    or_(
                        Courrier.numero_accuse_reception.contains(search),
                        Courrier.objet.contains(search),
                        Courrier.expediteur.contains(search),
                        Courrier.destinataire.contains(search),
                    )
                )

        if type_courrier:
            query = query.filter(Courrier.type_courrier == type_courrier)
        if statut:
            query = query.filter(Courrier.statut == statut)
        if date_from:
            try:
                query = query.filter(
                    Courrier.date_enregistrement >= datetime.strptime(date_from, '%Y-%m-%d').date()
                )
            except ValueError:
                pass
        if date_to:
            try:
                query = query.filter(
                    Courrier.date_enregistrement <= datetime.strptime(date_to, '%Y-%m-%d').date()
                )
            except ValueError:
                pass

        if sort_by in ['date_enregistrement', 'numero_accuse_reception', 'expediteur', 'objet', 'statut']:
            col = getattr(Courrier, sort_by)
            query = query.order_by(col.desc() if sort_order == 'desc' else col.asc())

        courriers = query.all()

        # ------------------------------------------------------------------ #
        # Build workbook in memory
        # ------------------------------------------------------------------ #
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})

        # --- Formats ---
        hdr_fmt = wb.add_format({
            'bold': True, 'bg_color': '#1e40af', 'font_color': '#ffffff',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True
        })
        cell_fmt = wb.add_format({'border': 1, 'valign': 'vcenter', 'text_wrap': True})
        date_fmt = wb.add_format({'border': 1, 'valign': 'vcenter', 'num_format': 'dd/mm/yyyy'})
        retard_fmt = wb.add_format({
            'border': 1, 'valign': 'vcenter', 'bg_color': '#fee2e2', 'font_color': '#991b1b'
        })
        even_fmt = wb.add_format({'border': 1, 'valign': 'vcenter', 'bg_color': '#f0f9ff', 'text_wrap': True})
        statut_colors = {
            'RECU':      ('#dcfce7', '#166534'),
            'EN_COURS':  ('#fef9c3', '#854d0e'),
            'TRAITE':    ('#dbeafe', '#1e40af'),
            'ARCHIVE':   ('#f3f4f6', '#374151'),
            'REJETE':    ('#fee2e2', '#991b1b'),
        }

        # ================================================================== #
        # Sheet 1 — Liste des courriers
        # ================================================================== #
        ws = wb.add_worksheet('Courriers')
        ws.freeze_panes(1, 0)
        ws.set_zoom(90)

        headers = [
            ('N° Accusé',          20),
            ('Type',               12),
            ('N° Référence',       18),
            ('Expéditeur',         25),
            ('Destinataire',       25),
            ('Objet',              40),
            ('Date Rédaction',     15),
            ('Date Enregistrement',18),
            ('Statut',             14),
            ('Échéance',           14),
            ('Tags',               20),
        ]
        for col_idx, (title, width) in enumerate(headers):
            ws.write(0, col_idx, title, hdr_fmt)
            ws.set_column(col_idx, col_idx, width)
        ws.set_row(0, 28)

        today = datetime.utcnow().date()
        for row_idx, c in enumerate(courriers, start=1):
            is_retard = (c.due_date and c.due_date < today and
                         c.statut not in ('TRAITE', 'ARCHIVE', 'REJETE'))
            base = retard_fmt if is_retard else (even_fmt if row_idx % 2 == 0 else cell_fmt)

            # Statut coloured format
            bg, fg = statut_colors.get(c.statut, ('#ffffff', '#111827'))
            s_fmt = wb.add_format({
                'border': 1, 'valign': 'vcenter',
                'bg_color': bg, 'font_color': fg, 'bold': True, 'align': 'center'
            })

            tags_str = ', '.join(t.tag.nom for t in c.tags.all()) if c.tags else ''

            ws.write(row_idx, 0,  c.numero_accuse_reception or '', base)
            ws.write(row_idx, 1,  c.type_courrier or '', base)
            ws.write(row_idx, 2,  str(c.numero_reference) if c.numero_reference else '', base)
            ws.write(row_idx, 3,  c.expediteur or '', base)
            ws.write(row_idx, 4,  c.destinataire or '', base)
            ws.write(row_idx, 5,  c.objet or '', base)
            if c.date_redaction:
                ws.write_datetime(row_idx, 6, datetime.combine(c.date_redaction, datetime.min.time()), date_fmt)
            else:
                ws.write(row_idx, 6, '', base)
            if c.date_enregistrement:
                ws.write_datetime(row_idx, 7, datetime.combine(c.date_enregistrement, datetime.min.time()), date_fmt)
            else:
                ws.write(row_idx, 7, '', base)
            ws.write(row_idx, 8,  c.statut or '', s_fmt)
            if c.due_date:
                ws.write_datetime(row_idx, 9, datetime.combine(c.due_date, datetime.min.time()), date_fmt)
            else:
                ws.write(row_idx, 9, '', base)
            ws.write(row_idx, 10, tags_str, base)

        # ================================================================== #
        # Sheet 2 — Statistiques
        # ================================================================== #
        ws2 = wb.add_worksheet('Statistiques')
        ws2.set_column(0, 0, 30)
        ws2.set_column(1, 1, 15)

        title_fmt = wb.add_format({
            'bold': True, 'font_size': 14, 'bg_color': '#1e40af',
            'font_color': '#ffffff', 'border': 1
        })
        sub_fmt = wb.add_format({'bold': True, 'bg_color': '#dbeafe', 'border': 1})
        num_fmt = wb.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0'})

        ws2.merge_range('A1:B1', 'Statistiques — Liste des courriers', title_fmt)
        ws2.set_row(0, 24)

        ws2.write(1, 0, 'Total courriers exportés', sub_fmt)
        ws2.write(1, 1, len(courriers), num_fmt)

        # Filtres appliqués
        ws2.write(3, 0, 'Filtres appliqués', sub_fmt)
        ws2.write(3, 1, '', sub_fmt)
        filter_rows = [
            ('Recherche',    search or '—'),
            ('Type',         type_courrier or '—'),
            ('Statut',       statut or '—'),
            ('Date début',   date_from or '—'),
            ('Date fin',     date_to or '—'),
        ]
        for i, (k, v) in enumerate(filter_rows, start=4):
            ws2.write(i, 0, k, cell_fmt)
            ws2.write(i, 1, v, cell_fmt)

        # Répartition par statut
        row = 4 + len(filter_rows) + 1
        ws2.write(row, 0, 'Répartition par statut', sub_fmt)
        ws2.write(row, 1, 'Nombre', sub_fmt)
        row += 1
        from collections import Counter
        statut_counts = Counter(c.statut for c in courriers if c.statut)
        for s, cnt in sorted(statut_counts.items()):
            bg2, fg2 = statut_colors.get(s, ('#ffffff', '#111827'))
            s2_fmt = wb.add_format({'border': 1, 'bg_color': bg2, 'font_color': fg2, 'bold': True})
            n2_fmt = wb.add_format({'border': 1, 'align': 'right', 'bg_color': bg2})
            ws2.write(row, 0, s, s2_fmt)
            ws2.write(row, 1, cnt, n2_fmt)
            row += 1

        # Répartition par type
        row += 1
        ws2.write(row, 0, 'Répartition par type', sub_fmt)
        ws2.write(row, 1, 'Nombre', sub_fmt)
        row += 1
        type_counts = Counter(c.type_courrier for c in courriers if c.type_courrier)
        for t, cnt in sorted(type_counts.items()):
            ws2.write(row, 0, t, cell_fmt)
            ws2.write(row, 1, cnt, num_fmt)
            row += 1

        # Courriers en retard
        retard_list = [c for c in courriers if c.due_date and c.due_date < today
                       and c.statut not in ('TRAITE', 'ARCHIVE', 'REJETE')]
        row += 1
        ws2.write(row, 0, 'Courriers en retard (échéance dépassée)', sub_fmt)
        ws2.write(row, 1, len(retard_list), num_fmt)

        # Export info
        row += 2
        info_fmt = wb.add_format({'italic': True, 'font_color': '#6b7280', 'border': 1})
        ws2.write(row, 0, 'Généré le', info_fmt)
        ws2.write(row, 1, datetime.now().strftime('%d/%m/%Y %H:%M'), info_fmt)

        wb.close()
        output.seek(0)

        log_activity(current_user.id, "EXPORT_LISTE_EXCEL",
                     f"Export Excel de {len(courriers)} courriers")

        filename_parts = ['liste_courriers']
        if search:
            filename_parts.append(f"recherche_{search[:20]}")
        if type_courrier:
            filename_parts.append(type_courrier.lower())
        if date_from or date_to:
            filename_parts.append("filtre_date")
        filename_parts.append(datetime.now().strftime('%Y%m%d_%H%M'))
        filename = '_'.join(filename_parts) + '.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logging.error(f"Erreur lors de l'export Excel de la liste: {e}")
        flash("Erreur lors de l'export Excel.", 'error')
        return redirect(url_for('view_mail'))


@app.route('/export_logs_pdf')
@login_required
def export_logs_pdf_route():
    """Exporter les logs d'activité en PDF - accessible uniquement aux super admins"""
    if not current_user.is_super_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Récupérer les mêmes filtres que la route view_logs
        search = request.args.get('search', '')
        action_filter = request.args.get('action', '')
        user_filter = request.args.get('user_id', '', type=str)
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Construction de la requête avec les mêmes filtres
        query = LogActivite.query.join(User).order_by(LogActivite.date_action.desc())
        
        # Appliquer les filtres
        if search:
            query = query.filter(
                db.or_(
                    LogActivite.action.contains(search),
                    LogActivite.description.contains(search),
                    User.username.contains(search),
                    User.nom_complet.contains(search)
                )
            )
        
        if action_filter:
            query = query.filter(LogActivite.action == action_filter)
        
        if user_filter:
            query = query.filter(LogActivite.utilisateur_id == user_filter)
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(LogActivite.date_action >= date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
                query = query.filter(LogActivite.date_action <= date_to_obj)
            except ValueError:
                pass
        
        # Limiter à 1000 entrées maximum pour éviter les PDFs trop volumineux
        logs = query.limit(1000).all()
        
        # Préparer les informations de filtres pour le PDF
        filters = {
            'search': search,
            'action_filter': action_filter,
            'user_filter': user_filter,
            'date_from': date_from,
            'date_to': date_to
        }
        
        # Générer le PDF
        from utils import export_logs_pdf
        pdf_path = export_logs_pdf(logs, filters)
        
        # Logger cette action d'export
        log_activity(current_user.id, "EXPORT_LOGS_PDF", 
                    f"Export PDF des logs d'activité ({len(logs)} entrées)")
        
        # Télécharger le fichier PDF
        import os
        from flask import send_from_directory
        directory = os.path.dirname(pdf_path)
        filename = os.path.basename(pdf_path)
        return send_from_directory(directory, filename, 
                                 as_attachment=True, 
                                 download_name=f"journal_activites_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                 mimetype='application/pdf')
                                 
    except Exception as e:
        logging.error(f"Erreur lors de l'export PDF des logs: {e}")
        flash('Erreur lors de l\'export PDF des logs d\'activité.', 'error')
        return redirect(url_for('view_logs'))

@app.route('/export_analytics/<format>')
@login_required
def export_analytics(format):
    """Export des données analytiques en PDF ou Excel"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from flask import send_file
    import io
    
    if format not in ['pdf', 'excel']:
        flash('Format d\'export invalide', 'error')
        return redirect(url_for('analytics'))
    
    # Collecter les mêmes données que pour la page analytics
    total_courriers = Courrier.query.filter_by(is_deleted=False).count()
    courriers_entrants = Courrier.query.filter_by(type_courrier='ENTRANT', is_deleted=False).count()
    courriers_sortants = Courrier.query.filter_by(type_courrier='SORTANT', is_deleted=False).count()
    
    # Calculer les statistiques par période
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
    
    # Top expéditeurs pour le PDF
    top_senders = db.session.query(
        Courrier.expediteur,
        func.count(Courrier.id).label('count')
    ).filter(
        Courrier.is_deleted == False,
        Courrier.expediteur.isnot(None),
        Courrier.expediteur != ''
    ).group_by(Courrier.expediteur).order_by(
        func.count(Courrier.id).desc()
    ).limit(10).all()
    
    if format == 'excel':
        try:
            import pandas as pd
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
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.graphics.shapes import Drawing
            from reportlab.graphics.charts.barcharts import VerticalBarChart
            from reportlab.graphics.charts.piecharts import Pie
            from reportlab.graphics.charts.legends import Legend
        except ImportError:
            flash('ReportLab n\'est pas installé. Impossible d\'exporter en PDF.', 'error')
            return redirect(url_for('analytics'))
        
        # Récupérer toutes les données analytiques comme dans la fonction analytics()
        # Copier les calculs de la fonction analytics() pour avoir toutes les données
        
        # Filtres de base
        base_filter = [Courrier.is_deleted == False]
        
        # Statistiques par département
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
        
        # Statistiques par utilisateur (top 10)
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
        
        # Top destinataires
        recipient_filter = base_filter + [
            Courrier.destinataire != None,
            Courrier.destinataire != ''
        ]
        top_recipients = db.session.query(
            Courrier.destinataire,
            func.count(Courrier.id).label('count')
        ).filter(*recipient_filter).group_by(Courrier.destinataire).order_by(func.count(Courrier.id).desc()).limit(10).all()
        
        # Répartition par statut
        status_distribution = db.session.query(
            Courrier.statut,
            func.count(Courrier.id).label('count')
        ).filter(*base_filter).group_by(Courrier.statut).all()
        
        # Volume par mois (6 derniers mois)
        monthly_volumes = []
        for i in range(6):
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
            monthly_volumes.append({
                'month': month_start.strftime('%B %Y'),
                'entrants': entrants,
                'sortants': sortants,
                'total': entrants + sortants
            })
        monthly_volumes.reverse()
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        elements = []
        styles = getSampleStyleSheet()
        
        # Titre principal
        title = Paragraph("Rapport Analytique Complet - GEC", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Date du rapport
        date_para = Paragraph(f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
        elements.append(date_para)
        elements.append(Spacer(1, 30))
        
        # ===================
        # 1. STATISTIQUES GÉNÉRALES
        # ===================
        stats_title = Paragraph("1. Statistiques Générales", styles['Heading2'])
        elements.append(stats_title)
        elements.append(Spacer(1, 10))
        
        stats_data = [
            ['Métrique', 'Valeur'],
            ['Total Courriers', str(total_courriers)],
            ['Courriers Entrants', str(courriers_entrants)],
            ['Courriers Sortants', str(courriers_sortants)],
            ['7 Derniers Jours', str(courriers_7_days)],
            ['30 Derniers Jours', str(courriers_30_days)]
        ]
        
        stats_table = Table(stats_data, colWidths=[10*cm, 5*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
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
        
        # ===================
        # 2. STATISTIQUES PAR DÉPARTEMENT
        # ===================
        # Récupérer l'appellation dynamique
        parametres = ParametresSysteme.get_parametres()
        appellation = getattr(parametres, 'appellation_departement', 'Départements') or 'Départements'
        dept_title = Paragraph(f"2. Statistiques par {appellation[:-1]}", styles['Heading2'])
        elements.append(dept_title)
        elements.append(Spacer(1, 10))
        
        if dept_stats:
            dept_data = [[appellation[:-1], 'Total', 'Entrants', 'Sortants']]
            for dept in dept_stats[:10]:  # Top 10 départements
                dept_data.append([
                    dept.departement[:30] + '...' if len(dept.departement) > 30 else dept.departement,
                    str(dept.total),
                    str(dept.entrants),
                    str(dept.sortants)
                ])
            
            dept_table = Table(dept_data, colWidths=[7*cm, 3*cm, 3*cm, 3*cm])
            dept_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            elements.append(dept_table)
        elements.append(Spacer(1, 30))
        
        # ===================
        # 3. TOP 10 UTILISATEURS
        # ===================
        users_title = Paragraph("3. Top 10 Utilisateurs les Plus Actifs", styles['Heading2'])
        elements.append(users_title)
        elements.append(Spacer(1, 10))
        
        if user_stats:
            user_data = [['Utilisateur', 'Total', 'Entrants', 'Sortants']]
            for user in user_stats:
                user_data.append([
                    user.nom_complet[:30] + '...' if len(user.nom_complet) > 30 else user.nom_complet,
                    str(user.total),
                    str(user.entrants),
                    str(user.sortants)
                ])
            
            user_table = Table(user_data, colWidths=[7*cm, 3*cm, 3*cm, 3*cm])
            user_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkorange),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            elements.append(user_table)
        elements.append(Spacer(1, 30))
        
        # ===================
        # 4. TOP EXPÉDITEURS
        # ===================
        if top_senders:
            senders_title = Paragraph("4. Top 10 Expéditeurs", styles['Heading2'])
            elements.append(senders_title)
            elements.append(Spacer(1, 10))
            
            senders_data = [['Expéditeur', 'Nombre de Courriers']]
            for sender in top_senders:
                senders_data.append([
                    sender.expediteur[:40] + '...' if len(sender.expediteur) > 40 else sender.expediteur,
                    str(sender.count)
                ])
            
            senders_table = Table(senders_data, colWidths=[12*cm, 4*cm])
            senders_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.mistyrose),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            elements.append(senders_table)
            elements.append(Spacer(1, 30))
        
        # ===================
        # 5. TOP DESTINATAIRES
        # ===================
        if top_recipients:
            recipients_title = Paragraph("5. Top 10 Destinataires", styles['Heading2'])
            elements.append(recipients_title)
            elements.append(Spacer(1, 10))
            
            recipients_data = [['Destinataire', 'Nombre de Courriers']]
            for recipient in top_recipients:
                recipients_data.append([
                    recipient.destinataire[:40] + '...' if len(recipient.destinataire) > 40 else recipient.destinataire,
                    str(recipient.count)
                ])
            
            recipients_table = Table(recipients_data, colWidths=[12*cm, 4*cm])
            recipients_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.purple),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lavender),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            elements.append(recipients_table)
            elements.append(PageBreak())
        
        # ===================
        # 6. RÉPARTITION PAR STATUT
        # ===================
        if status_distribution:
            status_title = Paragraph("6. Répartition par Statut", styles['Heading2'])
            elements.append(status_title)
            elements.append(Spacer(1, 10))
            
            status_data = [['Statut', 'Nombre de Courriers', 'Pourcentage']]
            total_status = sum([s.count for s in status_distribution])
            for status in status_distribution:
                percentage = round((status.count / total_status) * 100, 1) if total_status > 0 else 0
                status_data.append([
                    status.statut or 'Non défini',
                    str(status.count),
                    f"{percentage}%"
                ])
            
            status_table = Table(status_data, colWidths=[6*cm, 5*cm, 4*cm])
            status_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            elements.append(status_table)
            elements.append(Spacer(1, 30))
        
        # ===================
        # 7. ÉVOLUTION MENSUELLE (6 DERNIERS MOIS)
        # ===================
        if monthly_volumes:
            monthly_title = Paragraph("7. Évolution Mensuelle (6 Derniers Mois)", styles['Heading2'])
            elements.append(monthly_title)
            elements.append(Spacer(1, 10))
            
            monthly_data = [['Mois', 'Entrants', 'Sortants', 'Total']]
            for month in monthly_volumes:
                monthly_data.append([
                    month['month'],
                    str(month['entrants']),
                    str(month['sortants']),
                    str(month['total'])
                ])
            
            monthly_table = Table(monthly_data, colWidths=[5*cm, 3.5*cm, 3.5*cm, 4*cm])
            monthly_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            elements.append(monthly_table)
            elements.append(Spacer(1, 30))
        
        # ===================
        # 8. GRAPHIQUES VISUELS
        # ===================
        
        # Saut de page pour les graphiques
        elements.append(PageBreak())
        
        charts_title = Paragraph("8. Graphiques et Visualisations", styles['Heading2'])
        elements.append(charts_title)
        elements.append(Spacer(1, 20))
        
        # Graphique en barres : Évolution mensuelle
        if monthly_volumes:
            monthly_chart_title = Paragraph("Évolution Mensuelle (Barres)", styles['Heading3'])
            elements.append(monthly_chart_title)
            elements.append(Spacer(1, 10))
            
            # Créer le graphique en barres
            drawing = Drawing(400, 200)
            chart = VerticalBarChart()
            chart.x = 50
            chart.y = 50
            chart.height = 125
            chart.width = 300
            
            # Données pour le graphique
            months_data = [vol['total'] for vol in monthly_volumes]
            chart.data = [months_data]
            chart.categoryAxis.categoryNames = [vol['month'][:7] for vol in monthly_volumes]  # Raccourcir les noms
            
            # Style du graphique
            chart.bars[0].fillColor = colors.darkblue
            chart.valueAxis.valueMin = 0
            chart.valueAxis.valueMax = max(months_data) * 1.1 if months_data else 10
            chart.categoryAxis.labels.angle = 45
            chart.categoryAxis.labels.fontSize = 8
            
            drawing.add(chart)
            elements.append(drawing)
            elements.append(Spacer(1, 20))
        
        # Graphique en camembert : Répartition par statut
        if status_distribution:
            pie_chart_title = Paragraph("Répartition par Statut (Camembert)", styles['Heading3'])
            elements.append(pie_chart_title)
            elements.append(Spacer(1, 10))
            
            # Créer le graphique en camembert
            drawing = Drawing(400, 200)
            pie = Pie()
            pie.x = 65
            pie.y = 15
            pie.width = 100
            pie.height = 100
            
            # Données pour le camembert
            pie.data = [s.count for s in status_distribution]
            pie.labels = [s.statut or 'Non défini' for s in status_distribution]
            
            # Couleurs variées
            colors_list = [colors.red, colors.green, colors.blue, colors.orange, colors.purple, colors.yellow, colors.pink, colors.brown]
            pie.slices.strokeColor = colors.white
            for i, color in enumerate(colors_list[:len(status_distribution)]):
                pie.slices[i].fillColor = color
            
            # Ajouter une légende
            legend = Legend()
            legend.x = 200
            legend.y = 50
            legend.dx = 8
            legend.dy = 8
            legend.fontName = 'Helvetica'
            legend.fontSize = 9
            legend.boxAnchor = 'w'
            legend.columnMaximum = 6
            legend.strokeWidth = 1
            legend.strokeColor = colors.black
            legend.deltax = 75
            legend.deltay = 10
            legend.autoXPadding = 5
            legend.yGap = 0
            legend.dxTextSpace = 5
            legend.alignment = 'left'
            legend.dividerLines = 1|2|4
            legend.dividerOffsY = 4.5
            legend.subCols.rpad = 30
            
            legend.colorNamePairs = [(pie.slices[i].fillColor, (pie.labels[i][:15] + '...' if len(pie.labels[i]) > 15 else pie.labels[i])) for i in range(len(pie.labels))]
            
            drawing.add(pie)
            drawing.add(legend)
            elements.append(drawing)
            elements.append(Spacer(1, 30))
        
        # Graphique en barres : Top départements
        if dept_stats:
            dept_chart_title = Paragraph(f"Top 5 {appellation} (Barres)", styles['Heading3'])
            elements.append(dept_chart_title)
            elements.append(Spacer(1, 10))
            
            # Créer le graphique en barres pour départements
            drawing = Drawing(400, 200)
            chart = VerticalBarChart()
            chart.x = 50
            chart.y = 50
            chart.height = 125
            chart.width = 300
            
            # Données pour le graphique (top 5)
            top5_depts = dept_stats[:5]
            dept_data = [dept.total for dept in top5_depts]
            chart.data = [dept_data]
            chart.categoryAxis.categoryNames = [dept.departement[:15] + '...' if len(dept.departement) > 15 else dept.departement for dept in top5_depts]
            
            # Style du graphique
            chart.bars[0].fillColor = colors.darkgreen
            chart.valueAxis.valueMin = 0
            chart.valueAxis.valueMax = max(dept_data) * 1.1 if dept_data else 10
            chart.categoryAxis.labels.angle = 45
            chart.categoryAxis.labels.fontSize = 8
            
            drawing.add(chart)
            elements.append(drawing)
            elements.append(Spacer(1, 30))
        
        # Footer avec informations du système et utilisateur
        footer_para = Paragraph(
            f"<i>Ce rapport a été généré automatiquement par le système GEC - Gestion Électronique du Courrier<br/>"
            f"Total de {total_courriers} courriers analysés - Généré par: {current_user.nom_complet}<br/>"
            f"Page générée le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</i>",
            styles['Normal']
        )
        elements.append(footer_para)
        
        doc.build(elements)
        
        buffer.seek(0)
        return send_file(buffer,
                        mimetype='application/pdf',
                        as_attachment=True,
                        download_name=f'analytics_report_complet_{datetime.now().strftime("%Y%m%d")}.pdf')

