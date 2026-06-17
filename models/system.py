from extensions import db
from datetime import datetime, timedelta
import logging


class ParametresSysteme(db.Model):
    """Paramètres de configuration du système"""
    id = db.Column(db.Integer, primary_key=True)
    nom_logiciel = db.Column(db.String(100), nullable=False, default="GEC - Gestion du Courrier")
    logo_url = db.Column(db.String(500), nullable=True)

    mode_numero_accuse = db.Column(db.String(20), nullable=False, default="automatique")
    format_numero_accuse = db.Column(db.String(50), nullable=False, default="GEC-{year}-{counter:05d}")

    adresse_organisme = db.Column(db.Text, nullable=True)
    telephone = db.Column(db.String(20), nullable=True)
    email_contact = db.Column(db.String(120), nullable=True)

    texte_footer = db.Column(db.Text, nullable=True, default="Système de Gestion Électronique du Courrier")
    copyright_crypte = db.Column(db.String(500), nullable=False, default="")

    logo_pdf = db.Column(db.String(500), nullable=True)
    titre_pdf = db.Column(db.String(200), nullable=True, default="Secrétariat Général")
    sous_titre_pdf = db.Column(db.String(200), nullable=True, default="Secrétariat Général")
    pays_pdf = db.Column(db.String(200), nullable=True, default="République Démocratique du Congo")
    copyright_text = db.Column(db.Text, nullable=True, default="© 2025 GEC. Made with love and coffee by MOA-Digital Agency LLC")

    smtp_server = db.Column(db.String(200), nullable=True)
    smtp_port = db.Column(db.Integer, nullable=True, default=587)
    smtp_use_tls = db.Column(db.Boolean, nullable=False, default=True)
    smtp_username = db.Column(db.String(200), nullable=True)
    smtp_password = db.Column(db.String(500), nullable=True)

    appellation_departement = db.Column(db.String(100), nullable=False, default="Départements")
    titre_responsable_structure = db.Column(db.String(100), nullable=False, default="Secrétaire Général")

    email_provider = db.Column(db.String(20), nullable=False, default="resend")
    resend_api_key = db.Column(db.String(500), nullable=True)

    notify_superadmin_new_mail = db.Column(db.Boolean, nullable=False, default=True)
    whatsapp_number = db.Column(db.String(20), nullable=True, default='243860493345')

    # Paramètres notification globaux
    notifications_enabled  = db.Column(db.Boolean, default=True, nullable=False)
    notif_default_digest   = db.Column(db.String(10), default='instant', nullable=False)
    notif_types_enabled    = db.Column(db.Text, nullable=True)
    # JSON list ex: ["new_mail","mail_forwarded","mail_status_changed","mail_deadline","mail_commented"]

    # Sécurité & sessions (configurable en UI — Paramètres → Sécurité)
    session_idle_timeout_min = db.Column(db.Integer, nullable=False, default=15)   # déconnexion après X min d'inactivité
    session_lifetime_days    = db.Column(db.Integer, nullable=False, default=7)    # durée max d'une session (jours)
    max_upload_mb            = db.Column(db.Integer, nullable=False, default=100)  # taille max d'un fichier (Mo)
    courrier_edit_window_h   = db.Column(db.Integer, nullable=False, default=24)   # délai d'édition d'un courrier par son créateur (heures)
    reminder_interval_h      = db.Column(db.Integer, nullable=False, default=6)    # intervalle des rappels d'échéance (heures)

    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    modifie_par_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    modifie_par = db.relationship('User', backref='parametres_modifies')

    def __repr__(self):
        return f'<ParametresSysteme {self.nom_logiciel}>'

    def get_copyright_decrypte(self):
        import base64
        try:
            if self.copyright_text:
                return self.copyright_text
            elif self.copyright_crypte:
                return base64.b64decode(self.copyright_crypte.encode()).decode('utf-8')
            else:
                return "© 2025 GEC. Made with love and coffee by MOA-Digital Agency LLC"
        except:
            return "© 2025 GEC. Made with love and coffee by MOA-Digital Agency LLC"

    def set_copyright_crypte(self, copyright_text):
        import base64
        self.copyright_crypte = base64.b64encode(copyright_text.encode()).decode('utf-8')

    def get_smtp_password_decrypted(self):
        if not self.smtp_password:
            return None
        try:
            from security.auth import decrypt_data
            return decrypt_data(self.smtp_password)
        except Exception as e:
            logging.error(f"Erreur lors du décryptage du mot de passe SMTP: {e}")
            return None

    def get_resend_api_key(self):
        return self.resend_api_key if self.resend_api_key else None

    @staticmethod
    def get_parametres():
        parametres = ParametresSysteme.query.first()
        if not parametres:
            parametres = ParametresSysteme()
            parametres.copyright_text = "© 2025 GEC. Made with love and coffee by MOA-Digital Agency LLC"
            parametres.pays_pdf = "République Démocratique du Congo"
            parametres.set_copyright_crypte("© 2025 GEC. Made with love and coffee by MOA-Digital Agency LLC")
            db.session.add(parametres)
            db.session.commit()
        elif not parametres.copyright_text:
            parametres.copyright_text = "© 2025 GEC. Made with love and coffee by MOA-Digital Agency LLC"
            if not parametres.pays_pdf:
                parametres.pays_pdf = "République Démocratique du Congo"
            db.session.commit()
        return parametres

    @staticmethod
    def get_valeur(param_name, default_value=None):
        parametres = ParametresSysteme.get_parametres()
        if param_name == 'smtp_password':
            return parametres.get_smtp_password_decrypted()
        elif param_name == 'smtp_email':
            return parametres.smtp_username
        elif param_name == 'smtp_use_tls':
            return str(parametres.smtp_use_tls).lower() if parametres.smtp_use_tls is not None else default_value
        if hasattr(parametres, param_name):
            value = getattr(parametres, param_name)
            return value if value is not None else default_value
        return default_value


