import os
import uuid
import logging
from datetime import datetime
from flask import request, session
from utils.helpers import format_date
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable, KeepInFrame
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# --- Charte visuelle de l'accusé de réception (document officiel, sobre) ---------
GEC_NAVY   = colors.HexColor('#0F2A47')   # bleu nuit institutionnel (titres, bandeaux)
GEC_ACCENT = colors.HexColor('#B8912F')   # filet doré discret (liseré officiel)
GEC_LIGHT  = colors.HexColor('#F3F6FA')   # fond de ligne très clair (lisibilité)
GEC_BORDER = colors.HexColor('#D6DEE8')   # traits fins
GEC_MUTED  = colors.HexColor('#5B6675')   # texte secondaire


def _qr_flowable(texte, taille_mm=30.0):
    """QR code (encode le numéro d'accusé) en flowable ReportLab, net à l'impression."""
    import io
    import qrcode
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=1)
    qr.add_data(texte or '')
    qr.make(fit=True)
    image = qr.make_image(fill_color='black', back_color='white')
    tampon = io.BytesIO()
    image.save(tampon, format='PNG')
    tampon.seek(0)
    return Image(tampon, width=taille_mm * mm, height=taille_mm * mm)


def _resolve_logo_path(parametres):
    """Trouve le fichier logo sur disque quel que soit le format stocké
    ('/static/uploads/x', '/uploads/x' ou 'x'), en cherchant dans static/uploads puis uploads."""
    for stored in (getattr(parametres, 'logo_pdf', None), getattr(parametres, 'logo_url', None)):
        if not stored:
            continue
        basename = os.path.basename(stored.split('?')[0])
        for base in ('static/uploads', 'uploads'):
            candidate = os.path.join(base, basename)
            if os.path.exists(candidate):
                return candidate
    return None


