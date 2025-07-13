import os
import uuid
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session, send_file, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_
import logging

from app import app, db
from models import User, Courrier, LogActivite, ParametresSysteme
from utils import allowed_file, generate_accuse_reception, log_activity, export_courrier_pdf

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password) and user.actif:
            login_user(user)
            log_activity(user.id, "CONNEXION", f"Connexion réussie pour {username}")
            flash('Connexion réussie!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_activity(current_user.id, "DECONNEXION", f"Déconnexion de {current_user.username}")
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Statistiques pour le tableau de bord
    total_courriers = Courrier.query.count()
    courriers_today = Courrier.query.filter(
        Courrier.date_enregistrement >= datetime.now().date()
    ).count()
    
    # Derniers courriers enregistrés
    recent_courriers = Courrier.query.order_by(
        Courrier.date_enregistrement.desc()
    ).limit(5).all()
    
    return render_template('dashboard.html', 
                         total_courriers=total_courriers,
                         courriers_today=courriers_today,
                         recent_courriers=recent_courriers)

@app.route('/register_mail', methods=['GET', 'POST'])
@login_required
def register_mail():
    if request.method == 'POST':
        # Récupération des données du formulaire
        numero_reference = request.form.get('numero_reference', '').strip()
        objet = request.form['objet'].strip()
        expediteur = request.form['expediteur'].strip()
        
        if not objet or not expediteur:
            flash('L\'objet et l\'expéditeur sont obligatoires.', 'error')
            return render_template('register_mail.html')
        
        # Génération du numéro d'accusé de réception
        numero_accuse = generate_accuse_reception()
        
        # Gestion du fichier uploadé
        file = request.files.get('fichier')
        fichier_nom = None
        fichier_chemin = None
        fichier_type = None
        
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Ajouter timestamp pour éviter les conflits
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                fichier_chemin = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(fichier_chemin)
                fichier_nom = file.filename
                fichier_type = filename.rsplit('.', 1)[1].lower()
            else:
                flash('Type de fichier non autorisé. Utilisez PDF, JPG, PNG ou TIFF.', 'error')
                return render_template('register_mail.html')
        
        # Création du courrier
        courrier = Courrier(
            numero_accuse_reception=numero_accuse,
            numero_reference=numero_reference if numero_reference else None,
            objet=objet,
            expediteur=expediteur,
            fichier_nom=fichier_nom,
            fichier_chemin=fichier_chemin,
            fichier_type=fichier_type,
            utilisateur_id=current_user.id
        )
        
        try:
            db.session.add(courrier)
            db.session.commit()
            
            # Log de l'activité
            log_activity(current_user.id, "ENREGISTREMENT_COURRIER", 
                        f"Enregistrement du courrier {numero_accuse}", courrier.id)
            
            flash(f'Courrier enregistré avec succès! N° d\'accusé: {numero_accuse}', 'success')
            return redirect(url_for('mail_detail', id=courrier.id))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de l'enregistrement: {e}")
            flash('Erreur lors de l\'enregistrement du courrier.', 'error')
    
    return render_template('register_mail.html')

@app.route('/view_mail')
@login_required
def view_mail():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filtres
    search = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    sort_by = request.args.get('sort_by', 'date_enregistrement')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Construction de la requête
    query = Courrier.query
    
    # Recherche textuelle
    if search:
        query = query.filter(
            or_(
                Courrier.numero_accuse_reception.contains(search),
                Courrier.numero_reference.contains(search),
                Courrier.objet.contains(search),
                Courrier.expediteur.contains(search)
            )
        )
    
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
    
    # Tri
    if sort_by in ['date_enregistrement', 'numero_accuse_reception', 'expediteur', 'objet']:
        order_column = getattr(Courrier, sort_by)
        if sort_order == 'desc':
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())
    
    # Pagination
    courriers = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('view_mail.html', 
                         courriers=courriers,
                         search=search,
                         date_from=date_from,
                         date_to=date_to,
                         sort_by=sort_by,
                         sort_order=sort_order)

@app.route('/search')
@login_required
def search():
    return render_template('search.html')

@app.route('/mail/<int:id>')
@login_required
def mail_detail(id):
    courrier = Courrier.query.get_or_404(id)
    log_activity(current_user.id, "CONSULTATION_COURRIER", 
                f"Consultation du courrier {courrier.numero_accuse_reception}", courrier.id)
    return render_template('mail_detail.html', courrier=courrier)

@app.route('/export_pdf/<int:id>')
@login_required
def export_pdf(id):
    courrier = Courrier.query.get_or_404(id)
    try:
        pdf_path = export_courrier_pdf(courrier)
        log_activity(current_user.id, "EXPORT_PDF", 
                    f"Export PDF du courrier {courrier.numero_accuse_reception}", courrier.id)
        return send_file(pdf_path, as_attachment=True, 
                        download_name=f"courrier_{courrier.numero_accuse_reception}.pdf")
    except Exception as e:
        logging.error(f"Erreur lors de l'export PDF: {e}")
        flash('Erreur lors de l\'export PDF.', 'error')
        return redirect(url_for('mail_detail', id=id))

@app.route('/download_file/<int:id>')
@login_required
def download_file(id):
    courrier = Courrier.query.get_or_404(id)
    if courrier.fichier_chemin and os.path.exists(courrier.fichier_chemin):
        log_activity(current_user.id, "TELECHARGEMENT_FICHIER", 
                    f"Téléchargement du fichier du courrier {courrier.numero_accuse_reception}", courrier.id)
        return send_file(courrier.fichier_chemin, as_attachment=True, 
                        download_name=courrier.fichier_nom)
    else:
        flash('Fichier non trouvé.', 'error')
        return redirect(url_for('mail_detail', id=id))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    parametres = ParametresSysteme.get_parametres()
    
    if request.method == 'POST':
        # Mise à jour des paramètres
        parametres.nom_logiciel = request.form['nom_logiciel']
        parametres.format_numero_accuse = request.form['format_numero_accuse']
        parametres.telephone = request.form.get('telephone', '').strip() or None
        parametres.email_contact = request.form.get('email_contact', '').strip() or None
        parametres.adresse_organisme = request.form.get('adresse_organisme', '').strip() or None
        parametres.modifie_par_id = current_user.id
        
        # Gestion du logo
        if 'logo' in request.files:
            logo = request.files['logo']
            if logo and logo.filename and allowed_file(logo.filename):
                filename = secure_filename(logo.filename)
                # Créer un nom unique pour le logo
                logo_filename = f"logo_{uuid.uuid4().hex[:8]}_{filename}"
                logo_path = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), logo_filename)
                
                try:
                    logo.save(logo_path)
                    parametres.logo_url = f'/uploads/{logo_filename}'
                    flash('Logo téléchargé avec succès!', 'success')
                except Exception as e:
                    flash(f'Erreur lors du téléchargement du logo: {str(e)}', 'error')
        
        try:
            db.session.commit()
            log_activity(current_user.id, "MODIFICATION_PARAMETRES", 
                        f"Mise à jour des paramètres système par {current_user.username}")
            flash('Paramètres sauvegardés avec succès!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la sauvegarde: {str(e)}', 'error')
        
        return redirect(url_for('settings'))
    
    # Générer un aperçu du format
    format_preview = generate_format_preview(parametres.format_numero_accuse)
    
    return render_template('settings.html', 
                          parametres=parametres,
                          format_preview=format_preview)

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

@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('base.html'), 500
