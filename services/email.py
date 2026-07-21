"""
Utilitaires d'envoi d'emails — GEC
Provider principal : Resend (https://resend.com/docs)
Fallback         : SMTP traditionnel
"""
import os
import smtplib
import logging
import socket
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# ---------------------------------------------------------------------------
# Resend SDK
# ---------------------------------------------------------------------------
try:
    import resend as _resend_sdk
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
    logging.warning("Package 'resend' non disponible — fallback SMTP actif")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def validate_email_format(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) if email else False


def check_internet_connection() -> bool:
    for host in ("8.8.8.8", "1.1.1.1"):
        try:
            socket.create_connection((host, 53), timeout=3)
            return True
        except (socket.error, socket.timeout):
            continue
    return False


# ---------------------------------------------------------------------------
# Email template engine
# ---------------------------------------------------------------------------

def get_email_template(template_type: str, language: str = 'fr', variables: dict = None):
    """
    Récupère un template d'email depuis la base de données et remplace les variables.
    Retourne un dict {'subject', 'html_content', 'text_content'} ou None.
    """
    if variables is None:
        variables = {}

    try:
        from models import EmailTemplate

        template = EmailTemplate.query.filter_by(
            type_template=template_type, langue=language, actif=True
        ).first()

        if not template and language == 'en':
            template = EmailTemplate.query.filter_by(
                type_template=template_type, langue='fr', actif=True
            ).first()

        if not template:
            logging.warning(f"Aucun template pour {template_type}:{language}")
            return None

        subject      = template.sujet
        html_content = template.contenu_html
        text_content = template.contenu_texte

        for var_name, var_value in variables.items():
            safe_value = str(var_value) if var_value is not None else ''
            safe_value = (safe_value
                          .replace('&', '&amp;').replace('<', '&lt;')
                          .replace('>', '&gt;').replace('"', '&quot;')
                          .replace("'", '&#x27;'))
            for pattern in (f'{{{{{var_name}}}}}', f'{{{var_name}}}'):
                if subject:      subject      = subject.replace(pattern, safe_value)
                if html_content: html_content = html_content.replace(pattern, safe_value)
                if text_content: text_content = text_content.replace(pattern, safe_value)

        return {'subject': subject, 'html_content': html_content, 'text_content': text_content}

    except Exception as e:
        logging.error(f"Erreur template {template_type}:{language}: {e}")
        return None


# ---------------------------------------------------------------------------
# Resend sender
# ---------------------------------------------------------------------------

def send_email_with_resend(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str = None,
    attachment_path: str = None,
) -> bool:
    """
    Envoie un email via l'API Resend.
    Doc : https://resend.com/docs/api-reference/emails/send-email
    """
    if not RESEND_AVAILABLE:
        logging.warning("SDK Resend non installé")
        return False

    try:
        from models import ParametresSysteme

        parametres   = ParametresSysteme.get_parametres()
        resend_api_key = parametres.get_resend_api_key()
        if not resend_api_key:
            logging.error("Clé API Resend non configurée dans les paramètres système")
            return False

        # From-address priority: email_contact → smtp_username → onboarding@resend.dev
        email_contact = ParametresSysteme.get_valeur('email_contact') or ''
        smtp_username = ParametresSysteme.get_valeur('smtp_username') or ''
        nom_logiciel  = ParametresSysteme.get_valeur('nom_logiciel', 'GEC')

        # Resend free tier only allows onboarding@resend.dev or a verified domain
        # Use onboarding@resend.dev as safe default when no real domain is configured
        if email_contact and '@' in email_contact and not email_contact.endswith('.local'):
            sender_email = email_contact
        elif smtp_username and '@' in smtp_username and not smtp_username.endswith('.local'):
            sender_email = smtp_username
        else:
            sender_email = 'onboarding@resend.dev'

        _resend_sdk.api_key = resend_api_key

        params: _resend_sdk.Emails.SendParams = {
            "from": f"{nom_logiciel} <{sender_email}>",
            "to": [to_email],
            "subject": subject,
        }

        if html_content:
            params["html"] = html_content
        if text_content:
            params["text"] = text_content

        # Pièce jointe
        if attachment_path and os.path.exists(attachment_path):
            import base64
            with open(attachment_path, 'rb') as f:
                content_bytes = f.read()
            params["attachments"] = [
                {
                    "filename": os.path.basename(attachment_path),
                    "content":  list(content_bytes),
                }
            ]

        result = _resend_sdk.Emails.send(params)
        logging.info(f"Email Resend envoyé à {to_email} — id={getattr(result, 'id', result)}")
        return True

    except Exception as e:
        logging.error(f"Erreur Resend pour {to_email}: {e}")
        return False


