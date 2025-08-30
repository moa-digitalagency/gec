import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from datetime import datetime
import re

def get_email_template(template_type, language='fr', variables=None):
    """
    Récupère et traite un template d'email avec les variables fournies
    
    Args:
        template_type (str): Type de template (new_mail, mail_forwarded, etc.)
        language (str): Langue du template ('fr' ou 'en')
        variables (dict): Variables à remplacer dans le template
        
    Returns:
        dict: {'subject': str, 'html_content': str, 'text_content': str} ou None
    """
    if variables is None:
        variables = {}
        
    try:
        # Import ici pour éviter les imports circulaires
        from models import EmailTemplate
        
        # Récupérer le template actif pour ce type et cette langue
        template = EmailTemplate.query.filter_by(
            type_template=template_type,
            langue=language,
            actif=True
        ).first()
        
        if not template:
            # Fallback vers le français si le template en anglais n'existe pas
            if language == 'en':
                template = EmailTemplate.query.filter_by(
                    type_template=template_type,
                    langue='fr',
                    actif=True
                ).first()
            
            if not template:
                logging.warning(f"Aucun template trouvé pour {template_type}:{language}")
                return None
        
        # Remplacer les variables dans le sujet et le contenu
        subject = template.sujet
        html_content = template.contenu_html
        text_content = template.contenu_texte
        
        # Remplacer les variables avec protection contre les erreurs
        for var_name, var_value in variables.items():
            # Convertir None en chaîne vide et échapper les valeurs
            safe_value = str(var_value) if var_value is not None else ''
            
            # Remplacer les variables dans le format {{variable}}
            pattern = f'{{{{{var_name}}}}}'
            subject = subject.replace(pattern, safe_value)
            html_content = html_content.replace(pattern, safe_value)
            if text_content:
                text_content = text_content.replace(pattern, safe_value)
        
        return {
            'subject': subject,
            'html_content': html_content,
            'text_content': text_content
        }
        
    except Exception as e:
        logging.error(f"Erreur lors de la récupération du template {template_type}:{language}: {e}")
        return None

def send_email_from_system_config(to_email, subject, html_content, text_content=None, attachment_path=None):
    """
    Envoie un email en utilisant les paramètres SMTP configurés dans les paramètres système
    
    Args:
        to_email (str): Adresse email du destinataire
        subject (str): Sujet de l'email
        html_content (str): Contenu HTML de l'email
        text_content (str, optional): Contenu texte alternatif
        attachment_path (str, optional): Chemin vers le fichier à joindre
    
    Returns:
        bool: True si l'email a été envoyé avec succès, False sinon
    """
    try:
        # Import ici pour éviter les imports circulaires
        from models import ParametresSysteme
        
        # Récupérer les paramètres SMTP du système
        smtp_server = ParametresSysteme.get_valeur('smtp_server')
        smtp_port = ParametresSysteme.get_valeur('smtp_port', '587')
        smtp_email = ParametresSysteme.get_valeur('smtp_email')
        smtp_password = ParametresSysteme.get_valeur('smtp_password')
        smtp_use_tls = ParametresSysteme.get_valeur('smtp_use_tls', 'True')
        
        # Fallback vers les variables d'environnement si pas configuré
        if not smtp_server:
            smtp_server = os.environ.get('SMTP_SERVER', 'localhost')
            smtp_port = os.environ.get('SMTP_PORT', '587')
            smtp_email = os.environ.get('SMTP_EMAIL')
            smtp_password = os.environ.get('SMTP_PASSWORD')
            smtp_use_tls = os.environ.get('SMTP_USE_TLS', 'True')
        
        if not smtp_email:
            logging.error("Email SMTP non configuré")
            return False
        
        # Convertir les paramètres
        smtp_port = int(smtp_port) if smtp_port else 587
        use_tls = str(smtp_use_tls).lower() == 'true'
        
        # Créer le message
        msg = MIMEMultipart('alternative')
        msg['From'] = smtp_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Ajouter le contenu texte
        if text_content:
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(text_part)
        
        # Ajouter le contenu HTML
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Ajouter une pièce jointe si fournie
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(attachment_path)}'
            )
            msg.attach(part)
        
        # Envoyer l'email
        server = smtplib.SMTP(smtp_server, smtp_port)
        
        if use_tls:
            server.starttls()
        
        # Se connecter seulement si un mot de passe est fourni
        if smtp_password:
            # Déchiffrer le mot de passe s'il est crypté
            try:
                if smtp_password.startswith('encrypted:'):
                    from encryption_utils import EncryptionManager
                    encryption_manager = EncryptionManager()
                    smtp_password = encryption_manager.decrypt_data(smtp_password)
            except Exception as e:
                logging.warning(f"Impossible de déchiffrer le mot de passe SMTP: {e}")
            
            server.login(smtp_email, smtp_password)
        
        server.send_message(msg)
        server.quit()
        
        logging.info(f"Email envoyé avec succès à {to_email}")
        return True
        
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi de l'email à {to_email}: {str(e)}")
        return False