def export_courrier_pdf(courrier):
    """Exporter un courrier en PDF avec ses métadonnées"""
    # Créer le dossier exports s'il n'existe pas
    exports_dir = 'exports'
    os.makedirs(exports_dir, exist_ok=True)
    
    # Nom du fichier PDF
    filename = f"courrier_{courrier.numero_accuse_reception}.pdf"
    pdf_path = os.path.join(exports_dir, filename)
    
    # Classe personnalisée pour les numéros de page
    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []
            
        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()
            
        def save(self):
            """Add page info to each page (page x of y)"""
            num_pages = len(self._saved_page_states)
            for (page_num, page_state) in enumerate(self._saved_page_states):
                self.__dict__.update(page_state)
                self.draw_page_number(page_num + 1, num_pages)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)
            
        def draw_page_number(self, page_num, total_pages):
            """Draw the footer with copyright and page number at the bottom on two lines"""
            from models import ParametresSysteme
            from flask_login import current_user
            parametres = ParametresSysteme.get_parametres()
            
            # Première ligne : Système et Copyright
            line1_parts = []
            if parametres.texte_footer:
                line1_parts.append(parametres.texte_footer)
            
            copyright = parametres.copyright_text or parametres.get_copyright_decrypte()
            line1_parts.append(copyright)
            
            line1_text = " | ".join(line1_parts)
            
            # Deuxième ligne : Date, utilisateur et pagination
            line2_parts = []
            
            # Date de génération
            now = datetime.now()
            date_str = now.strftime('%A %d %B %Y à %H:%M')
            # Traduire en français
            mois_fr = {
                'January': 'janvier', 'February': 'février', 'March': 'mars', 'April': 'avril',
                'May': 'mai', 'June': 'juin', 'July': 'juillet', 'August': 'août',
                'September': 'septembre', 'October': 'octobre', 'November': 'novembre', 'December': 'décembre'
            }
            jours_fr = {
                'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi', 'Thursday': 'Jeudi',
                'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'
            }
            for en, fr in mois_fr.items():
                date_str = date_str.replace(en, fr)
            for en, fr in jours_fr.items():
                date_str = date_str.replace(en, fr)
            
            # Essayer d'obtenir l'utilisateur actuel
            try:
                if current_user and current_user.is_authenticated:
                    user_info = f"par {current_user.nom_complet}"
                else:
                    user_info = "par le système GEC"
            except:
                user_info = "par le système GEC"
            
            line2_parts.append(f"Document généré le {date_str} {user_info}")
            line2_parts.append(f"Page {page_num} sur {total_pages}")
            
            line2_text = " | ".join(line2_parts)
            
            # Configuration du texte
            self.setFont("Helvetica", 8)
            page_width = A4[0]
            left_margin = 0.75*inch
            right_margin = 0.75*inch
            text_width = page_width - left_margin - right_margin
            
            # Dessiner la première ligne
            line1_width = self.stringWidth(line1_text, "Helvetica", 8)
            if line1_width <= text_width:
                x_position1 = (page_width - line1_width) / 2
            else:
                x_position1 = left_margin
            self.drawString(x_position1, 0.6*inch, line1_text)
            
            # Dessiner la deuxième ligne
            line2_width = self.stringWidth(line2_text, "Helvetica", 8)
            if line2_width <= text_width:
                x_position2 = (page_width - line2_width) / 2
            else:
                x_position2 = left_margin
            self.drawString(x_position2, 0.4*inch, line2_text)
    
    # Créer le document PDF avec la classe personnalisée
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, topMargin=1*inch, bottomMargin=1.2*inch, 
                          leftMargin=0.75*inch, rightMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Style personnalisé pour le titre (sections de la page 2)
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=13,
        spaceAfter=10,
        alignment=0,  # Aligné à gauche (titre de section)
        textColor=GEC_NAVY
    )
    
    # Style pour le texte avec wrap automatique
    text_style = ParagraphStyle(
        'CustomText',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=12,
        wordWrap='CJK',  # Permettre le wrap sur les mots longs
        splitLongWords=True,
        allowWidows=1,
        allowOrphans=1
    )
    
    # Style pour les labels
    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontSize=9.5,
        spaceAfter=0,
        textColor=GEC_NAVY,
        fontName='Helvetica-Bold',
        leading=12
    )
    
    # Récupérer les paramètres système pour le PDF
    from models import ParametresSysteme
    parametres = ParametresSysteme.get_parametres()
    
    # ====================================================================
    #  EN-TÊTE (letterhead) : identité à gauche, panneau QR à droite.
    #  Le QR encode le numéro d'accusé (vérification directe du document) ;
    #  il remplace l'ancienne étiquette qui vivait en page 2.
    # ====================================================================
    titre_pdf = parametres.titre_pdf or parametres.nom_logiciel or ""
    sous_titre_pdf = parametres.sous_titre_pdf or "Secrétariat Général"
    pays_text = parametres.pays_pdf or "République Démocratique du Congo"

    st_pays = ParagraphStyle('AR_Pays', parent=styles['Normal'], fontSize=12.5,
                             fontName='Helvetica-Bold', textColor=GEC_NAVY,
                             leading=15, spaceAfter=2)
    st_org = ParagraphStyle('AR_Org', parent=styles['Normal'], fontSize=10.5,
                            fontName='Helvetica-Bold', textColor=GEC_NAVY, leading=13)
    st_org_sub = ParagraphStyle('AR_OrgSub', parent=styles['Normal'], fontSize=9,
                                textColor=GEC_MUTED, leading=12)
    st_qr_lbl = ParagraphStyle('AR_QrLbl', parent=styles['Normal'], fontSize=6.5,
                               alignment=1, textColor=GEC_MUTED, leading=8,
                               spaceBefore=3, fontName='Helvetica-Bold')
    st_qr_num = ParagraphStyle('AR_QrNum', parent=styles['Normal'], fontSize=9,
                               alignment=1, textColor=GEC_NAVY, leading=11,
                               fontName='Helvetica-Bold')

    # Colonne identité (logo optionnel + pays + organisation)
    col_identite = []
    logo_path = _resolve_logo_path(parametres)
    if logo_path:
        try:
            from PIL import Image as PILImage
            with PILImage.open(logo_path) as pil_img:
                ow, oh = pil_img.size
            ratio = min((1.35 * inch) / ow, (0.78 * inch) / oh)
            logo = Image(logo_path, width=ow * ratio, height=oh * ratio)
            logo.hAlign = 'LEFT'
            col_identite.append(logo)
            col_identite.append(Spacer(1, 6))
        except Exception as e:
            logging.warning(f"Logo non chargé pour l'accusé : {e}")
    col_identite.append(Paragraph(pays_text, st_pays))
    if titre_pdf:
        col_identite.append(Paragraph(titre_pdf, st_org))
    if sous_titre_pdf:
        col_identite.append(Paragraph(sous_titre_pdf, st_org_sub))

    # Panneau QR (image + libellé + numéro), encadré discret
    col_qr = [Paragraph("Non spécifié", st_qr_num)]
    try:
        col_qr = [
            _qr_flowable(courrier.numero_accuse_reception, taille_mm=27.0),
            Paragraph("N° D'ACCUSÉ DE RÉCEPTION", st_qr_lbl),
            Paragraph(courrier.numero_accuse_reception or '-', st_qr_num),
        ]
    except Exception as e:
        logging.warning(f"QR non généré pour l'accusé : {e}")

    entete = Table([[col_identite, col_qr]], colWidths=[4.35 * inch, 2.25 * inch])
    entete.setStyle(TableStyle([
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ('VALIGN', (1, 0), (1, 0), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('BOX', (1, 0), (1, 0), 0.8, GEC_BORDER),
        ('TOPPADDING', (1, 0), (1, 0), 6),
        ('BOTTOMPADDING', (1, 0), (1, 0), 6),
        ('LEFTPADDING', (1, 0), (1, 0), 6),
        ('RIGHTPADDING', (1, 0), (1, 0), 6),
    ]))
    story.append(entete)
    story.append(Spacer(1, 8))
    # Double filet officiel : trait navy épais + liseré doré fin
    story.append(HRFlowable(width='100%', thickness=1.4, color=GEC_NAVY, spaceAfter=1.5))
    story.append(HRFlowable(width='100%', thickness=0.8, color=GEC_ACCENT, spaceAfter=14))

    # Bandeau titre du document
    type_display = "COURRIER ENTRANT" if courrier.type_courrier == 'ENTRANT' else "COURRIER SORTANT"
    st_doc_title = ParagraphStyle('AR_DocTitle', parent=styles['Normal'], fontSize=15,
                                  fontName='Helvetica-Bold', textColor=colors.white,
                                  alignment=1, leading=19)
    st_doc_sub = ParagraphStyle('AR_DocSub', parent=styles['Normal'], fontSize=8.5,
                                textColor=colors.white, alignment=1, leading=11,
                                spaceBefore=1)
    bandeau = Table([[Paragraph("ACCUSÉ DE RÉCEPTION", st_doc_title)],
                     [Paragraph(type_display, st_doc_sub)]], colWidths=[6.6 * inch])
    bandeau.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GEC_NAVY),
        ('TOPPADDING', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 1),
        ('TOPPADDING', (0, 1), (-1, 1), 0),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 9),
        ('LINEBELOW', (0, 1), (-1, 1), 2.5, GEC_ACCENT),
    ]))
    story.append(bandeau)
    story.append(Spacer(1, 16))
    
    # Tableau des métadonnées avec text wrapping pour les champs longs
    data = [
        [Paragraph('N° d\'Accusé de Réception:', label_style), Paragraph(courrier.numero_accuse_reception, text_style)],
        [Paragraph('Type de Courrier:', label_style), Paragraph(courrier.type_courrier, text_style)],
        [Paragraph('N° de Référence:', label_style), Paragraph(courrier.numero_reference if courrier.numero_reference else 'Non référencé', text_style)],
        [Paragraph(courrier.get_label_contact() + ':', label_style), Paragraph(courrier.get_contact_principal() if courrier.get_contact_principal() else 'Non spécifié', text_style)],
    ]
    
    # Ajouter le champ SG en copie seulement pour les courriers entrants
    if courrier.type_courrier == 'ENTRANT' and hasattr(courrier, 'secretaire_general_copie'):
        sg_copie_text = 'Oui' if courrier.secretaire_general_copie else 'Non'
        if courrier.secretaire_general_copie is None:
            sg_copie_text = 'Non renseigné'
        data.append([Paragraph('En copie:', label_style), Paragraph(sg_copie_text, text_style)])
    
    # Utiliser le bon label selon le type de courrier
    date_label = "Date d'Émission:" if courrier.type_courrier == 'SORTANT' else "Date de Rédaction:"
    
    data.extend([
        [Paragraph('Objet:', label_style), Paragraph(courrier.objet, text_style)],
        [Paragraph(date_label, label_style), Paragraph(format_date(courrier.date_redaction), text_style)],
        [Paragraph('Date d\'Enregistrement:', label_style), Paragraph(format_date(courrier.date_enregistrement, include_time=True), text_style)],
        [Paragraph('Enregistré par:', label_style), Paragraph(courrier.utilisateur_enregistrement.nom_complet, text_style)],
        [Paragraph('Statut:', label_style), Paragraph(courrier.statut, text_style)],
        [Paragraph('Fichier Joint:', label_style), Paragraph(courrier.fichier_nom if courrier.fichier_nom else 'Aucun', text_style)],
    ])
    
    st_section = ParagraphStyle('AR_Section', parent=styles['Normal'], fontSize=8,
                                fontName='Helvetica-Bold', textColor=GEC_MUTED,
                                leading=11)
    story.append(Paragraph("INFORMATIONS DU COURRIER", st_section))
    story.append(Spacer(1, 5))

    table = Table(data, colWidths=[2.25*inch, 4.35*inch], repeatRows=0)
    table.setStyle(TableStyle([
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1A2430')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (0, -1), 10),
        ('LEFTPADDING', (1, 0), (1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        # Colonne libellés teintée, colonne valeurs blanche, lignes alternées
        ('BACKGROUND', (0, 0), (0, -1), GEC_LIGHT),
        ('ROWBACKGROUNDS', (1, 0), (1, -1), [colors.white, colors.HexColor('#FBFCFD')]),
        # Traits fins horizontaux + cadre léger, aucun grillage noir
        ('LINEBELOW', (0, 0), (-1, -2), 0.4, GEC_BORDER),
        ('LINEAFTER', (0, 0), (0, -1), 0.4, GEC_BORDER),
        ('BOX', (0, 0), (-1, -1), 0.8, GEC_BORDER),
        ('WORDWRAP', (1, 0), (1, -1), 'CJK'),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 10))

    # Mention de vérification (reliée au QR de l'en-tête)
    st_verif = ParagraphStyle('AR_Verif', parent=styles['Normal'], fontSize=8,
                              textColor=GEC_MUTED, leading=11, alignment=0)
    story.append(Paragraph(
        "Ce document peut être vérifié en scannant le QR code de l'en-tête. "
        "Le numéro d'accusé de réception en est la référence unique.", st_verif))
    story.append(Spacer(1, 18))

    
    # L'étiquette séparée (ancienne page 2) est supprimée : le QR code figure
    # désormais dans l'en-tête de la page 1, directement sur l'accusé.

    # Le footer est maintenant géré automatiquement par la classe NumberedCanvas
    # sur chaque page, donc on n'ajoute plus rien ici
    
    # Construire le PDF avec numérotation des pages
    doc.build(story, canvasmaker=NumberedCanvas)
    
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
    
    # Ajouter le logo s'il existe
    logo_path = None
    if parametres.logo_pdf:
        # Convertir l'URL relative en chemin de fichier absolu
        if parametres.logo_pdf.startswith('/uploads/'):
            logo_file_path = parametres.logo_pdf[9:]  # Enlever '/uploads/'
            logo_abs_path = os.path.join('uploads', logo_file_path)
            if os.path.exists(logo_abs_path):
                logo_path = logo_abs_path
    elif parametres.logo_url:
        # Convertir l'URL relative en chemin de fichier absolu
        if parametres.logo_url.startswith('/uploads/'):
            logo_file_path = parametres.logo_url[9:]  # Enlever '/uploads/'
            logo_abs_path = os.path.join('uploads', logo_file_path)
            if os.path.exists(logo_abs_path):
                logo_path = logo_abs_path
    
    logo_path = _resolve_logo_path(parametres)
    if logo_path:
        try:
            # Charger l'image pour obtenir ses dimensions originales
            from PIL import Image as PILImage
            pil_img = PILImage.open(logo_path)
            original_width, original_height = pil_img.size
            
            # Calculer les dimensions en préservant le ratio (plus petit pour liste)
            max_width = 1.2*inch
            max_height = 0.8*inch
            
            # Calculer le ratio de redimensionnement
            width_ratio = max_width / original_width
            height_ratio = max_height / original_height
            ratio = min(width_ratio, height_ratio)
            
            # Nouvelles dimensions préservant le ratio
            new_width = original_width * ratio
            new_height = original_height * ratio
            
            logo = Image(logo_path, width=new_width, height=new_height)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 8))
        except Exception as e:
            print(f"Erreur chargement logo: {e}")  # Pour debug
    
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
    titre_pdf = parametres.titre_pdf or parametres.nom_logiciel or ""
    sous_titre_pdf = parametres.sous_titre_pdf or "Secrétariat Général"
    
    # En-tête pays - PREMIER ÉLÉMENT
    pays_style = ParagraphStyle(
        'PaysStyle',
        parent=styles['Normal'],
        fontSize=16,
        fontName='Helvetica-Bold',
        alignment=1,  # Center
        spaceAfter=10,
        textColor=colors.darkblue
    )
    pays_text = parametres.pays_pdf or "République Démocratique du Congo"
    story.append(Paragraph(pays_text, pays_style))
    
    title = Paragraph(f"{titre_pdf}<br/>{sous_titre_pdf}", title_style)
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
    date_generation = format_date(datetime.now(), include_time=True)
    info_para = Paragraph(f"Total: {count} courrier{'s' if count > 1 else ''} | Généré le: {date_generation}", styles['Normal'])
    story.append(info_para)
    story.append(Spacer(1, 15))
    
    if not courriers:
        # Message si aucun courrier
        no_data = Paragraph("Aucun courrier trouvé avec les critères spécifiés.", styles['Normal'])
        story.append(no_data)
    else:
        # Style pour le texte dans les cellules avec wrapping
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            alignment=0,  # Left alignment
            leftIndent=2,
            rightIndent=2,
            spaceAfter=2
        )
        
        # Style pour les en-têtes
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            alignment=0,  # Left alignment
            textColor=colors.whitesmoke,
            leftIndent=2,
            rightIndent=2
        )
        
        # Déterminer si on a des courriers sortants pour ajuster le label de date
        has_sortant = any(c.type_courrier == 'SORTANT' for c in courriers)
        has_entrant = any(c.type_courrier == 'ENTRANT' for c in courriers)
        
        # Choisir le label approprié
        if has_sortant and not has_entrant:
            date_header = 'Date d\'Émission'
        elif has_entrant and not has_sortant:
            date_header = 'Date de Rédaction'
        else:
            # Mix des deux types
            date_header = 'Date Réd./Émission'
        
        # Créer le tableau des courriers avec le nouveau champ Observation
        headers = [
            Paragraph('N° Accusé de Réception', header_style),
            Paragraph('Type', header_style),
            Paragraph('N° de Référence', header_style),
            Paragraph('Contact Principal', header_style),
            Paragraph('Objet', header_style),
            Paragraph(date_header, header_style),
            Paragraph('Date d\'Enregistrement', header_style),
            Paragraph('Statut', header_style),
            Paragraph('En Copie', header_style),
            Paragraph('Observation', header_style)
        ]
        data = [headers]
        
        for courrier in courriers:
            # Contact principal selon le type - texte complet avec wrapping
            contact = courrier.expediteur if courrier.type_courrier == 'ENTRANT' else courrier.destinataire
            contact_text = contact if contact else 'Non spécifié'
            
            # Référence - texte complet avec wrapping
            reference_text = courrier.numero_reference if courrier.numero_reference else 'Non référencé'
            
            # Objet - texte complet avec wrapping
            objet_text = courrier.objet
            
            # Date de rédaction/émission formatée
            date_redaction_str = format_date(courrier.date_redaction)
            
            # Date d'enregistrement formatée
            date_enr_str = format_date(courrier.date_enregistrement, include_time=True).replace(' à ', '<br/>')
            
            # Type complet
            type_text = 'Courrier Entrant' if courrier.type_courrier == 'ENTRANT' else 'Courrier Sortant'
            
            # Statut formatté
            statut_text = courrier.statut.replace('_', ' ')
            
            # SG en copie (pour courriers entrants)
            sg_copie_text = '-'
            if courrier.type_courrier == 'ENTRANT' and hasattr(courrier, 'secretaire_general_copie'):
                if courrier.secretaire_general_copie is not None:
                    sg_copie_text = 'Oui' if courrier.secretaire_general_copie else 'Non'
            
            # Observation - champ vide pour remplissage manuel
            observation_text = ''
            
            row = [
                Paragraph(courrier.numero_accuse_reception, cell_style),
                Paragraph(type_text, cell_style),
                Paragraph(reference_text, cell_style),
                Paragraph(contact_text, cell_style),
                Paragraph(objet_text, cell_style),
                Paragraph(date_redaction_str, cell_style),
                Paragraph(date_enr_str, cell_style),
                Paragraph(statut_text, cell_style),
                Paragraph(sg_copie_text, cell_style),
                Paragraph(observation_text, cell_style)
            ]
            data.append(row)
        
        # Créer le tableau avec largeurs optimisées pour paysage A4 (11.69 x 8.27 inches utilisables)
        # Total width disponible: environ 10.69 inches (en retirant les marges)
        col_widths = [
            1.1*inch,   # N° Accusé de Réception
            0.8*inch,   # Type  
            1.0*inch,   # N° de Référence
            1.5*inch,   # Contact Principal
            2.5*inch,   # Objet (plus large pour le texte long)
            0.8*inch,   # Date de Rédaction/Émission
            0.9*inch,   # Date d'Enregistrement
            0.8*inch,   # Statut
            0.6*inch,   # SG Copie
            1.4*inch    # Observation (plus d'espace)
        ]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        
        # Style du tableau amélioré pour une meilleure lisibilité
        table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Alignement vertical en haut
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            
            # Corps du tableau avec plus d'espace pour le texte
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('ROWSIZE', (0, 1), (-1, -1), 'auto'),  # Hauteur automatique pour accommoder le texte
            
            # Bordures plus épaisses pour la lisibilité
            ('GRID', (0, 0), (-1, -1), 0.8, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.darkblue),  # Ligne plus épaisse sous l'en-tête
            
            # Alternance de couleur pour les lignes
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            
            # Style spécial pour la colonne Observation (dernière colonne)
            ('BACKGROUND', (-1, 1), (-1, -1), colors.lightyellow),  # Fond jaune clair pour Observation
            
            # Espacement entre les mots et retour à la ligne automatique
            ('WORDWRAP', (0, 0), (-1, -1), 'CJK'),
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

