import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from datetime import datetime

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

def send_new_mail_notification(admins_emails, courrier_data):
    """
    Envoie une notification aux administrateurs lors de l'ajout d'un nouveau courrier
    
    Args:
        admins_emails (list): Liste des emails des administrateurs
        courrier_data (dict): Données du courrier
    
    Returns:
        bool: True si tous les emails ont été envoyés avec succès
    """
    success_count = 0
    
    subject = f"Nouveau courrier enregistré - {courrier_data.get('numero_accuse_reception', 'N/A')}"
    
    # Contenu HTML de l'email
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
            <h2>GEC Mines - Notification de Nouveau Courrier</h2>
        </div>
        <div class="content">
            <p>Bonjour,</p>
            <p>Un nouveau courrier a été enregistré dans le système GEC Mines.</p>
            
            <div class="details">
                <h3>Détails du courrier :</h3>
                <p><strong>Numéro d'accusé de réception :</strong> {courrier_data.get('numero_accuse_reception', 'N/A')}</p>
                <p><strong>Type :</strong> {courrier_data.get('type_courrier', 'N/A')}</p>
                <p><strong>Objet :</strong> {courrier_data.get('objet', 'N/A')}</p>
                <p><strong>Expéditeur :</strong> {courrier_data.get('expediteur', 'N/A')}</p>
                <p><strong>Date d'enregistrement :</strong> {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
                <p><strong>Enregistré par :</strong> {courrier_data.get('created_by', 'N/A')}</p>
            </div>
            
            <p>Vous pouvez consulter ce courrier en vous connectant au système GEC Mines.</p>
        </div>
        <div class="footer">
            <p>GEC Mines - Système de Gestion des Courriers<br>
            Secrétariat Général des Mines - République Démocratique du Congo</p>
        </div>
    </body>
    </html>
    """
    
    # Contenu texte alternatif
    text_content = f"""
    GEC Mines - Notification de Nouveau Courrier
    
    Un nouveau courrier a été enregistré dans le système.
    
    Détails du courrier :
    - Numéro d'accusé de réception : {courrier_data.get('numero_accuse_reception', 'N/A')}
    - Type : {courrier_data.get('type_courrier', 'N/A')}
    - Objet : {courrier_data.get('objet', 'N/A')}
    - Expéditeur : {courrier_data.get('expediteur', 'N/A')}
    - Date d'enregistrement : {datetime.now().strftime('%d/%m/%Y à %H:%M')}
    - Enregistré par : {courrier_data.get('created_by', 'N/A')}
    
    Connectez-vous au système GEC Mines pour consulter ce courrier.
    
    GEC Mines - Système de Gestion des Courriers
    Secrétariat Général des Mines - République Démocratique du Congo
    """
    
    for email in admins_emails:
        if send_email(email, subject, html_content, text_content):
            success_count += 1
    
    return success_count == len(admins_emails)

def send_mail_forwarded_notification(user_email, courrier_data, forwarded_by):
    """
    Envoie une notification à un utilisateur quand un courrier lui est transmis
    
    Args:
        user_email (str): Email de l'utilisateur destinataire
        courrier_data (dict): Données du courrier
        forwarded_by (str): Nom de la personne qui a transmis le courrier
    
    Returns:
        bool: True si l'email a été envoyé avec succès
    """
    subject = f"Courrier transmis - {courrier_data.get('numero_accuse_reception', 'N/A')}"
    
    # Contenu HTML de l'email
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
            <h2>GEC Mines - Courrier Transmis</h2>
        </div>
        <div class="content">
            <p>Bonjour,</p>
            <p>Un courrier vous a été transmis par <strong>{forwarded_by}</strong>.</p>
            
            <div class="details">
                <h3>Détails du courrier :</h3>
                <p><strong>Numéro d'accusé de réception :</strong> {courrier_data.get('numero_accuse_reception', 'N/A')}</p>
                <p><strong>Type :</strong> {courrier_data.get('type_courrier', 'N/A')}</p>
                <p><strong>Objet :</strong> {courrier_data.get('objet', 'N/A')}</p>
                <p><strong>Expéditeur :</strong> {courrier_data.get('expediteur', 'N/A')}</p>
                <p><strong>Date de transmission :</strong> {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
            </div>
            
            <p>Veuillez vous connecter au système GEC Mines pour consulter ce courrier.</p>
        </div>
        <div class="footer">
            <p>GEC Mines - Système de Gestion des Courriers<br>
            Secrétariat Général des Mines - République Démocratique du Congo</p>
        </div>
    </body>
    </html>
    """
    
    # Contenu texte alternatif
    text_content = f"""
    GEC Mines - Courrier Transmis
    
    Un courrier vous a été transmis par {forwarded_by}.
    
    Détails du courrier :
    - Numéro d'accusé de réception : {courrier_data.get('numero_accuse_reception', 'N/A')}
    - Type : {courrier_data.get('type_courrier', 'N/A')}
    - Objet : {courrier_data.get('objet', 'N/A')}
    - Expéditeur : {courrier_data.get('expediteur', 'N/A')}
    - Date de transmission : {datetime.now().strftime('%d/%m/%Y à %H:%M')}
    
    Connectez-vous au système GEC Mines pour consulter ce courrier.
    
    GEC Mines - Système de Gestion des Courriers
    Secrétariat Général des Mines - République Démocratique du Congo
    """
    
    return send_email(user_email, subject, html_content, text_content)