def send_email(to_email, subject, html_content, text_content=None, attachment_path=None):
    """
    Envoie un email en utilisant un serveur SMTP standard
    
    Args:
        to_email (str): Adresse email du destinataire
        subject (str): Sujet de l'email
        html_content (str): Contenu HTML de l'email
        text_content (str, optional): Contenu texte alternatif
        attachment_path (str, optional): Chemin vers le fichier à joindre
    
    Returns:
        bool: True si l'email a été envoyé avec succès, False sinon
    """
    try:
        # Configuration SMTP standard (configurable)
        smtp_server = os.environ.get('SMTP_SERVER', 'localhost')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        sender_email = os.environ.get('SMTP_EMAIL')
        sender_password = os.environ.get('SMTP_PASSWORD')
        use_tls = os.environ.get('SMTP_USE_TLS', 'True').lower() == 'true'
        
        if not sender_email:
            logging.error("Email SMTP non configuré")
            return False
        
        # Créer le message
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Ajouter le contenu texte
        if text_content:
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(text_part)
        
        # Ajouter le contenu HTML
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Ajouter une pièce jointe si fournie
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(attachment_path)}'
            )
            msg.attach(part)
        
        # Envoyer l'email
        server = smtplib.SMTP(smtp_server, smtp_port)
        
        if use_tls:
            server.starttls()
        
        # Se connecter seulement si un mot de passe est fourni
        if sender_password:
            server.login(sender_email, sender_password)
        
        server.send_message(msg)
        server.quit()
        
        logging.info(f"Email envoyé avec succès à {to_email}")
        return True
        
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi de l'email à {to_email}: {str(e)}")
        return False

