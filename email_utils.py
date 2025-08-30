import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from datetime import datetime
import re

# Import SendGrid
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logging.warning("SendGrid non disponible, utilisation de SMTP traditionnel")

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

def send_email_with_sendgrid(to_email, subject, html_content, text_content=None, attachment_path=None):
    """
    Envoie un email via SendGrid API
    
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
        
        # Récupérer la clé API SendGrid
        sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        if not sendgrid_api_key:
            logging.error("Clé API SendGrid non configurée")
            return False
        
        # Récupérer l'email expéditeur depuis les paramètres système
        sender_email = ParametresSysteme.get_valeur('smtp_username')
        if not sender_email:
            sender_email = os.environ.get('SMTP_EMAIL', 'noreply@gec.local')
        
        # Créer le message SendGrid
        message = Mail(
            from_email=Email(sender_email),
            to_emails=To(to_email),
            subject=subject
        )
        
        # Ajouter le contenu
        if html_content:
            message.content = Content("text/html", html_content)
        elif text_content:
            message.content = Content("text/plain", text_content)
        
        # Gérer les pièces jointes (SendGrid supporte les attachments)
        if attachment_path and os.path.exists(attachment_path):
            import base64
            from sendgrid.helpers.mail import Attachment, FileContent, FileName, FileType, Disposition
            
            with open(attachment_path, 'rb') as f:
                data = f.read()
                encoded = base64.b64encode(data).decode()
            
            attached_file = Attachment(
                FileContent(encoded),
                FileName(os.path.basename(attachment_path)),
                FileType('application/octet-stream'),
                Disposition('attachment')
            )
            message.attachment = attached_file
        
        # Envoyer via SendGrid
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        
        logging.info(f"Email envoyé avec succès via SendGrid à {to_email} (Status: {response.status_code})")
        return True
        
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi via SendGrid à {to_email}: {str(e)}")
        return False

def test_sendgrid_configuration(test_email):
    """
    Teste la configuration SendGrid en envoyant un email de test
    
    Args:
        test_email (str): Adresse email pour recevoir le test
        
    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        # Vérifier que SendGrid est disponible
        if not SENDGRID_AVAILABLE:
            return {
                'success': False,
                'message': 'SendGrid n\'est pas installé. Veuillez installer le package sendgrid.'
            }
        
        # Vérifier la clé API
        sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        if not sendgrid_api_key:
            return {
                'success': False,
                'message': 'Clé API SendGrid non configurée. Veuillez configurer SENDGRID_API_KEY.'
            }
        
        # Import ici pour éviter les imports circulaires
        from models import ParametresSysteme
        
        # Récupérer l'email expéditeur
        sender_email = ParametresSysteme.get_valeur('smtp_username')
        if not sender_email:
            sender_email = os.environ.get('SMTP_EMAIL', 'noreply@gec.local')
        
        # Récupérer le nom du logiciel
        software_name = ParametresSysteme.get_valeur('nom_logiciel', 'GEC')
        
        # Créer le contenu du test
        subject = f"Test de configuration SendGrid - {software_name}"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h2 style="color: #003087; text-align: center;">✅ Test SendGrid Réussi</h2>
                <p>Félicitations ! Votre configuration SendGrid fonctionne correctement.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">Détails du test :</h3>
                    <ul>
                        <li><strong>Système :</strong> {software_name}</li>
                        <li><strong>Date :</strong> {datetime.now().strftime('%d/%m/%Y à %H:%M')}</li>
                        <li><strong>Email expéditeur :</strong> {sender_email}</li>
                        <li><strong>Email destinataire :</strong> {test_email}</li>
                    </ul>
                </div>
                
                <p style="color: #6c757d; font-size: 14px; margin-top: 30px;">
                    Ce message a été envoyé automatiquement depuis votre système {software_name} 
                    pour vérifier la configuration SendGrid.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Test SendGrid Réussi - {software_name}
        
        Félicitations ! Votre configuration SendGrid fonctionne correctement.
        
        Détails du test :
        - Système : {software_name}
        - Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}
        - Email expéditeur : {sender_email}
        - Email destinataire : {test_email}
        
        Ce message a été envoyé automatiquement pour vérifier la configuration SendGrid.
        """
        
        # Envoyer l'email de test
        success = send_email_with_sendgrid(test_email, subject, html_content, text_content)
        
        if success:
            return {
                'success': True,
                'message': f'Email de test envoyé avec succès à {test_email}. Vérifiez votre boîte de réception.'
            }
        else:
            return {
                'success': False,
                'message': 'Échec de l\'envoi de l\'email de test. Vérifiez vos logs pour plus de détails.'
            }
            
    except Exception as e:
        logging.error(f"Erreur lors du test SendGrid: {str(e)}")
        return {
            'success': False,
            'message': f'Erreur lors du test : {str(e)}'
        }

def send_email_from_system_config(to_email, subject, html_content, text_content=None, attachment_path=None):
    """
    Envoie un email en utilisant SendGrid (priorité) ou SMTP traditionnel (fallback)
    
    Args:
        to_email (str): Adresse email du destinataire
        subject (str): Sujet de l'email
        html_content (str): Contenu HTML de l'email
        text_content (str, optional): Contenu texte alternatif
        attachment_path (str, optional): Chemin vers le fichier à joindre
    
    Returns:
        bool: True si l'email a été envoyé avec succès, False sinon
    """
    print(f"DEBUG: send_email_from_system_config appelée pour {to_email}")
    
    # Import ici pour éviter les imports circulaires
    from models import ParametresSysteme
    
    # Vérifier le choix du fournisseur email dans les paramètres
    email_provider = ParametresSysteme.get_valeur('email_provider', 'sendgrid')
    sendgrid_key = os.environ.get('SENDGRID_API_KEY')
    
    print(f"DEBUG: email_provider={email_provider}, SENDGRID_AVAILABLE={SENDGRID_AVAILABLE}, sendgrid_key={'configured' if sendgrid_key else 'missing'}")
    
    if email_provider == 'sendgrid' and SENDGRID_AVAILABLE and sendgrid_key:
        print(f"DEBUG: Tentative d'envoi via SendGrid à {to_email}")
        logging.info("Tentative d'envoi via SendGrid...")
        result = send_email_with_sendgrid(to_email, subject, html_content, text_content, attachment_path)
        print(f"DEBUG: Résultat SendGrid: {result}")
        if result:
            return True
        else:
            logging.warning("Échec SendGrid, tentative SMTP traditionnel...")
            print(f"DEBUG: Échec SendGrid, fallback vers SMTP")
    
    # Utiliser SMTP traditionnel (soit par choix, soit par fallback)
    print(f"DEBUG: Tentative d'envoi via SMTP traditionnel à {to_email}")
    logging.info("Tentative d'envoi via SMTP traditionnel...")
    result = send_email_with_smtp(to_email, subject, html_content, text_content, attachment_path)
    print(f"DEBUG: Résultat SMTP: {result}")
    return result

def send_email_with_smtp(to_email, subject, html_content, text_content=None, attachment_path=None):
    """
    Envoie un email via SMTP traditionnel
    
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
        smtp_email = ParametresSysteme.get_valeur('smtp_username')  # Le champ est smtp_username
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
            
        # Debug des paramètres SMTP
        logging.info(f"DEBUG SMTP - Server: {smtp_server}, Port: {smtp_port}, Email: {smtp_email}, TLS: {use_tls}")
        logging.info(f"DEBUG SMTP - Password configured: {'Oui' if smtp_password else 'Non'}")
        
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
        
        # Envoyer l'email - gérer SSL vs TLS selon le port
        if smtp_port == 465:
            # Port 465 utilise SSL direct
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # Autres ports (587, 25) utilisent STARTTLS
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
        
        # Envoyer l'email - gérer SSL vs TLS selon le port
        if smtp_port == 465:
            # Port 465 utilise SSL direct
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # Autres ports (587, 25) utilisent STARTTLS
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
    print(f"DEBUG: send_mail_forwarded_notification appelée avec email={user_email}, forwarded_by={forwarded_by}")
    
    if not user_email or not user_email.strip():
        print(f"DEBUG: Email utilisateur vide ou invalide: '{user_email}'")
        return False
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
    
    print(f"DEBUG: Tentative d'envoi d'email de transmission via send_email_from_system_config à {user_email}")
    result = send_email_from_system_config(user_email, subject, html_content, text_content)
    print(f"DEBUG: Résultat de l'envoi d'email de transmission: {result}")
    return result