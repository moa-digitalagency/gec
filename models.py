from app import db
from flask_login import UserMixin
from datetime import datetime
import uuid
import os

class Departement(db.Model):
    """Modèle pour les départements"""
    __tablename__ = 'departement'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    code = db.Column(db.String(10), unique=True, nullable=False)  # Code département (ex: RH, IT, FIN)
    chef_departement_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    chef_departement = db.relationship('User', foreign_keys=[chef_departement_id], backref='departement_chef', post_update=True)
    
    def __repr__(self):
        return f'<Departement {self.nom}>'
    
    @staticmethod
    def get_departements_actifs():
        """Récupère la liste des départements actifs"""
        return Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
    
    @staticmethod
    def init_default_departments():
        """Initialise les départements par défaut"""
        from app import db
        
        # Vérifier si des départements existent déjà
        if Departement.query.count() > 0:
            return
        
        departements_defaut = [
            {'nom': 'Administration Générale', 'code': 'ADM', 'description': 'Administration générale et ressources humaines'},
            {'nom': 'Département Juridique', 'code': 'JUR', 'description': 'Affaires juridiques et contentieux'},
            {'nom': 'Département Technique', 'code': 'TECH', 'description': 'Études techniques et supervision'},
            {'nom': 'Département Financier', 'code': 'FIN', 'description': 'Gestion financière et comptabilité'},
            {'nom': 'Secrétariat Général', 'code': 'SG', 'description': 'Secrétariat général et courrier'},
        ]
        
        for dept_data in departements_defaut:
            departement = Departement(**dept_data)
            db.session.add(departement)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Erreur lors de l'initialisation des départements: {e}")

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    nom_complet = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    actif = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), nullable=False, default='user')
    langue = db.Column(db.String(5), nullable=False, default='fr')
    photo_profile = db.Column(db.String(255), nullable=True)  # Chemin vers la photo de profil
    departement_id = db.Column(db.Integer, db.ForeignKey('departement.id'), nullable=True)
    matricule = db.Column(db.String(50), nullable=True)  # Matricule de l'employé
    fonction = db.Column(db.String(200), nullable=True)  # Fonction/poste de l'employé
    
    # Relations
    courriers = db.relationship('Courrier', foreign_keys='Courrier.utilisateur_id', backref='utilisateur_enregistrement', lazy=True)
    logs = db.relationship('LogActivite', backref='utilisateur', lazy=True)
    departement = db.relationship('Departement', foreign_keys=[departement_id], backref='utilisateurs', lazy=True)
    
    def has_permission(self, permission):
        """Vérifie si l'utilisateur a une permission spécifique"""
        # Obtenir le rôle de l'utilisateur
        role = Role.query.filter_by(nom=self.role).first()
        if role:
            return role.has_permission(permission)
        
        # Fallback sur l'ancien système si pas de rôle en base
        permissions = {
            'super_admin': ['manage_users', 'manage_system', 'manage_statuses', 'manage_departments', 'view_all', 'edit_all', 'read_all_mail'],
            'admin': ['manage_statuses', 'view_department', 'edit_department', 'read_department_mail'],
            'user': ['view_own', 'edit_own', 'read_own_mail']
        }
        return permission in permissions.get(self.role, [])
    
    def is_super_admin(self):
        """Vérifie si l'utilisateur est super administrateur"""
        return self.role == 'super_admin'
    
    def is_admin(self):
        """Vérifie si l'utilisateur est administrateur"""
        return self.role in ['super_admin', 'admin']
    
    def can_manage_users(self):
        """Vérifie si l'utilisateur peut gérer les utilisateurs"""
        return self.role == 'super_admin'
    
    def can_view_courrier(self, courrier):
        """Vérifie si l'utilisateur peut voir ce courrier"""
        # Vérifier les permissions spécifiques aux courriers
        if self.has_permission('read_all_mail'):
            return True
        elif self.has_permission('read_department_mail'):
            # Peut voir les courriers de son département
            if self.departement_id is None:
                return courrier.utilisateur_id == self.id
            return self.departement_id == courrier.utilisateur_enregistrement.departement_id
        elif self.has_permission('read_own_mail'):
            # Peut voir seulement ses propres courriers
            return courrier.utilisateur_id == self.id
        else:
            # Fallback sur l'ancien système si pas de permissions spécifiques
            if self.role == 'super_admin':
                return True
            elif self.role == 'admin':
                # Admin peut voir les courriers de son département
                if self.departement_id is None:
                    return courrier.utilisateur_id == self.id
                return self.departement_id == courrier.utilisateur_enregistrement.departement_id
            else:
                # Utilisateur peut voir seulement ses propres courriers
                return courrier.utilisateur_id == self.id
    
    def get_profile_photo_url(self):
        """Retourne l'URL de la photo de profil ou une image par défaut"""
        if self.photo_profile:
            # Essayer d'abord le dossier uploads/profiles
            profile_path = os.path.join('uploads/profiles', self.photo_profile)
            if os.path.exists(profile_path):
                return f'/static/uploads/profiles/{self.photo_profile}'
            # Sinon essayer le dossier static/uploads/profiles  
            static_path = os.path.join('static/uploads/profiles', self.photo_profile)
            if os.path.exists(static_path):
                return f'/static/uploads/profiles/{self.photo_profile}'
        return '/static/images/default-profile.svg'