def send_new_mail_notification(admins_emails, courrier_data, language='fr'):
    """
    Envoie une notification aux administrateurs lors de l'ajout d'un nouveau courrier
    
    Args:
        admins_emails (list): Liste des emails des administrateurs
        courrier_data (dict): Données du courrier
        language (str): Langue de l'email ('fr' ou 'en')
    
    Returns:
        bool: True si tous les emails ont été envoyés avec succès
    """
    success_count = 0
    
    # Import ici pour éviter les imports circulaires
    from models import ParametresSysteme
    
    # Récupérer le nom du logiciel depuis les paramètres système
    nom_logiciel = ParametresSysteme.get_valeur('nom_logiciel', 'GEC')
    
    # Préparer les variables pour le template
    variables = {
        'numero_courrier': courrier_data.get('numero_accuse_reception', 'N/A'),
        'objet': courrier_data.get('objet', 'N/A'),
        'expediteur': courrier_data.get('expediteur', 'N/A'),
        'type_courrier': courrier_data.get('type_courrier', 'N/A'),
        'date_reception': datetime.now().strftime('%d/%m/%Y à %H:%M'),
        'nom_utilisateur': courrier_data.get('created_by', 'N/A'),
        'nom_logiciel': nom_logiciel,
        'url_courrier': courrier_data.get('url_courrier', '#')
    }
    
    # Récupérer le template d'email
    template_data = get_email_template('new_mail', language, variables)
    
    if template_data:
        # Utiliser le template personnalisé
        subject = template_data['subject']
        html_content = template_data['html_content']
        text_content = template_data['text_content']
    else:
        # Fallback vers le template par défaut si aucun template trouvé
        subject = f"Nouveau courrier enregistré - {courrier_data.get('numero_accuse_reception', 'N/A')}"
        
        # Template HTML par défaut
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
                .footer {{ background-color: #f1f1f1; padding: 10px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>{nom_logiciel} - Notification de Nouveau Courrier</h2>
            </div>
            <div class="content">
                <p>Bonjour,</p>
                <p>Un nouveau courrier a été enregistré dans le système {nom_logiciel}.</p>
                
                <div class="details">
                    <h3>Détails du courrier :</h3>
                    <p><strong>Numéro d'accusé de réception :</strong> {courrier_data.get('numero_accuse_reception', 'N/A')}</p>
                    <p><strong>Type :</strong> {courrier_data.get('type_courrier', 'N/A')}</p>
                    <p><strong>Objet :</strong> {courrier_data.get('objet', 'N/A')}</p>
                    <p><strong>Expéditeur :</strong> {courrier_data.get('expediteur', 'N/A')}</p>
                    <p><strong>Date d'enregistrement :</strong> {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
                    <p><strong>Enregistré par :</strong> {courrier_data.get('created_by', 'N/A')}</p>
                </div>
                
                <p>Vous pouvez consulter ce courrier en vous connectant au système {nom_logiciel}.</p>
            </div>
            <div class="footer">
                <p>{nom_logiciel} - Système de Gestion des Courriers<br>
                Secrétariat Général des Mines - République Démocratique du Congo</p>
            </div>
        </body>
        </html>
        """
        
        # Template texte par défaut
        text_content = f"""
        {nom_logiciel} - Notification de Nouveau Courrier
        
        Un nouveau courrier a été enregistré dans le système.
        
        Détails du courrier :
        - Numéro d'accusé de réception : {courrier_data.get('numero_accuse_reception', 'N/A')}
        - Type : {courrier_data.get('type_courrier', 'N/A')}
        - Objet : {courrier_data.get('objet', 'N/A')}
        - Expéditeur : {courrier_data.get('expediteur', 'N/A')}
        - Date d'enregistrement : {datetime.now().strftime('%d/%m/%Y à %H:%M')}
        - Enregistré par : {courrier_data.get('created_by', 'N/A')}
        
        Connectez-vous au système {nom_logiciel} pour consulter ce courrier.
        
        {nom_logiciel} - Système de Gestion des Courriers
        Secrétariat Général des Mines - République Démocratique du Congo
        """
    
    # Envoyer l'email à tous les administrateurs
    for email in admins_emails:
        if send_email_from_system_config(email, subject, html_content, text_content):
            success_count += 1
    
    return success_count == len(admins_emails)

def send_mail_forwarded_notification(user_email, courrier_data, forwarded_by, user_name='', language='fr'):
    """
    Envoie une notification à un utilisateur quand un courrier lui est transmis
    
    Args:
        user_email (str): Email de l'utilisateur destinataire
        courrier_data (dict): Données du courrier
        forwarded_by (str): Nom de la personne qui a transmis le courrier
        user_name (str): Nom de l'utilisateur destinataire
        language (str): Langue de l'email ('fr' ou 'en')
    
    Returns:
        bool: True si l'email a été envoyé avec succès
    """
    # Import ici pour éviter les imports circulaires
    from models import ParametresSysteme
    
    # Récupérer le nom du logiciel depuis les paramètres système
    nom_logiciel = ParametresSysteme.get_valeur('nom_logiciel', 'GEC')
    
    # Préparer les variables pour le template
    variables = {
        'numero_courrier': courrier_data.get('numero_accuse_reception', 'N/A'),
        'objet': courrier_data.get('objet', 'N/A'),
        'expediteur': courrier_data.get('expediteur', 'N/A'),
        'type_courrier': courrier_data.get('type_courrier', 'N/A'),
        'date_reception': datetime.now().strftime('%d/%m/%Y à %H:%M'),
        'nom_utilisateur': user_name or 'utilisateur',
        'nom_logiciel': nom_logiciel,
        'url_courrier': courrier_data.get('url_courrier', '#'),
        'transmis_par': forwarded_by
    }
    
    # Récupérer le template d'email
    template_data = get_email_template('mail_forwarded', language, variables)
    
    if template_data:
        # Utiliser le template personnalisé
        subject = template_data['subject']
        html_content = template_data['html_content']
        text_content = template_data['text_content']
    else:
        # Fallback vers le template par défaut si aucun template trouvé
        subject = f"Courrier transmis - {courrier_data.get('numero_accuse_reception', 'N/A')}"
        
        # Template HTML par défaut
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #009639; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .details {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .footer {{ background-color: #f1f1f1; padding: 10px; text-align: center; font-size: 12px; }}
                .action-btn {{ background-color: #003087; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>{nom_logiciel} - Courrier Transmis</h2>
            </div>
            <div class="content">
                <p>Bonjour {user_name or ''},</p>
                <p>Un courrier vous a été transmis par <strong>{forwarded_by}</strong>.</p>
                
                <div class="details">
                    <h3>Détails du courrier :</h3>
                    <p><strong>Numéro d'accusé de réception :</strong> {courrier_data.get('numero_accuse_reception', 'N/A')}</p>
                    <p><strong>Type :</strong> {courrier_data.get('type_courrier', 'N/A')}</p>
                    <p><strong>Objet :</strong> {courrier_data.get('objet', 'N/A')}</p>
                    <p><strong>Expéditeur :</strong> {courrier_data.get('expediteur', 'N/A')}</p>
                    <p><strong>Date de transmission :</strong> {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
                </div>
                
                <p>Veuillez vous connecter au système {nom_logiciel} pour consulter ce courrier.</p>
            </div>
            <div class="footer">
                <p>{nom_logiciel} - Système de Gestion des Courriers<br>
                Secrétariat Général des Mines - République Démocratique du Congo</p>
            </div>
        </body>
        </html>
        """
        
        # Template texte par défaut
        text_content = f"""
        {nom_logiciel} - Courrier Transmis
        
        Un courrier vous a été transmis par {forwarded_by}.
        
        Détails du courrier :
        - Numéro d'accusé de réception : {courrier_data.get('numero_accuse_reception', 'N/A')}
        - Type : {courrier_data.get('type_courrier', 'N/A')}
        - Objet : {courrier_data.get('objet', 'N/A')}
        - Expéditeur : {courrier_data.get('expediteur', 'N/A')}
        - Date de transmission : {datetime.now().strftime('%d/%m/%Y à %H:%M')}
        
        Connectez-vous au système {nom_logiciel} pour consulter ce courrier.
        
        {nom_logiciel} - Système de Gestion des Courriers
        Secrétariat Général des Mines - République Démocratique du Congo
        """
    
    return send_email_from_system_config(user_email, subject, html_content, text_content)