def send_comment_notification(email, courrier_data):
    """Envoyer un email de notification pour les commentaires/annotations/instructions"""
    try:
        # Charger les paramètres système pour l'email
        from models import ParametresSysteme
        parametres = ParametresSysteme.get_parametres()
        if not parametres:
            logging.error("Impossible de charger les paramètres système pour l'email")
            return False
        
        # Textes selon le type de commentaire
        type_labels = {
            'comment': 'Commentaire',
            'annotation': 'Annotation', 
            'instruction': 'Instruction'
        }
        type_label = type_labels.get(courrier_data['comment_type'], 'Commentaire')
        
        subject = f"Nouveau {type_label} - {courrier_data['numero_accuse_reception']}"
        
        # Template HTML pour l'email
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background-color: #003087; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .details {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        .comment {{ background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 10px 0; }}
        .footer {{ background-color: #f1f1f1; padding: 10px; text-align: center; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>GEC - Nouveau {type_label}</h2>
    </div>
    <div class="content">
        <p>Bonjour,</p>
        <p>Un nouveau {type_label.lower()} a été ajouté sur un courrier dans le système GEC.</p>
        
        <div class="details">
            <h3>Détails du courrier :</h3>
            <p><strong>Numéro d'accusé de réception :</strong> {courrier_data['numero_accuse_reception']}</p>
            <p><strong>Type :</strong> {courrier_data['type_courrier']}</p>
            <p><strong>Objet :</strong> {courrier_data['objet']}</p>
            <p><strong>Contact :</strong> {courrier_data['expediteur']}</p>
            <p><strong>{type_label} ajouté par :</strong> {courrier_data['added_by']}</p>
        </div>
        
        <div class="comment">
            <h3>{type_label} :</h3>
            <p>{courrier_data['comment_text']}</p>
        </div>
        
        <p>Vous pouvez consulter ce courrier et répondre en vous connectant au système GEC.</p>
    </div>
    <div class="footer">
        <p>GEC - Système de Gestion du Courrier<br>
        Secrétariat Général - République Démocratique du Congo</p>
    </div>
</body>
</html>
        """
        
        # Envoyer l'email
        from services.email import send_email_from_system_config
        return send_email_from_system_config(email, subject, html_content)
        
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi de la notification de commentaire: {e}")
        return False

def export_logs_pdf(logs, filters):
    """Exporter les logs d'activité en PDF avec mise en forme professionnelle"""
    # Créer le dossier exports s'il n'existe pas
    exports_dir = 'exports'
    os.makedirs(exports_dir, exist_ok=True)
    
    # Nom du fichier PDF
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"logs_activite_{timestamp}.pdf"
    pdf_path = os.path.join(exports_dir, filename)
    
    # Créer le document PDF en orientation paysage pour plus d'espace
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import Image
    from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
    from reportlab.platypus.frames import Frame
    from reportlab.pdfgen import canvas
    
    # Classe pour numérotation des pages et en-têtes/pieds de page
    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []
            
        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()
            
        def save(self):
            """Ajouter les en-têtes et pieds de page sur toutes les pages"""
            num_pages = len(self._saved_page_states)
            for (page_num, page_state) in enumerate(self._saved_page_states):
                self.__dict__.update(page_state)
                self.draw_page_elements(page_num + 1, num_pages)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)
            
        def draw_page_elements(self, page_num, total_pages):
            """Dessiner les éléments sur chaque page"""
            from flask_login import current_user
            
            # En-tête
            self.setFont('Helvetica-Bold', 10)
            # Nom utilisateur en haut à gauche
            if current_user and current_user.is_authenticated:
                self.drawString(0.5*inch, landscape(A4)[1] - 0.3*inch, 
                              f"Utilisateur: {current_user.nom_complet}")
            
            # Date et heure en haut à droite
            self.drawRightString(landscape(A4)[0] - 0.5*inch, landscape(A4)[1] - 0.3*inch,
                               f"Date d'export: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            # Pied de page
            self.setFont('Helvetica', 8)
            # Numérotation des pages au centre
            self.drawString(landscape(A4)[0]/2 - 30, 0.3*inch, 
                           f"Page {page_num} sur {total_pages}")
            
            # Copyright en bas à droite
            from models import ParametresSysteme
            parametres = ParametresSysteme.get_parametres()
            copyright = parametres.get_copyright_decrypte() if parametres else "© GEC System"
            self.drawRightString(landscape(A4)[0] - 0.5*inch, 0.3*inch, copyright)
    
    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4), 
                          leftMargin=0.5*inch, rightMargin=0.5*inch,
                          topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Récupérer les paramètres système
    from models import ParametresSysteme
    parametres = ParametresSysteme.get_parametres()
    
    # Ajouter le logo s'il existe
    logo_path = None
    if parametres.logo_pdf:
        if parametres.logo_pdf.startswith('/uploads/'):
            logo_file_path = parametres.logo_pdf[9:]
            logo_abs_path = os.path.join('uploads', logo_file_path)
            if os.path.exists(logo_abs_path):
                logo_path = logo_abs_path
    elif parametres.logo_url:
        if parametres.logo_url.startswith('/uploads/'):
            logo_file_path = parametres.logo_url[9:]
            logo_abs_path = os.path.join('uploads', logo_file_path)
            if os.path.exists(logo_abs_path):
                logo_path = logo_abs_path
    
    logo_path = _resolve_logo_path(parametres)
    if logo_path:
        try:
            from PIL import Image as PILImage
            pil_img = PILImage.open(logo_path)
            original_width, original_height = pil_img.size
            
            # Calculer les dimensions en préservant le ratio
            max_width = 1.5*inch
            max_height = 1.0*inch
            
            width_ratio = max_width / original_width
            height_ratio = max_height / original_height
            ratio = min(width_ratio, height_ratio)
            
            new_width = original_width * ratio
            new_height = original_height * ratio
            
            logo = Image(logo_path, width=new_width, height=new_height)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 10))
        except Exception as e:
            print(f"Erreur chargement logo: {e}")
    
    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=20,
        alignment=1,  # Centré
        textColor=colors.darkblue,
        fontName='Helvetica-Bold'
    )
    
    # En-tête pays
    pays_style = ParagraphStyle(
        'PaysStyle',
        parent=styles['Normal'],
        fontSize=18,
        fontName='Helvetica-Bold',
        alignment=1,
        spaceAfter=10,
        textColor=colors.darkblue
    )
    pays_text = parametres.pays_pdf or "République Démocratique du Congo"
    story.append(Paragraph(pays_text, pays_style))
    
    # Titre et sous-titre
    titre_pdf = parametres.titre_pdf or parametres.nom_logiciel or ""
    sous_titre_pdf = parametres.sous_titre_pdf or "Secrétariat Général"
    
    title = Paragraph(f"{titre_pdf}<br/>{sous_titre_pdf}", title_style)
    story.append(title)
    story.append(Spacer(1, 20))
    
    # Titre du rapport
    rapport_title = Paragraph("JOURNAL DES ACTIVITÉS SYSTÈME", styles['Heading2'])
    story.append(rapport_title)
    story.append(Spacer(1, 15))
    
    # Informations sur les filtres appliqués
    filter_info = []
    if filters.get('search'):
        filter_info.append(f"Recherche textuelle: {filters['search']}")
    if filters.get('action_filter'):
        filter_info.append(f"Action filtrée: {filters['action_filter']}")
    if filters.get('user_filter'):
        from models import User
        user = User.query.get(filters['user_filter'])
        if user:
            filter_info.append(f"Utilisateur: {user.nom_complet}")
    if filters.get('date_from') or filters.get('date_to'):
        period = "Période: "
        if filters.get('date_from'):
            period += f"du {filters['date_from']}"
        if filters.get('date_to'):
            period += f" au {filters['date_to']}"
        filter_info.append(period)
    
    if filter_info:
        filter_style = ParagraphStyle(
            'FilterStyle',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=15,
            textColor=colors.grey
        )
        filter_text = " | ".join(filter_info)
        story.append(Paragraph(f"<b>Filtres appliqués:</b> {filter_text}", filter_style))
    
    # Statistiques rapides
    total_logs = len(logs)
    actions_uniques = len(set(log.action for log in logs))
    utilisateurs_uniques = len(set(log.utilisateur_id for log in logs))
    
    stats_style = ParagraphStyle(
        'StatsStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=15,
        textColor=colors.darkgreen
    )
    stats_text = f"<b>Statistiques:</b> {total_logs} entrées | {actions_uniques} types d'actions | {utilisateurs_uniques} utilisateurs actifs"
    story.append(Paragraph(stats_text, stats_style))
    story.append(Spacer(1, 10))
    
    # Construire le tableau des logs
    if logs:
        # En-têtes du tableau
        headers = [
            'Date/Heure',
            'Utilisateur', 
            'Action',
            'Description',
            'IP',
            'Courrier'
        ]
        
        # Données du tableau
        data = [headers]
        
        for log in logs:
            # Formatage de la date
            date_str = log.date_action.strftime('%d/%m/%Y\n%H:%M:%S') if log.date_action else ''
            
            # Nom utilisateur
            user_name = log.utilisateur.nom_complet if log.utilisateur else 'Inconnu'
            
            # Action
            action = log.action or ''
            
            # Description (limitée et avec retour à la ligne)
            description = log.description or ''
            if len(description) > 80:
                description = description[:77] + '...'
            
            # IP
            ip = log.ip_address or ''
            
            # Courrier (si applicable)
            courrier_info = ''
            if log.courrier_id and log.courrier:
                courrier_info = f"#{log.courrier.numero_accuse_reception}"
            
            row = [
                Paragraph(date_str, styles['Normal']),
                Paragraph(user_name, styles['Normal']),
                Paragraph(action, styles['Normal']),
                Paragraph(description, styles['Normal']),
                Paragraph(ip, styles['Normal']),
                Paragraph(courrier_info, styles['Normal'])
            ]
            data.append(row)
        
        # Largeurs des colonnes optimisées pour paysage
        col_widths = [
            1.2*inch,   # Date/Heure
            1.4*inch,   # Utilisateur
            1.3*inch,   # Action
            3.5*inch,   # Description (plus large)
            1.0*inch,   # IP
            1.0*inch    # Courrier
        ]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        
        # Style du tableau professionnel
        table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            
            # Corps du tableau
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            
            # Bordures
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.darkblue),
            
            # Alternance de couleur pour lisibilité
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            
            # Styles spéciaux par colonne
            ('BACKGROUND', (0, 1), (0, -1), colors.lightblue),  # Date/Heure
            ('BACKGROUND', (2, 1), (2, -1), colors.lightyellow),  # Action
            
            # Retour à la ligne automatique
            ('WORDWRAP', (0, 0), (-1, -1), 'CJK'),
        ]))
        
        story.append(table)
    else:
        # Message si aucun log
        no_data_style = ParagraphStyle(
            'NoDataStyle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=1,
            textColor=colors.red
        )
        story.append(Paragraph("Aucun log d'activité trouvé avec les critères sélectionnés.", no_data_style))
    
    story.append(Spacer(1, 20))
    
    # Construire le PDF avec numérotation des pages
    doc.build(story, canvasmaker=NumberedCanvas)
    
    return pdf_path