class Courrier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_accuse_reception = db.Column(db.String(50), unique=True, nullable=False)
    numero_reference = db.Column(db.String(100), nullable=True)
    objet = db.Column(db.Text, nullable=False)
    type_courrier = db.Column(db.String(20), nullable=False, default='ENTRANT')  # ENTRANT ou SORTANT
    expediteur = db.Column(db.String(200), nullable=True)  # Pour courrier entrant
    destinataire = db.Column(db.String(200), nullable=True)  # Pour courrier sortant
    date_redaction = db.Column(db.Date, nullable=True)  # Date de rédaction de la lettre
    date_enregistrement = db.Column(db.DateTime, default=datetime.utcnow)
    fichier_nom = db.Column(db.String(255), nullable=True)
    fichier_chemin = db.Column(db.String(500), nullable=True)
    fichier_type = db.Column(db.String(50), nullable=True)
    statut = db.Column(db.String(50), nullable=False, default='RECU')
    date_modification_statut = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Clé étrangère
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    modifie_par_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    modifie_par = db.relationship('User', foreign_keys=[modifie_par_id], backref='courriers_modifies')
    
    def __repr__(self):
        return f'<Courrier {self.numero_accuse_reception}>'
    
    @property
    def reference_display(self):
        return self.numero_reference if self.numero_reference else "Non référencé"
    
    def get_contact_principal(self):
        """Retourne l'expéditeur ou le destinataire selon le type"""
        if self.type_courrier == 'ENTRANT':
            return self.expediteur
        else:
            return self.destinataire
    
    def get_label_contact(self):
        """Retourne le label du contact selon le type"""
        if self.type_courrier == 'ENTRANT':
            return "Expéditeur"
        else:
            return "Destinataire"
    
    def get_type_display(self):
        """Affichage formaté du type de courrier"""
        return "Courrier Entrant" if self.type_courrier == 'ENTRANT' else "Courrier Sortant"
    
    def get_type_color(self):
        """Couleur associée au type de courrier"""
        if self.type_courrier == 'ENTRANT':
            return 'bg-blue-100 text-blue-800'
        else:
            return 'bg-green-100 text-green-800'
    
    @property
    def statut_color(self):
        """Retourne la couleur associée au statut"""
        colors = {
            'RECU': 'bg-blue-100 text-blue-800',
            'EN_COURS': 'bg-yellow-100 text-yellow-800',
            'TRAITE': 'bg-green-100 text-green-800',
            'ARCHIVE': 'bg-gray-100 text-gray-800',
            'URGENT': 'bg-red-100 text-red-800'
        }
        return colors.get(self.statut, 'bg-gray-100 text-gray-800')

class LogActivite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date_action = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)
    
    # Clé étrangère
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    courrier_id = db.Column(db.Integer, db.ForeignKey('courrier.id'), nullable=True)
    
    def __repr__(self):
        return f'<LogActivite {self.action} by {self.utilisateur.username}>'

