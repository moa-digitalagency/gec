import os
import uuid
import json
from datetime import datetime
from flask import request, session
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from app import db
from models import LogActivite

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif'}

# Languages disponibles
AVAILABLE_LANGUAGES = {
    'fr': {'name': 'Français', 'flag': '🇫🇷'},
    'en': {'name': 'English', 'flag': '🇺🇸'}
}

def get_available_languages():
    """Retourne la liste des langues disponibles"""
    languages = {}
    lang_dir = os.path.join(os.path.dirname(__file__), 'lang')
    
    if os.path.exists(lang_dir):
        for filename in os.listdir(lang_dir):
            if filename.endswith('.json'):
                lang_code = filename[:-5]  # Remove .json
                if lang_code in AVAILABLE_LANGUAGES:
                    languages[lang_code] = AVAILABLE_LANGUAGES[lang_code]
    
    return languages

def get_current_language():
    """Obtient la langue actuelle depuis la session ou les préférences utilisateur"""
    if 'language' in session:
        return session['language']
    return 'fr'

def set_language(lang_code):
    """Définit la langue dans la session"""
    if lang_code in get_available_languages():
        session['language'] = lang_code
        return True
    return False

def load_translations(lang_code='fr'):
    """Charge les traductions pour une langue donnée"""
    lang_dir = os.path.join(os.path.dirname(__file__), 'lang')
    lang_file = os.path.join(lang_dir, f'{lang_code}.json')
    
    if not os.path.exists(lang_file):
        lang_file = os.path.join(lang_dir, 'fr.json')
    
    try:
        with open(lang_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def t(key, lang_code=None, **kwargs):
    """Fonction de traduction"""
    if lang_code is None:
        lang_code = get_current_language()
    
    translations = load_translations(lang_code)
    
    keys = key.split('.')
    value = translations
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return key
    
    if kwargs and isinstance(value, str):
        try:
            return value.format(**kwargs)
        except (KeyError, ValueError):
            return value
    
    return value

def allowed_file(filename):
    """Vérifier si l'extension du fichier est autorisée"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_accuse_reception():
    """Générer un numéro d'accusé de réception unique selon le format configuré"""
    import re
    
    # Import dynamique pour éviter les dépendances circulaires
    from models import ParametresSysteme, Courrier
    
    # Récupérer le format configuré
    try:
        parametres = ParametresSysteme.get_parametres()
        format_string = parametres.format_numero_accuse
    except:
        # Fallback si les paramètres ne sont pas disponibles
        format_string = "GEC-{year}-{counter:05d}"
    
    now = datetime.now()
    
    # Remplacer les variables de base
    numero = format_string.replace('{year}', str(now.year))
    numero = numero.replace('{month}', f"{now.month:02d}")
    numero = numero.replace('{day}', f"{now.day:02d}")
    
    # Calculer le compteur pour l'année en cours
    try:
        count = Courrier.query.filter(
            Courrier.date_enregistrement >= datetime(now.year, 1, 1)
        ).count() + 1
    except:
        count = 1
    
    # Traiter les compteurs avec format
    counter_pattern = r'\{counter:(\d+)d\}'
    matches = re.findall(counter_pattern, numero)
    for match in matches:
        width = int(match)
        formatted_counter = f"{count:0{width}d}"
        numero = re.sub(r'\{counter:\d+d\}', formatted_counter, numero, count=1)
    
    # Compteur simple
    numero = numero.replace('{counter}', str(count))
    
    # Nombre aléatoire
    import random
    random_pattern = r'\{random:(\d+)\}'
    matches = re.findall(random_pattern, numero)
    for match in matches:
        width = int(match)
        random_num = random.randint(10**(width-1), 10**width-1)
        numero = re.sub(r'\{random:\d+\}', str(random_num), numero, count=1)
    
    return numero

def log_activity(user_id, action, description, courrier_id=None):
    """Enregistrer une activité dans les logs"""
    try:
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
        
        log = LogActivite(
            utilisateur_id=user_id,
            action=action,
            description=description,
            courrier_id=courrier_id,
            ip_address=ip_address
        )
        
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de l'enregistrement du log: {e}")

def export_courrier_pdf(courrier):
    """Exporter un courrier en PDF avec ses métadonnées"""
    # Créer le dossier exports s'il n'existe pas
    exports_dir = 'exports'
    os.makedirs(exports_dir, exist_ok=True)
    
    # Nom du fichier PDF
    filename = f"courrier_{courrier.numero_accuse_reception}.pdf"
    pdf_path = os.path.join(exports_dir, filename)
    
    # Créer le document PDF
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1,  # Centré
        textColor=colors.darkblue
    )
    
    # Récupérer les paramètres système pour le PDF
    from models import ParametresSysteme
    parametres = ParametresSysteme.get_parametres()
    
    # Titre configuré du document
    titre_pdf = parametres.titre_pdf or "Ministère des Mines"
    sous_titre_pdf = parametres.sous_titre_pdf or "Secrétariat Général"
    
    title = Paragraph(f"{titre_pdf}<br/>{sous_titre_pdf}<br/>République Démocratique du Congo", title_style)
    story.append(title)
    story.append(Spacer(1, 20))
    
    # Sous-titre selon le type
    type_display = "COURRIER ENTRANT" if courrier.type_courrier == 'ENTRANT' else "COURRIER SORTANT"
    subtitle = Paragraph(f"ACCUSÉ DE RÉCEPTION - {type_display}", styles['Heading2'])
    story.append(subtitle)
    story.append(Spacer(1, 20))
    
    # Tableau des métadonnées - Dans le même ordre que la page de détail
    data = [
        ['N° d\'Accusé de Réception:', courrier.numero_accuse_reception],
        ['Type de Courrier:', courrier.type_courrier],
        ['N° de Référence:', courrier.numero_reference if courrier.numero_reference else 'Non référencé'],
        [courrier.get_label_contact() + ':', courrier.get_contact_principal() if courrier.get_contact_principal() else 'Non spécifié'],
        ['Objet:', courrier.objet],
        ['Date de Rédaction:', courrier.date_redaction.strftime('%d/%m/%Y') if courrier.date_redaction else 'Non renseignée'],
        ['Date d\'Enregistrement:', courrier.date_enregistrement.strftime('%d/%m/%Y à %H:%M')],
        ['Enregistré par:', courrier.utilisateur_enregistrement.nom_complet],
        ['Statut:', courrier.statut],
        ['Fichier Joint:', courrier.fichier_nom if courrier.fichier_nom else 'Aucun'],
    ]
    
    table = Table(data, colWidths=[2.5*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    story.append(Spacer(1, 30))
    
    # Note de bas de page avec texte configurable
    footer_lines = []
    
    # Texte footer configurable
    if parametres.texte_footer:
        footer_lines.append(parametres.texte_footer)
    
    # Date de génération
    footer_lines.append(f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} par le système GEC")
    
    # Copyright crypté
    copyright = parametres.get_copyright_decrypte()
    footer_lines.append(copyright)
    
    for line in footer_lines:
        footer = Paragraph(line, styles['Normal'])
        story.append(footer)
        story.append(Spacer(1, 6))
    
    # Construire le PDF
    doc.build(story)
    
    return pdf_path

def export_mail_list_pdf(courriers, filters):
    """Exporter une liste de courriers en PDF"""
    # Créer le dossier exports s'il n'existe pas
    exports_dir = 'exports'
    os.makedirs(exports_dir, exist_ok=True)
    
    # Nom du fichier PDF
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"liste_courriers_{timestamp}.pdf"
    pdf_path = os.path.join(exports_dir, filename)
    
    # Créer le document PDF en orientation paysage pour plus d'espace
    from reportlab.lib.pagesizes import landscape, A4
    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4), 
                          leftMargin=0.5*inch, rightMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Récupérer les paramètres système
    from models import ParametresSysteme
    parametres = ParametresSysteme.get_parametres()
    
    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=20,
        alignment=1,  # Centré
        textColor=colors.darkblue
    )
    
    # En-tête
    titre_pdf = parametres.titre_pdf or "Ministère des Mines"
    sous_titre_pdf = parametres.sous_titre_pdf or "Secrétariat Général"
    
    title = Paragraph(f"{titre_pdf}<br/>{sous_titre_pdf}<br/>République Démocratique du Congo", title_style)
    story.append(title)
    story.append(Spacer(1, 15))
    
    # Titre de la liste
    liste_title = Paragraph("LISTE DES COURRIERS", styles['Heading2'])
    story.append(liste_title)
    story.append(Spacer(1, 10))
    
    # Informations sur les filtres appliqués
    filter_info = []
    if filters['search']:
        filter_info.append(f"Recherche: {filters['search']}")
    if filters['type_courrier']:
        type_display = 'Entrant' if filters['type_courrier'] == 'ENTRANT' else 'Sortant'
        filter_info.append(f"Type: {type_display}")
    if filters['statut']:
        filter_info.append(f"Statut: {filters['statut']}")
    if filters['date_from'] or filters['date_to']:
        period = "Période Enr.: "
        if filters['date_from']:
            period += f"du {filters['date_from']}"
        if filters['date_to']:
            period += f" au {filters['date_to']}"
        filter_info.append(period)
    
    if filters.get('date_redaction_from') or filters.get('date_redaction_to'):
        period_red = "Période Réd.: "
        if filters.get('date_redaction_from'):
            period_red += f"du {filters['date_redaction_from']}"
        if filters.get('date_redaction_to'):
            period_red += f" au {filters['date_redaction_to']}"
        filter_info.append(period_red)
    
    if filter_info:
        filter_text = " | ".join(filter_info)
        filter_para = Paragraph(f"Filtres appliqués: {filter_text}", styles['Normal'])
        story.append(filter_para)
        story.append(Spacer(1, 10))
    
    # Informations sur le rapport
    count = len(courriers)
    date_generation = datetime.now().strftime('%d/%m/%Y à %H:%M')
    info_para = Paragraph(f"Total: {count} courrier{'s' if count > 1 else ''} | Généré le: {date_generation}", styles['Normal'])
    story.append(info_para)
    story.append(Spacer(1, 15))
    
    if not courriers:
        # Message si aucun courrier
        no_data = Paragraph("Aucun courrier trouvé avec les critères spécifiés.", styles['Normal'])
        story.append(no_data)
    else:
        # Créer le tableau des courriers
        headers = ['N° Accusé', 'Type', 'Référence', 'Contact', 'Objet', 'Date Réd.', 'Date Enr.', 'Statut', 'Fichier']
        data = [headers]
        
        for courrier in courriers:
            # Contact principal selon le type
            contact = courrier.expediteur if courrier.type_courrier == 'ENTRANT' else courrier.destinataire
            contact = contact[:20] + '...' if contact and len(contact) > 20 else contact or 'N/A'
            
            # Référence
            reference = courrier.numero_reference[:15] + '...' if courrier.numero_reference and len(courrier.numero_reference) > 15 else courrier.numero_reference or 'N/A'
            
            # Objet tronqué
            objet = courrier.objet[:30] + '...' if len(courrier.objet) > 30 else courrier.objet
            
            # Date de rédaction formatée
            date_redaction_str = courrier.date_redaction.strftime('%d/%m/%Y') if courrier.date_redaction else 'N/A'
            
            # Date d'enregistrement formatée
            date_enr_str = courrier.date_enregistrement.strftime('%d/%m/%Y')
            
            # Type court
            type_short = 'ENT' if courrier.type_courrier == 'ENTRANT' else 'SOR'
            
            # Statut formatté
            statut = courrier.statut.replace('_', ' ')[:8]
            
            # Fichier joint
            fichier = 'Oui' if courrier.fichier_nom else 'Non'
            
            row = [
                courrier.numero_accuse_reception,
                type_short,
                reference,
                contact,
                objet,
                date_redaction_str,
                date_enr_str,
                statut,
                fichier
            ]
            data.append(row)
        
        # Créer le tableau avec largeurs optimisées pour paysage
        col_widths = [1.0*inch, 0.4*inch, 0.8*inch, 1.4*inch, 2.0*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.4*inch]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        
        # Style du tableau
        table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            
            # Corps du tableau
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            
            # Bordures
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            
            # Alternance de couleur pour les lignes
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        story.append(table)
    
    story.append(Spacer(1, 20))
    
    # Pied de page
    footer_lines = []
    
    # Texte footer configurable
    if parametres.texte_footer:
        footer_lines.append(parametres.texte_footer)
    
    # Copyright crypté
    copyright = parametres.get_copyright_decrypte()
    footer_lines.append(copyright)
    
    for line in footer_lines:
        footer = Paragraph(line, styles['Normal'])
        story.append(footer)
        story.append(Spacer(1, 4))
    
    # Construire le PDF
    doc.build(story)
    
    return pdf_path
