from app import db
from flask_login import UserMixin
from datetime import datetime
import uuid

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
    
    # Relations
    courriers = db.relationship('Courrier', foreign_keys='Courrier.utilisateur_id', backref='utilisateur_enregistrement', lazy=True)
    logs = db.relationship('LogActivite', backref='utilisateur', lazy=True)
    
    def has_permission(self, permission):
        """Vérifie si l'utilisateur a une permission spécifique"""
        permissions = {
            'super_admin': ['manage_users', 'manage_system', 'manage_statuses', 'view_all', 'edit_all'],
            'admin': ['manage_statuses', 'view_all', 'edit_all'],
            'user': ['view_own', 'edit_own']
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

class Courrier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_accuse_reception = db.Column(db.String(50), unique=True, nullable=False)
    numero_reference = db.Column(db.String(100), nullable=True)
    objet = db.Column(db.Text, nullable=False)
    expediteur = db.Column(db.String(200), nullable=False)
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
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Clé étrangère pour tracer qui a modifié
    modifie_par_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    modifie_par = db.relationship('User', backref='parametres_modifies')
    
    def __repr__(self):
        return f'<ParametresSysteme {self.nom_logiciel}>'
    
    @staticmethod
    def get_parametres():
        """Récupère les paramètres système ou crée des valeurs par défaut"""
        parametres = ParametresSysteme.query.first()
        if not parametres:
            parametres = ParametresSysteme()
            db.session.add(parametres)
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