class ParametresSysteme(db.Model):
    """Paramètres de configuration du système"""
    id = db.Column(db.Integer, primary_key=True)
    nom_logiciel = db.Column(db.String(100), nullable=False, default="GEC - Mines RDC")
    logo_url = db.Column(db.String(500), nullable=True)
    format_numero_accuse = db.Column(db.String(50), nullable=False, default="GEC-{year}-{counter:05d}")
    adresse_organisme = db.Column(db.Text, nullable=True)
    telephone = db.Column(db.String(20), nullable=True)
    email_contact = db.Column(db.String(120), nullable=True)
    
    # Paramètres footer
    texte_footer = db.Column(db.Text, nullable=True, default="Système de Gestion Électronique du Courrier")
    copyright_crypte = db.Column(db.String(500), nullable=False, default="")  # Copyright crypté
    
    # Paramètres PDF
    logo_pdf = db.Column(db.String(500), nullable=True)  # Logo spécifique pour PDF
    titre_pdf = db.Column(db.String(200), nullable=True, default="Ministère des Mines")
    sous_titre_pdf = db.Column(db.String(200), nullable=True, default="Secrétariat Général")
    
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Clé étrangère pour tracer qui a modifié
    modifie_par_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    modifie_par = db.relationship('User', backref='parametres_modifies')
    
    def __repr__(self):
        return f'<ParametresSysteme {self.nom_logiciel}>'
    
    def get_copyright_decrypte(self):
        """Décrypte et retourne le copyright"""
        import base64
        try:
            if self.copyright_crypte:
                return base64.b64decode(self.copyright_crypte.encode()).decode('utf-8')
            else:
                return "© 2025 GEC. Made with 💖 and ☕  By MOA-Digital Agency LLC"
        except:
            return "© 2025 GEC. Made with 💖 and ☕  By MOA-Digital Agency LLC"
    
    def set_copyright_crypte(self, copyright_text):
        """Crypte et sauvegarde le copyright"""
        import base64
        self.copyright_crypte = base64.b64encode(copyright_text.encode()).decode('utf-8')
    
    @staticmethod
    def get_parametres():
        """Récupère les paramètres système ou crée des valeurs par défaut"""
        parametres = ParametresSysteme.query.first()
        if not parametres:
            parametres = ParametresSysteme()
            # Initialiser le copyright crypté par défaut
            parametres.set_copyright_crypte("© 2025 GEC. Made with 💖 and ☕  By MOA-Digital Agency LLC")
            db.session.add(parametres)
            db.session.commit()
        elif not parametres.copyright_crypte:
            # Si pas de copyright crypté, l'initialiser
            parametres.set_copyright_crypte("© 2025 GEC. Made with 💖 and ☕  By MOA-Digital Agency LLC")
            db.session.commit()
        return parametres