class EmailTemplate(db.Model):
    """Templates d'email pour les notifications multi-langues"""
    __tablename__ = 'email_template'

    id = db.Column(db.Integer, primary_key=True)
    type_template = db.Column(db.String(50), nullable=False)
    langue = db.Column(db.String(5), nullable=False, default='fr')

    sujet = db.Column(db.String(200), nullable=False)
    contenu_html = db.Column(db.Text, nullable=False)
    contenu_texte = db.Column(db.Text, nullable=True)

    actif = db.Column(db.Boolean, nullable=False, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cree_par_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    modifie_par_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    cree_par = db.relationship('User', foreign_keys=[cree_par_id], backref='templates_crees')
    modifie_par = db.relationship('User', foreign_keys=[modifie_par_id], backref='templates_modifies')

    __table_args__ = (
        db.UniqueConstraint('type_template', 'langue', name='unique_template_lang'),
    )

    def __repr__(self):
        return f'<EmailTemplate {self.type_template}:{self.langue}>'

    @staticmethod
    def get_template(type_template, langue='fr'):
        template = EmailTemplate.query.filter_by(
            type_template=type_template,
            langue=langue,
            actif=True
        ).first()
        if not template and langue != 'fr':
            template = EmailTemplate.query.filter_by(
                type_template=type_template,
                langue='fr',
                actif=True
            ).first()
        return template

    @staticmethod
    def init_default_templates():
        try:
            if not EmailTemplate.query.filter_by(type_template='new_mail', langue='fr').first():
                template_fr = EmailTemplate(
                    type_template='new_mail',
                    langue='fr',
                    sujet='Nouveau courrier enregistré - {{numero_accuse_reception}}',
                    contenu_html='''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .header { background-color: #003087; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .details { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .footer { background-color: #f1f1f1; padding: 10px; text-align: center; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h2>GEC - Notification de Nouveau Courrier</h2>
    </div>
    <div class="content">
        <p>Bonjour,</p>
        <p>Un nouveau courrier a été enregistré dans le système GEC.</p>
        <div class="details">
            <h3>Détails du courrier :</h3>
            <p><strong>Numéro d\'accusé de réception :</strong> {{numero_accuse_reception}}</p>
            <p><strong>Type :</strong> {{type_courrier}}</p>
            <p><strong>Objet :</strong> {{objet}}</p>
            <p><strong>Expéditeur :</strong> {{expediteur}}</p>
            <p><strong>Date d\'enregistrement :</strong> {{date_enregistrement}}</p>
            <p><strong>Enregistré par :</strong> {{created_by}}</p>
        </div>
        <p>Vous pouvez consulter ce courrier en vous connectant au système GEC.</p>
    </div>
    <div class="footer">
        <p>GEC - Système de Gestion du Courrier<br>
        Secrétariat Général - République Démocratique du Congo</p>
    </div>
</body>
</html>''',
                    contenu_texte='''GEC - Notification de Nouveau Courrier

Un nouveau courrier a été enregistré dans le système.

Détails du courrier :
- Numéro d\'accusé de réception : {{numero_accuse_reception}}
- Type : {{type_courrier}}
- Objet : {{objet}}
- Expéditeur : {{expediteur}}
- Date d\'enregistrement : {{date_enregistrement}}
- Enregistré par : {{created_by}}

Connectez-vous au système GEC pour consulter ce courrier.

GEC - Système de Gestion du Courrier
Secrétariat Général - République Démocratique du Congo''',
                    cree_par_id=1
                )
                db.session.add(template_fr)

            if not EmailTemplate.query.filter_by(type_template='mail_forwarded', langue='fr').first():
                template_forward_fr = EmailTemplate(
                    type_template='mail_forwarded',
                    langue='fr',
                    sujet='Courrier transmis - {{numero_accuse_reception}}',
                    contenu_html='''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .header { background-color: #009639; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .details { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .footer { background-color: #f1f1f1; padding: 10px; text-align: center; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h2>GEC - Courrier Transmis</h2>
    </div>
    <div class="content">
        <p>Bonjour,</p>
        <p>Un courrier vous a été transmis par <strong>{{transmis_par}}</strong>.</p>
        <div class="details">
            <h3>Détails du courrier :</h3>
            <p><strong>Numéro d\'accusé de réception :</strong> {{numero_courrier}}</p>
            <p><strong>Type :</strong> {{type_courrier}}</p>
            <p><strong>Objet :</strong> {{objet}}</p>
            <p><strong>Expéditeur :</strong> {{expediteur}}</p>
            <p><strong>Date de transmission :</strong> {{date_reception}}</p>
        </div>
        <p>Veuillez vous connecter au système GEC pour consulter ce courrier.</p>
    </div>
    <div class="footer">
        <p>GEC - Système de Gestion du Courrier<br>
        Secrétariat Général - République Démocratique du Congo</p>
    </div>
</body>
</html>''',
                    contenu_texte='''GEC - Courrier Transmis

Un courrier vous a été transmis par {{transmis_par}}.

Détails du courrier :
- Numéro d\'accusé de réception : {{numero_courrier}}
- Type : {{type_courrier}}
- Objet : {{objet}}
- Expéditeur : {{expediteur}}
- Date de transmission : {{date_reception}}

Connectez-vous au système GEC pour consulter ce courrier.

GEC - Système de Gestion du Courrier
Secrétariat Général - République Démocratique du Congo''',
                    cree_par_id=1
                )
                db.session.add(template_forward_fr)

            db.session.commit()
        except Exception as e:
            print(f"Erreur lors de l'initialisation des templates email: {e}")
            db.session.rollback()


class IPBlock(db.Model):
    """Model for storing blocked IP addresses"""
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False, unique=True, index=True)
    reason = db.Column(db.String(200), nullable=False)
    blocked_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_by = db.Column(db.String(100), default='system')
    is_active = db.Column(db.Boolean, default=True, index=True)

    @staticmethod
    def is_ip_blocked(ip_address):
        now = datetime.utcnow()
        block = IPBlock.query.filter_by(
            ip_address=ip_address,
            is_active=True
        ).filter(IPBlock.expires_at > now).first()
        return block is not None

    @staticmethod
    def block_ip(ip_address, duration_minutes=30, reason="Suspicious activity"):
        from app import db
        IPBlock.query.filter_by(ip_address=ip_address).delete()
        expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
        new_block = IPBlock(
            ip_address=ip_address,
            reason=reason,
            expires_at=expires_at
        )
        db.session.add(new_block)
        db.session.commit()
        return new_block

    @staticmethod
    def cleanup_expired_blocks():
        from app import db
        now = datetime.utcnow()
        expired_count = IPBlock.query.filter(IPBlock.expires_at <= now).delete()
        db.session.commit()
        return expired_count

    @staticmethod
    def unblock_ip(ip_address):
        from app import db
        unblocked_count = IPBlock.query.filter_by(ip_address=ip_address, is_active=True).update({
            'is_active': False
        })
        db.session.commit()
        return unblocked_count > 0

    @staticmethod
    def unblock_all_ips():
        from app import db
        unblocked_count = IPBlock.query.filter_by(is_active=True).update({
            'is_active': False
        })
        db.session.commit()
        return unblocked_count

    @staticmethod
    def get_blocked_ips():
        now = datetime.utcnow()
        return IPBlock.query.filter_by(is_active=True).filter(
            IPBlock.expires_at > now
        ).all()

    def __repr__(self):
        return f'<IPBlock {self.ip_address} until {self.expires_at}>'