# ---------------------------------------------------------------------------
# Test / diagnostic Resend
# ---------------------------------------------------------------------------

def verify_resend_prerequisites(test_email: str) -> dict:
    result = {
        'internet': False,
        'api_configured': False,
        'email_valid': False,
        'all_ok': False,
        'error_message': None,
        'diagnostic_details': [],
    }

    # 1. Internet
    result['internet'] = check_internet_connection()
    status = "✅ OK" if result['internet'] else "❌ ÉCHEC"
    result['diagnostic_details'].append(f"🌐 Connexion Internet: {status}")
    if not result['internet']:
        result['error_message'] = "Pas de connexion Internet."
        return result

    # 2. Clé Resend
    try:
        from models import ParametresSysteme
        parametres = ParametresSysteme.get_parametres()
        key = parametres.get_resend_api_key()
    except Exception:
        key = None

    result['api_configured'] = bool(key and key.startswith('re_') and len(key) > 10)
    status = f"✅ OK ({len(key)} car.)" if result['api_configured'] else "❌ ÉCHEC"
    result['diagnostic_details'].append(f"🔑 Clé API Resend: {status}")
    if not result['api_configured']:
        result['error_message'] = "Clé API Resend invalide ou manquante (doit commencer par 're_')."
        return result

    # 3. Email
    result['email_valid'] = validate_email_format(test_email)
    status = "✅ OK" if result['email_valid'] else "❌ ÉCHEC"
    result['diagnostic_details'].append(f"📧 Format email: {status}")
    if not result['email_valid']:
        result['error_message'] = f"Adresse email invalide : '{test_email}'"
        return result

    result['all_ok'] = True
    result['diagnostic_details'].append("✅ Toutes les conditions remplies — prêt à envoyer")
    return result