class StatutCourrier(db.Model):
    """Statuts possibles pour les courriers"""
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    couleur = db.Column(db.String(50), nullable=False, default='bg-gray-100 text-gray-800')
    actif = db.Column(db.Boolean, default=True)
    ordre = db.Column(db.Integer, default=0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<StatutCourrier {self.nom}>'
    
    @staticmethod
    def get_statuts_actifs():
        """Récupère la liste des statuts actifs triés par ordre"""
        return StatutCourrier.query.filter_by(actif=True).order_by(StatutCourrier.ordre).all()
    
    @staticmethod
    def init_default_statuts():
        """Initialise les statuts par défaut"""
        statuts_default = [
            {'nom': 'RECU', 'description': 'Courrier reçu', 'couleur': 'bg-blue-100 text-blue-800', 'ordre': 1},
            {'nom': 'EN_COURS', 'description': 'En cours de traitement', 'couleur': 'bg-yellow-100 text-yellow-800', 'ordre': 2},
            {'nom': 'TRAITE', 'description': 'Traité', 'couleur': 'bg-green-100 text-green-800', 'ordre': 3},
            {'nom': 'ARCHIVE', 'description': 'Archivé', 'couleur': 'bg-gray-100 text-gray-800', 'ordre': 4},
            {'nom': 'URGENT', 'description': 'Urgent', 'couleur': 'bg-red-100 text-red-800', 'ordre': 0}
        ]
        
        for statut_data in statuts_default:
            existing = StatutCourrier.query.filter_by(nom=statut_data['nom']).first()
            if not existing:
                statut = StatutCourrier(**statut_data)
                db.session.add(statut)
        
        try:
            db.session.commit()
        except:
            db.session.rollback()


class Role(db.Model):
    """Rôles personnalisés du système"""
    __tablename__ = 'role'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), unique=True, nullable=False)
    nom_affichage = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    couleur = db.Column(db.String(50), nullable=False, default='bg-gray-100 text-gray-800')
    icone = db.Column(db.String(50), nullable=False, default='fas fa-user')
    actif = db.Column(db.Boolean, default=True)
    modifiable = db.Column(db.Boolean, default=True)  # Les rôles système ne sont pas modifiables
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    cree_par_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    cree_par = db.relationship('User', foreign_keys=[cree_par_id], backref='roles_crees')
    
    permissions = db.relationship('RolePermission', backref='role', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Role {self.nom}>'
    
    def has_permission(self, permission_nom):
        """Vérifie si le rôle a une permission spécifique"""
        return any(p.permission_nom == permission_nom for p in self.permissions)
    
    def get_permissions_list(self):
        """Retourne la liste des noms de permissions"""
        return [p.permission_nom for p in self.permissions]
    
    @staticmethod
    def init_default_roles():
        """Initialise les rôles par défaut"""
        from app import db
        
        # Vérifier si des rôles existent déjà
        if Role.query.count() > 0:
            return
        
        roles_defaut = [
            {
                'nom': 'super_admin',
                'nom_affichage': 'Super Administrateur',
                'description': 'Accès complet au système avec toutes les permissions',
                'couleur': 'bg-yellow-100 text-yellow-800',
                'icone': 'fas fa-crown',
                'modifiable': False
            },
            {
                'nom': 'admin',
                'nom_affichage': 'Administrateur',
                'description': 'Gestion des utilisateurs et configuration système limitée',
                'couleur': 'bg-blue-100 text-blue-800',
                'icone': 'fas fa-shield-alt',
                'modifiable': True
            },
            {
                'nom': 'user',
                'nom_affichage': 'Utilisateur',
                'description': 'Accès de base pour enregistrer et consulter les courriers',
                'couleur': 'bg-gray-100 text-gray-800',
                'icone': 'fas fa-user',
                'modifiable': True
            }
        ]
        
        for role_data in roles_defaut:
            role = Role(**role_data)
            db.session.add(role)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Erreur lors de l'initialisation des rôles: {e}")


class RolePermission(db.Model):
    """Permissions associées aux rôles"""
    __tablename__ = 'role_permission'
    
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    permission_nom = db.Column(db.String(100), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    accorde_par_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    accorde_par = db.relationship('User', backref='permissions_accordees')
    
    def __repr__(self):
        return f'<RolePermission {self.permission_nom} pour {self.role.nom}>'
    
    @staticmethod
    def init_default_permissions():
        """Initialise les permissions par défaut"""
        from app import db
        
        # Vérifier si des permissions existent déjà
        if RolePermission.query.count() > 0:
            return
        
        # Permissions par rôle
        permissions_defaut = {
            'super_admin': [
                'manage_users', 'manage_roles', 'manage_system_settings', 
                'view_all_logs', 'manage_statuses', 'manage_departments',
                'register_mail', 'view_mail', 'search_mail', 'export_data', 
                'delete_mail', 'view_all', 'edit_all', 'read_all_mail'
            ],
            'admin': [
                'manage_statuses', 'register_mail', 'view_mail', 
                'search_mail', 'export_data', 'manage_system_settings',
                'view_department', 'edit_department', 'read_department_mail'
            ],
            'user': [
                'register_mail', 'view_mail', 'search_mail', 'export_data',
                'view_own', 'edit_own', 'read_own_mail'
            ]
        }
        
        for role_nom, perms in permissions_defaut.items():
            role = Role.query.filter_by(nom=role_nom).first()
            if role:
                for perm_nom in perms:
                    permission = RolePermission(role_id=role.id, permission_nom=perm_nom)
                    db.session.add(permission)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Erreur lors de l'initialisation des permissions: {e}")


# Fonction d'initialisation globale
def init_default_data():
    """Initialise toutes les données par défaut"""
    StatutCourrier.init_default_statuts()
    Role.init_default_roles()
    RolePermission.init_default_permissions()
    Departement.init_default_departments()