class IPWhitelist(db.Model):
    """Model for storing whitelisted IP addresses"""
    __tablename__ = 'ip_whitelist'

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False, unique=True, index=True)
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_by = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True, index=True)

    @staticmethod
    def is_ip_whitelisted(ip_address):
        whitelist_entry = IPWhitelist.query.filter_by(
            ip_address=ip_address,
            is_active=True
        ).first()
        return whitelist_entry is not None

    @staticmethod
    def add_to_whitelist(ip_address, description="", created_by="system"):
        from app import db
        existing = IPWhitelist.query.filter_by(ip_address=ip_address).first()
        if existing:
            existing.is_active = True
            existing.description = description
            existing.created_by = created_by
        else:
            new_whitelist = IPWhitelist(
                ip_address=ip_address,
                description=description,
                created_by=created_by
            )
            db.session.add(new_whitelist)
        IPBlock.unblock_ip(ip_address)
        db.session.commit()
        return True

    @staticmethod
    def remove_from_whitelist(ip_address):
        from app import db
        removed_count = IPWhitelist.query.filter_by(ip_address=ip_address).update({
            'is_active': False
        })
        db.session.commit()
        return removed_count > 0

    @staticmethod
    def get_whitelisted_ips():
        return IPWhitelist.query.filter_by(is_active=True).order_by(IPWhitelist.created_at.desc()).all()

    def __repr__(self):
        return f'<IPWhitelist {self.ip_address}>'