def test_resend_configuration(test_email: str) -> dict:
    """Test complet de la configuration Resend."""
    if not RESEND_AVAILABLE:
        return {'success': False, 'message': "Package 'resend' non installé (pip install resend)."}

    prerequisites = verify_resend_prerequisites(test_email)
    if not prerequisites['all_ok']:
        details = "\n".join(prerequisites['diagnostic_details'])
        return {
            'success': False,
            'message': f"{prerequisites['error_message']}\n\n📋 Diagnostic:\n{details}"
        }

    try:
        from models import ParametresSysteme
        software_name = ParametresSysteme.get_valeur('nom_logiciel', 'GEC')
        email_contact = ParametresSysteme.get_valeur('email_contact') or ''
        smtp_username = ParametresSysteme.get_valeur('smtp_username') or ''
        if email_contact and '@' in email_contact and not email_contact.endswith('.local'):
            sender_email = email_contact
        elif smtp_username and '@' in smtp_username and not smtp_username.endswith('.local'):
            sender_email = smtp_username
        else:
            sender_email = 'onboarding@resend.dev'
    except Exception:
        software_name = 'GEC'
        sender_email  = 'onboarding@resend.dev'

    subject = f"Test Resend — {software_name}"
    html_content = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333">
      <div style="max-width:600px;margin:0 auto;padding:20px;border:1px solid #ddd;border-radius:8px">
        <h2 style="color:#003087;text-align:center">✅ Test Resend Réussi</h2>
        <p>Votre configuration Resend fonctionne correctement.</p>
        <div style="background:#f8f9fa;padding:15px;border-radius:5px;margin:20px 0">
          <ul>
            <li><strong>Système :</strong> {software_name}</li>
            <li><strong>Date :</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</li>
            <li><strong>Expéditeur :</strong> {sender_email}</li>
            <li><strong>Destinataire :</strong> {test_email}</li>
          </ul>
        </div>
      </div>
    </body></html>
    """

    # Send and capture detailed API errors
    try:
        parametres   = ParametresSysteme.get_parametres()
        resend_api_key = parametres.get_resend_api_key()
        _resend_sdk.api_key = resend_api_key

        params = {
            "from": f"{software_name} <{sender_email}>",
            "to":   [test_email],
            "subject": subject,
            "html": html_content,
        }
        _resend_sdk.Emails.send(params)
        details = "\n".join(prerequisites['diagnostic_details'])
        return {'success': True, 'message': f"✅ Email de test envoyé à {test_email}.\n\n📋 Vérifications:\n{details}"}
    except Exception as api_err:
        err_str = str(api_err)
        details = "\n".join(prerequisites['diagnostic_details'])
        hint = ""
        if "domain" in err_str.lower() or "sender" in err_str.lower() or "from" in err_str.lower():
            hint = f"\n\n💡 Astuce : votre domaine expéditeur ({sender_email}) n'est peut-être pas vérifié sur Resend. Vérifiez https://resend.com/domains ou utilisez onboarding@resend.dev pour les tests."
        return {
            'success': False,
            'message': f"❌ Erreur API Resend : {err_str}{hint}\n\n📋 Vérifications:\n{details}"
        }


# ---------------------------------------------------------------------------
# Main dispatcher : Resend → SMTP → simulation
# ---------------------------------------------------------------------------

def send_email_from_system_config(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str = None,
    attachment_path: str = None,
) -> bool:
    """
    Envoie via Resend (priorité) ou SMTP traditionnel (fallback).
    """
    from models import ParametresSysteme

    email_provider = ParametresSysteme.get_valeur('email_provider', 'resend')
    parametres     = ParametresSysteme.get_parametres()
    resend_key     = parametres.get_resend_api_key()

    if email_provider == 'resend' and RESEND_AVAILABLE and resend_key:
        logging.info(f"Envoi via Resend → {to_email}")
        if send_email_with_resend(to_email, subject, html_content, text_content, attachment_path):
            return True
        logging.warning("Resend échoué, tentative SMTP...")

    # SMTP fallback
    smtp_server = ParametresSysteme.get_valeur('smtp_server')
    if not smtp_server or smtp_server == 'localhost':
        logging.info(f"EMAIL SIMULATION: → {to_email} — {subject}")
        return True  # simulation mode local

    return send_email_with_smtp(to_email, subject, html_content, text_content, attachment_path)


# ---------------------------------------------------------------------------
# SMTP sender (fallback)
# ---------------------------------------------------------------------------

def send_email_with_smtp(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str = None,
    attachment_path: str = None,
) -> bool:
    try:
        from models import ParametresSysteme

        smtp_server   = ParametresSysteme.get_valeur('smtp_server') or os.environ.get('SMTP_SERVER', 'localhost')
        smtp_port     = int(ParametresSysteme.get_valeur('smtp_port', '587') or os.environ.get('SMTP_PORT', '587'))
        smtp_email    = ParametresSysteme.get_valeur('smtp_username') or os.environ.get('SMTP_EMAIL')
        smtp_password = ParametresSysteme.get_valeur('smtp_password') or os.environ.get('SMTP_PASSWORD')
        use_tls       = str(ParametresSysteme.get_valeur('smtp_use_tls', 'True')).lower() == 'true'

        if not smtp_email:
            logging.info(f"EMAIL SIMULATION (SMTP sans config) → {to_email}")
            return True

        msg = MIMEMultipart('alternative')
        msg['From']    = smtp_email
        msg['To']      = to_email
        msg['Subject'] = subject

        if text_content:
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
            msg.attach(part)

        # Déchiffrer le mot de passe SMTP si crypté
        if smtp_password and smtp_password.startswith('encrypted:'):
            try:
                from security.encryption import EncryptionManager
                smtp_password = EncryptionManager().decrypt_data(smtp_password)
            except Exception as e:
                logging.warning(f"Déchiffrement SMTP: {e}")

        server = smtplib.SMTP_SSL(smtp_server, smtp_port) if smtp_port == 465 \
                 else smtplib.SMTP(smtp_server, smtp_port)
        if smtp_port != 465 and use_tls:
            server.starttls()
        if smtp_password:
            server.login(smtp_email, smtp_password)
        server.send_message(msg)
        server.quit()

        logging.info(f"Email SMTP envoyé à {to_email}")
        return True

    except Exception as e:
        logging.error(f"Erreur SMTP vers {to_email}: {e}")
        return False


# ---------------------------------------------------------------------------
# High-level notification helpers
# ---------------------------------------------------------------------------

def send_new_mail_notification(admins_emails: list, courrier_data: dict, language: str = 'fr') -> bool:
    from models import ParametresSysteme
    nom_logiciel = ParametresSysteme.get_valeur('nom_logiciel', 'GEC')

    variables = {
        'numero_accuse_reception': courrier_data.get('numero_accuse_reception', 'N/A'),
        'numero_courrier':         courrier_data.get('numero_accuse_reception', 'N/A'),
        'objet':                   courrier_data.get('objet', 'N/A'),
        'expediteur':              courrier_data.get('expediteur', 'N/A'),
        'type_courrier':           courrier_data.get('type_courrier', 'N/A'),
        'date_enregistrement':     datetime.now().strftime('%d/%m/%Y à %H:%M'),
        'date_reception':          datetime.now().strftime('%d/%m/%Y à %H:%M'),
        'created_by':              courrier_data.get('created_by', 'N/A'),
        'nom_utilisateur':         courrier_data.get('created_by', 'N/A'),
        'nom_logiciel':            nom_logiciel,
        'url_courrier':            courrier_data.get('url_courrier', '#'),
    }

    template_data = get_email_template('new_mail', language, variables)

    if template_data:
        subject      = template_data['subject']
        html_content = template_data['html_content']
        text_content = template_data['text_content']
    else:
        subject = f"Nouveau courrier — {courrier_data.get('numero_accuse_reception', 'N/A')}"
        html_content = f"""
        <html><body style="font-family:Arial,sans-serif;color:#333">
          <div style="max-width:600px;margin:0 auto;padding:20px;border:1px solid #ddd;border-radius:8px">
            <div style="background:#003087;color:white;padding:20px;text-align:center;border-radius:6px 6px 0 0">
              <h2>{nom_logiciel} — Nouveau Courrier</h2>
            </div>
            <div style="padding:20px">
              <p>Bonjour,</p>
              <p>Un nouveau courrier a été enregistré.</p>
              <div style="background:#f8f9fa;padding:15px;border-radius:5px;margin:10px 0">
                <p><strong>N° Accusé :</strong> {courrier_data.get('numero_accuse_reception','N/A')}</p>
                <p><strong>Type :</strong> {courrier_data.get('type_courrier','N/A')}</p>
                <p><strong>Objet :</strong> {courrier_data.get('objet','N/A')}</p>
                <p><strong>Expéditeur :</strong> {courrier_data.get('expediteur','N/A')}</p>
                <p><strong>Date :</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p><strong>Enregistré par :</strong> {courrier_data.get('created_by','N/A')}</p>
              </div>
            </div>
          </div>
        </body></html>"""
        text_content = (
            f"{nom_logiciel} — Nouveau courrier\n"
            f"N° {courrier_data.get('numero_accuse_reception','N/A')} · "
            f"{courrier_data.get('objet','N/A')} · "
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )

    success_count = sum(
        1 for email in admins_emails
        if send_email_from_system_config(email, subject, html_content, text_content)
    )
    return success_count == len(admins_emails)


def send_mail_forwarded_notification(
    user_email: str,
    courrier_data: dict,
    forwarded_by: str,
    user_name: str = '',
    language: str = 'fr',
) -> bool:
    if not user_email or not user_email.strip():
        return False

    from models import ParametresSysteme
    nom_logiciel = ParametresSysteme.get_valeur('nom_logiciel', 'GEC')

    variables = {
        'numero_accuse_reception': courrier_data.get('numero_accuse_reception', 'N/A'),
        'numero_courrier':         courrier_data.get('numero_accuse_reception', 'N/A'),
        'objet':                   courrier_data.get('objet', 'N/A'),
        'expediteur':              courrier_data.get('expediteur', 'N/A'),
        'type_courrier':           courrier_data.get('type_courrier', 'N/A'),
        'date_transmission':       datetime.now().strftime('%d/%m/%Y à %H:%M'),
        'date_reception':          datetime.now().strftime('%d/%m/%Y à %H:%M'),
        'nom_utilisateur':         user_name or 'utilisateur',
        'nom_logiciel':            nom_logiciel,
        'url_courrier':            courrier_data.get('url_courrier', '#'),
        'transmis_par':            forwarded_by,
        'forwarded_by':            forwarded_by,
        'message_accompagnement':  courrier_data.get('message', ''),
        'piece_jointe':            courrier_data.get('attachment_info', ''),
    }

    template_data = get_email_template('mail_forwarded', language, variables)

    if template_data:
        subject      = template_data['subject']
        html_content = template_data['html_content']
        text_content = template_data['text_content']
    else:
        subject = f"Courrier transmis — {courrier_data.get('numero_accuse_reception','N/A')}"
        html_content = f"""
        <html><body style="font-family:Arial,sans-serif;color:#333">
          <div style="max-width:600px;margin:0 auto;padding:20px;border:1px solid #ddd;border-radius:8px">
            <div style="background:#009639;color:white;padding:20px;text-align:center;border-radius:6px 6px 0 0">
              <h2>{nom_logiciel} — Courrier Transmis</h2>
            </div>
            <div style="padding:20px">
              <p>Bonjour {user_name or 'utilisateur'},</p>
              <p>Un courrier vous a été transmis par <strong>{forwarded_by}</strong>.</p>
              <div style="background:#f8f9fa;padding:15px;border-radius:5px;margin:10px 0">
                <p><strong>N° Accusé :</strong> {courrier_data.get('numero_accuse_reception','N/A')}</p>
                <p><strong>Type :</strong> {courrier_data.get('type_courrier','N/A')}</p>
                <p><strong>Objet :</strong> {courrier_data.get('objet','N/A')}</p>
                <p><strong>Date :</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
              </div>
            </div>
          </div>
        </body></html>"""
        text_content = (
            f"{nom_logiciel} — Courrier transmis par {forwarded_by}\n"
            f"N° {courrier_data.get('numero_accuse_reception','N/A')} · "
            f"{courrier_data.get('objet','N/A')}"
        )

    return send_email_from_system_config(user_email, subject, html_content, text_content)


def send_comment_notification(
    user_email: str,
    courrier_data: dict,
    language: str = 'fr',
) -> bool:
    """Notifie un utilisateur qu'un commentaire/annotation/instruction a été ajouté sur un courrier."""
    if not user_email or not user_email.strip():
        return False

    from models import ParametresSysteme
    nom_logiciel = ParametresSysteme.get_valeur('nom_logiciel', 'GEC')

    comment_type = courrier_data.get('comment_type', 'commentaire')
    type_labels = {'comment': 'Commentaire', 'annotation': 'Annotation', 'instruction': 'Instruction'}
    type_label = type_labels.get(comment_type, 'Commentaire')
    added_by = courrier_data.get('added_by', 'Un utilisateur')
    comment_text = courrier_data.get('comment_text', '')

    subject = f"{type_label} ajouté — {courrier_data.get('numero_accuse_reception', 'N/A')}"
    html_content = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333">
      <div style="max-width:600px;margin:0 auto;padding:20px;border:1px solid #ddd;border-radius:8px">
        <div style="background:#6366f1;color:white;padding:20px;text-align:center;border-radius:6px 6px 0 0">
          <h2>{nom_logiciel} — Nouveau {type_label}</h2>
        </div>
        <div style="padding:20px">
          <p>Bonjour,</p>
          <p><strong>{added_by}</strong> a ajouté un {type_label.lower()} sur le courrier suivant&nbsp;:</p>
          <div style="background:#f8f9fa;padding:15px;border-radius:5px;margin:10px 0">
            <p><strong>N° Accusé :</strong> {courrier_data.get('numero_accuse_reception','N/A')}</p>
            <p><strong>Objet :</strong> {courrier_data.get('objet','N/A')}</p>
            <p><strong>{type_label} :</strong> {comment_text[:300]}{'...' if len(comment_text) > 300 else ''}</p>
            <p><strong>Date :</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
          </div>
        </div>
      </div>
    </body></html>"""
    text_content = (
        f"{nom_logiciel} — {type_label} par {added_by}\n"
        f"N° {courrier_data.get('numero_accuse_reception','N/A')} · "
        f"{courrier_data.get('objet','N/A')}\n"
        f"{comment_text[:200]}"
    )

    return send_email_from_system_config(user_email, subject, html_content, text_content)
