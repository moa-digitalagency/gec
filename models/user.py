from extensions import db
from flask_login import UserMixin
from datetime import datetime, timedelta
import os
from security.encryption import encrypt_sensitive_data, decrypt_sensitive_data

# ══════════════════════════════════════════════════════════════════════════════
# RÈGLE INVIOLABLE — NE PAS MODIFIER
# Le super_admin est un administrateur système (users, config, sécurité).
# Il n'a AUCUN accès aux courriers : ni lecture, ni création, ni modification.
# Cette règle est codée en dur et ne peut PAS être contournée via les rôles/permissions.
# Seuls les admin et users avec les permissions adéquates accèdent aux courriers.
# ══════════════════════════════════════════════════════════════════════════════
_SUPER_ADMIN_MAIL_BLOCKED_PERMISSIONS = frozenset({
    'read_all_mail', 'read_department_mail', 'read_own_mail',
    'edit_all_mail', 'edit_department_mail', 'edit_own_mail',
    'create_mail', 'delete_mail', 'restore_mail', 'manage_mail',
    'view_all_mail', 'bulk_mail', 'view_trash', 'permanent_delete',
})


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    nom_complet = db.Column(db.String(120), nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    actif = db.Column(db.Boolean, default=True, index=True)
    role = db.Column(db.String(20), nullable=False, default='user', index=True)
    langue = db.Column(db.String(5), nullable=False, default='fr')
    photo_profile = db.Column(db.String(255), nullable=True)
    departement_id = db.Column(db.Integer, db.ForeignKey('departement.id'), nullable=True, index=True)
    matricule = db.Column(db.String(50), nullable=True, unique=True)
    fonction = db.Column(db.String(200), nullable=True)

    # Données cryptées
    email_encrypted = db.Column(db.Text, nullable=True)
    nom_complet_encrypted = db.Column(db.Text, nullable=True)
    matricule_encrypted = db.Column(db.Text, nullable=True)
    fonction_encrypted = db.Column(db.Text, nullable=True)
    password_hash_encrypted = db.Column(db.Text, nullable=True)

    # Préférences notifications par email (in-app = toujours actif)
    notif_enabled      = db.Column(db.Boolean, default=True,      nullable=False)
    notif_new_mail     = db.Column(db.Boolean, default=True,      nullable=False)
    notif_forwarded    = db.Column(db.Boolean, default=True,      nullable=False)
    notif_status       = db.Column(db.Boolean, default=True,      nullable=False)
    notif_deadline     = db.Column(db.Boolean, default=True,      nullable=False)
    notif_commented    = db.Column(db.Boolean, default=False,     nullable=False)
    notif_digest       = db.Column(db.String(10), default='instant', nullable=False)
    # valeurs : 'instant' | 'daily' | 'weekly'

    # 2FA TOTP
    totp_secret = db.Column(db.String(64), nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False, nullable=False)
    totp_pending_secret = db.Column(db.String(64), nullable=True)

    # Relations
    courriers = db.relationship('Courrier', foreign_keys='Courrier.utilisateur_id', backref='utilisateur_enregistrement', lazy=True)
    logs = db.relationship('LogActivite', backref='utilisateur', lazy=True)
    departement = db.relationship('Departement', foreign_keys=[departement_id], backref='utilisateurs', lazy=True)

    def get_totp_uri(self, issuer='GEC-Courrier'):
        import pyotp
        return pyotp.totp.TOTP(self.totp_pending_secret or self.totp_secret).provisioning_uri(
            name=self.email, issuer_name=issuer
        )

    def verify_totp(self, token):
        import pyotp
        if not self.totp_enabled or not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        # valid_window=4 : tolère ±2 minutes de dérive d'horloge entre le
        # téléphone et le serveur (9 fenêtres de 30 s, soit ±120 s).
        return totp.verify(token, valid_window=4)

    def set_encrypted_email(self, email):
        self.email = email
        self.email_encrypted = encrypt_sensitive_data(email)

    def get_decrypted_email(self):
        if self.email_encrypted:
            try:
                return decrypt_sensitive_data(self.email_encrypted)
            except:
                return self.email
        return self.email

    def set_encrypted_nom_complet(self, nom_complet):
        self.nom_complet = nom_complet
        self.nom_complet_encrypted = encrypt_sensitive_data(nom_complet)

    def get_decrypted_nom_complet(self):
        if self.nom_complet_encrypted:
            try:
                return decrypt_sensitive_data(self.nom_complet_encrypted)
            except:
                return self.nom_complet
        return self.nom_complet

    def set_encrypted_password(self, password_hash):
        self.password_hash = password_hash
        self.password_hash_encrypted = encrypt_sensitive_data(password_hash)

    def get_decrypted_password_hash(self):
        if self.password_hash_encrypted:
            try:
                return decrypt_sensitive_data(self.password_hash_encrypted)
            except:
                return self.password_hash
        return self.password_hash

    def set_encrypted_matricule(self, matricule):
        if matricule:
            self.matricule = matricule
            self.matricule_encrypted = encrypt_sensitive_data(matricule)

    def get_decrypted_matricule(self):
        if self.matricule_encrypted:
            try:
                return decrypt_sensitive_data(self.matricule_encrypted)
            except:
                return self.matricule
        return self.matricule

    def set_encrypted_fonction(self, fonction):
        if fonction:
            self.fonction = fonction
            self.fonction_encrypted = encrypt_sensitive_data(fonction)

    def get_decrypted_fonction(self):
        if self.fonction_encrypted:
            try:
                return decrypt_sensitive_data(self.fonction_encrypted)
            except:
                return self.fonction
        return self.fonction

    def has_permission(self, permission):
        # RÈGLE INVIOLABLE : super_admin ne peut jamais avoir de permission sur les courriers
        if self.role == 'super_admin' and permission in _SUPER_ADMIN_MAIL_BLOCKED_PERMISSIONS:
            return False
        if self.role == 'super_admin':
            return True
        from models.rbac import Role
        role = Role.query.filter_by(nom=self.role).first()
        if role:
            return role.has_permission(permission)
        permissions = {
            'admin': ['manage_statuses', 'view_department', 'edit_department', 'read_department_mail', 'view_trash'],
            'user': ['view_own', 'edit_own', 'read_own_mail']
        }
        return permission in permissions.get(self.role, [])

    def is_super_admin(self):
        return self.role == 'super_admin'

    def is_admin(self):
        return self.role in ['super_admin', 'admin']

    def can_manage_users(self):
        return self.has_permission('manage_users')

    def can_access_courrier(self, courrier):
        if not self.actif:
            return False
        # RÈGLE INVIOLABLE : super_admin exclut
        if self.role == 'super_admin':
            return False
        # Propriétaire : accès à son propre courrier
        if courrier.utilisateur_id == self.id:
            return True
        # Destinataire d'une transmission : accès au courrier transmis
        from models.courrier import CourrierForward
        if CourrierForward.query.filter_by(courrier_id=courrier.id, forwarded_to_id=self.id).first():
            return True
        # Sinon, accès strictement selon les actions read_* assignées au rôle
        if self.has_permission('read_all_mail'):
            return True
        elif self.has_permission('read_department_mail') and self.departement_id:
            courrier_creator = User.query.get(courrier.utilisateur_id)
            if courrier_creator and courrier_creator.departement_id == self.departement_id:
                return True
        return False

    def can_view_courrier(self, courrier):
        # RÈGLE INVIOLABLE : super_admin ne consulte pas les courriers
        if self.role == 'super_admin':
            return False
        from models.courrier import CourrierForward
        forwarded_to_user = CourrierForward.query.filter_by(
            courrier_id=courrier.id,
            forwarded_to_id=self.id
        ).first()
        if forwarded_to_user:
            return True
        # Propriétaire : accès à son propre courrier
        if courrier.utilisateur_id == self.id:
            return True
        # Sinon, lecture strictement selon les actions read_* assignées au rôle
        if self.has_permission('read_all_mail'):
            return True
        elif self.has_permission('read_department_mail'):
            if self.departement_id is None:
                return False
            return self.departement_id == courrier.utilisateur_enregistrement.departement_id
        elif self.has_permission('read_own_mail'):
            return courrier.utilisateur_id == self.id
        # Aucune action read_* assignée : restreint (propriétaire/transmis déjà gérés ci-dessus)
        return False

    def can_edit_courrier(self, courrier):
        # RÈGLE INVIOLABLE : super_admin ne modifie pas les courriers
        if self.role == 'super_admin':
            return False
        if self.has_permission('edit_all_mail'):
            return True
        elif self.has_permission('edit_department_mail'):
            if hasattr(courrier, 'utilisateur_enregistrement') and courrier.utilisateur_enregistrement:
                return courrier.utilisateur_enregistrement.departement_id == self.departement_id
            return False
        elif self.has_permission('edit_own_mail'):
            return courrier.utilisateur_id == self.id
        # Propriétaire sans action d'édition : fenêtre de 24h après enregistrement
        if courrier.utilisateur_id == self.id:
            from datetime import datetime, timedelta
            time_limit = courrier.date_enregistrement + timedelta(hours=24)
            return datetime.now() <= time_limit
        return False

    def can_receive_new_mail_notifications(self):
        if not self.actif or not self.email:
            return False
        if self.role == 'super_admin':
            return True
        if self.has_permission('receive_new_mail_notifications'):
            return True
        elif self.has_permission('manage_mail') or self.has_permission('read_all_mail') or self.has_permission('read_department_mail'):
            return True
        return False

    def get_profile_photo_url(self):
        if self.photo_profile:
            profile_path = os.path.join('static/uploads/profiles', self.photo_profile)
            if os.path.exists(profile_path):
                return f'/static/uploads/profiles/{self.photo_profile}'
        return '/static/img/default-profile.svg'

    @staticmethod
    def init_super_admin():
        from werkzeug.security import generate_password_hash
        from app import db
        if User.query.count() > 0:
            super_admin = User.query.filter_by(role='super_admin').first()
            if not super_admin:
                first_user = User.query.order_by(User.id).first()
                if first_user:
                    first_user.role = 'super_admin'
                    db.session.commit()
                    print(f"Utilisateur {first_user.username} promu super admin")
            return
        super_admin = User(
            username=os.environ.get('FIRST_ADMIN_USERNAME', 'admin'),
            email=os.environ.get('FIRST_ADMIN_EMAIL', 'admin@gec.cd'),
            nom_complet='Super Administrateur',
            password_hash=generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'Admin2025!')),
            role='super_admin',
            langue='fr',
            actif=True
        )
        db.session.add(super_admin)
        try:
            db.session.commit()
            print("Super administrateur créé avec succès!")
        except Exception as e:
            db.session.rollback()
            print(f"Erreur lors de la création du super admin: {e}")
