import os
import uuid
from datetime import datetime
from flask import request
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from app import db
from models import LogActivite

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif'}

def allowed_file(filename):
    """Vérifier si l'extension du fichier est autorisée"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_accuse_reception():
    """Générer un numéro d'accusé de réception unique"""
    year = datetime.now().year
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"GEC-{year}-{timestamp}-{unique_id}"

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
    
    # Titre du document
    title = Paragraph("SECRÉTARIAT GÉNÉRAL DES MINES<br/>République Démocratique du Congo", title_style)
    story.append(title)
    story.append(Spacer(1, 20))
    
    # Sous-titre
    subtitle = Paragraph("ACCUSÉ DE RÉCEPTION - COURRIER ENTRANT", styles['Heading2'])
    story.append(subtitle)
    story.append(Spacer(1, 20))
    
    # Tableau des métadonnées
    data = [
        ['N° d\'Accusé de Réception:', courrier.numero_accuse_reception],
        ['N° de Référence:', courrier.reference_display],
        ['Objet:', courrier.objet],
        ['Expéditeur:', courrier.expediteur],
        ['Date d\'Enregistrement:', courrier.date_enregistrement.strftime('%d/%m/%Y à %H:%M')],
        ['Enregistré par:', courrier.utilisateur_enregistrement.nom_complet],
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
    
    # Note de bas de page
    footer_text = f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} par le système GEC"
    footer = Paragraph(footer_text, styles['Normal'])
    story.append(footer)
    
    # Construire le PDF
    doc.build(story)
    
    return pdf_path
