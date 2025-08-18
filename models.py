from app import db
from flask_login import UserMixin
from datetime import datetime
import uuid
import os
from encryption_utils import encryption_manager, encrypt_sensitive_data, decrypt_sensitive_data
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
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    nom_complet = db.Column(db.String(120), nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    actif = db.Column(db.Boolean, default=True, index=True)
    role = db.Column(db.String(20), nullable=False, default='user', index=True)
    langue = db.Column(db.String(5), nullable=False, default='fr')
    photo_profile = db.Column(db.String(255), nullable=True)  # Chemin vers la photo de profil
    departement_id = db.Column(db.Integer, db.ForeignKey('departement.id'), nullable=True, index=True)
    matricule = db.Column(db.String(50), nullable=True, unique=True)  # Matricule de l'employé
    fonction = db.Column(db.String(200), nullable=True)  # Fonction/poste de l'employé
    
    # Données cryptées (nouvelles colonnes pour les données sensibles)
    email_encrypted = db.Column(db.Text, nullable=True)  # Email crypté
    nom_complet_encrypted = db.Column(db.Text, nullable=True)  # Nom complet crypté
    matricule_encrypted = db.Column(db.Text, nullable=True)  # Matricule crypté
    fonction_encrypted = db.Column(db.Text, nullable=True)  # Fonction cryptée
    password_hash_encrypted = db.Column(db.Text, nullable=True)  # Hash de mot de passe crypté
    

    
    # Relations
    courriers = db.relationship('Courrier', foreign_keys='Courrier.utilisateur_id', backref='utilisateur_enregistrement', lazy=True)
    logs = db.relationship('LogActivite', backref='utilisateur', lazy=True)
    departement = db.relationship('Departement', foreign_keys=[departement_id], backref='utilisateurs', lazy=True)
    
    def set_encrypted_email(self, email):
        """Définit l'email crypté"""
        self.email = email  # Garde aussi en clair pour la compatibilité
        self.email_encrypted = encrypt_sensitive_data(email)
    
    def get_decrypted_email(self):
        """Récupère l'email décrypté"""
        if self.email_encrypted:
            try:
                return decrypt_sensitive_data(self.email_encrypted)
            except:
                return self.email  # Fallback vers l'email en clair
        return self.email
    
    def set_encrypted_nom_complet(self, nom_complet):
        """Définit le nom complet crypté"""
        self.nom_complet = nom_complet  # Garde aussi en clair pour la compatibilité
        self.nom_complet_encrypted = encrypt_sensitive_data(nom_complet)
    
    def get_decrypted_nom_complet(self):
        """Récupère le nom complet décrypté"""
        if self.nom_complet_encrypted:
            try:
                return decrypt_sensitive_data(self.nom_complet_encrypted)
            except:
                return self.nom_complet  # Fallback vers le nom en clair
        return self.nom_complet
    
    def set_encrypted_password(self, password_hash):
        """Définit le hash de mot de passe crypté"""
        self.password_hash = password_hash  # Garde aussi en clair pour la compatibilité
        self.password_hash_encrypted = encrypt_sensitive_data(password_hash)
    
    def get_decrypted_password_hash(self):
        """Récupère le hash de mot de passe décrypté"""
        if self.password_hash_encrypted:
            try:
                return decrypt_sensitive_data(self.password_hash_encrypted)
            except:
                return self.password_hash  # Fallback vers le hash en clair
        return self.password_hash
    
    def set_encrypted_matricule(self, matricule):
        """Définit le matricule crypté"""
        if matricule:
            self.matricule = matricule  # Garde aussi en clair pour la compatibilité
            self.matricule_encrypted = encrypt_sensitive_data(matricule)
    
    def get_decrypted_matricule(self):
        """Récupère le matricule décrypté"""
        if self.matricule_encrypted:
            try:
                return decrypt_sensitive_data(self.matricule_encrypted)
            except:
                return self.matricule  # Fallback vers le matricule en clair
        return self.matricule
    
    def set_encrypted_fonction(self, fonction):
        """Définit la fonction cryptée"""
        if fonction:
            self.fonction = fonction  # Garde aussi en clair pour la compatibilité
            self.fonction_encrypted = encrypt_sensitive_data(fonction)
    
    def get_decrypted_fonction(self):
        """Récupère la fonction décryptée"""
        if self.fonction_encrypted:
            try:
                return decrypt_sensitive_data(self.fonction_encrypted)
            except:
                return self.fonction  # Fallback vers la fonction en clair
        return self.fonction

    
    def has_permission(self, permission):
        """Vérifie si l'utilisateur a une permission spécifique"""
        # Le super admin a TOUTES les permissions
        if self.role == 'super_admin':
            return True
            
        # Obtenir le rôle de l'utilisateur
        role = Role.query.filter_by(nom=self.role).first()
        if role:
            return role.has_permission(permission)
        
        # Fallback sur l'ancien système si pas de rôle en base
        permissions = {
            'admin': ['manage_statuses', 'view_department', 'edit_department', 'read_department_mail', 'view_trash'],
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
    
    def can_edit_courrier(self, courrier):
        """Vérifier si l'utilisateur peut modifier un courrier donné"""
        # Super admin peut tout modifier
        if self.is_super_admin():
            return True
        
        # Vérifier les permissions spécifiques d'édition
        if self.has_permission('edit_all_mail'):
            return True
        elif self.has_permission('edit_department_mail'):
            if hasattr(courrier, 'utilisateur_enregistrement') and courrier.utilisateur_enregistrement:
                return courrier.utilisateur_enregistrement.departement_id == self.departement_id
            return False
        elif self.has_permission('edit_own_mail'):
            return courrier.utilisateur_id == self.id
        
        # Fallback sur les rôles par défaut
        if self.role == 'admin':
            if hasattr(courrier, 'utilisateur_enregistrement') and courrier.utilisateur_enregistrement:
                return courrier.utilisateur_enregistrement.departement_id == self.departement_id
            return courrier.utilisateur_id == self.id
        
        # Utilisateur normal ne peut modifier que ses propres courriers dans les 24h
        if courrier.utilisateur_id == self.id:
            # Permettre modification dans les 24h suivant la création
            from datetime import datetime, timedelta
            time_limit = courrier.date_enregistrement + timedelta(hours=24)
            return datetime.now() <= time_limit
        
        return False
    
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
    
    @staticmethod
    def init_super_admin():
        """Crée le premier utilisateur super admin s'il n'existe pas"""
        from werkzeug.security import generate_password_hash
        from app import db
        
        # Vérifier s'il existe déjà des utilisateurs
        if User.query.count() > 0:
            # Vérifier s'il y a au moins un super admin
            super_admin = User.query.filter_by(role='super_admin').first()
            if not super_admin:
                # S'il n'y a pas de super admin, promouvoir le premier utilisateur
                first_user = User.query.order_by(User.id).first()
                if first_user:
                    first_user.role = 'super_admin'
                    db.session.commit()
                    print(f"Utilisateur {first_user.username} promu super admin")
            return
        
        # Créer le super admin par défaut
        super_admin = User(
            username='admin',
            email='admin@gecmines.cd',
            nom_complet='Super Administrateur',
            password_hash=generate_password_hash('Admin2025!'),
            role='super_admin',
            langue='fr',
            actif=True
        )
        
        db.session.add(super_admin)
        
        try:
            db.session.commit()
            print("Super administrateur créé avec succès!")
            print("Username: admin")
            print("Password: Admin2025!")
            print("IMPORTANT: Changez ce mot de passe immédiatement!")
        except Exception as e:
            db.session.rollback()
            print(f"Erreur lors de la création du super admin: {e}")

class TypeCourrierSortant(db.Model):
    """Modèle pour les types de courrier sortant"""
    __tablename__ = 'type_courrier_sortant'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    actif = db.Column(db.Boolean, default=True, nullable=False)
    ordre_affichage = db.Column(db.Integer, default=0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    cree_par_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relations
    cree_par = db.relationship('User', backref='types_courrier_crees')
    courriers = db.relationship('Courrier', backref='type_sortant', lazy='dynamic')
    
    def __repr__(self):
        return f'<TypeCourrierSortant {self.nom}>'
    
    @staticmethod
    def get_types_actifs():
        """Récupère tous les types actifs triés par ordre d'affichage"""
        return TypeCourrierSortant.query.filter_by(actif=True).order_by(TypeCourrierSortant.ordre_affichage, TypeCourrierSortant.nom).all()
    
    @staticmethod
    def init_default_types():
        """Initialise les types de courrier sortant par défaut"""
        from app import db
        
        # Vérifier si des types existent déjà
        if TypeCourrierSortant.query.count() > 0:
            return
        
        types_defaut = [
            {'nom': 'Note circulaire', 'description': 'Note circulaire à diffusion large', 'ordre_affichage': 1},
            {'nom': 'Note télégramme', 'description': 'Note télégramme urgente', 'ordre_affichage': 2},
            {'nom': 'Lettre officielle', 'description': 'Lettre officielle standard', 'ordre_affichage': 3},
            {'nom': 'Mémorandum', 'description': 'Mémorandum interne', 'ordre_affichage': 4},
            {'nom': 'Convocation', 'description': 'Convocation à une réunion ou événement', 'ordre_affichage': 5},
            {'nom': 'Rapport', 'description': 'Rapport officiel', 'ordre_affichage': 6},
            {'nom': 'Note de service', 'description': 'Note de service interne', 'ordre_affichage': 7},
            {'nom': 'Autre', 'description': 'Autre type de courrier sortant', 'ordre_affichage': 99}
        ]
        
        for type_data in types_defaut:
            type_courrier = TypeCourrierSortant(**type_data)
            db.session.add(type_courrier)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Erreur lors de l'initialisation des types de courrier sortant: {e}")

class Courrier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_accuse_reception = db.Column(db.String(50), unique=True, nullable=False, index=True)
    numero_reference = db.Column(db.String(100), nullable=True, index=True)
    objet = db.Column(db.Text, nullable=False)
    type_courrier = db.Column(db.String(20), nullable=False, default='ENTRANT', index=True)  # ENTRANT ou SORTANT
    type_courrier_sortant_id = db.Column(db.Integer, db.ForeignKey('type_courrier_sortant.id'), nullable=True, index=True)  # Type spécifique pour courrier sortant
    expediteur = db.Column(db.String(200), nullable=True, index=True)  # Pour courrier entrant
    destinataire = db.Column(db.String(200), nullable=True, index=True)  # Pour courrier sortant
    date_redaction = db.Column(db.Date, nullable=True, index=True)  # Date de rédaction de la lettre (Date d'émission pour sortant)
    date_enregistrement = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    autres_informations = db.Column(db.Text, nullable=True)  # Informations supplémentaires pour courrier sortant
    fichier_nom = db.Column(db.String(255), nullable=True)
    fichier_chemin = db.Column(db.String(500), nullable=True)
    fichier_type = db.Column(db.String(50), nullable=True, index=True)
    statut = db.Column(db.String(50), nullable=False, default='RECU', index=True)
    date_modification_statut = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    
    # Champ spécifique pour courriers entrants
    secretaire_general_copie = db.Column(db.Boolean, nullable=True)  # Le SG est en copie (Oui/Non)
    
    # Colonnes de sécurité et cryptage
    objet_encrypted = db.Column(db.Text, nullable=True)  # Objet crypté
    expediteur_encrypted = db.Column(db.Text, nullable=True)  # Expéditeur crypté
    destinataire_encrypted = db.Column(db.Text, nullable=True)  # Destinataire crypté
    numero_reference_encrypted = db.Column(db.Text, nullable=True)  # Référence cryptée
    fichier_checksum = db.Column(db.String(64), nullable=True)  # Checksum du fichier
    fichier_encrypted = db.Column(db.Boolean, default=False)  # Fichier crypté ?
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Clé étrangère
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    modifie_par_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    modifie_par = db.relationship('User', foreign_keys=[modifie_par_id], backref='courriers_modifies')
    deleted_by = db.relationship('User', foreign_keys=[deleted_by_id], backref='courriers_deleted')
    
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
    
    def set_encrypted_objet(self, objet):
        """Définit l'objet crypté"""
        self.objet = objet  # Garde aussi en clair pour la compatibilité
        self.objet_encrypted = encrypt_sensitive_data(objet)
    
    def get_decrypted_objet(self):
        """Récupère l'objet décrypté"""
        if self.objet_encrypted:
            try:
                return decrypt_sensitive_data(self.objet_encrypted)
            except:
                return self.objet  # Fallback vers l'objet en clair
        return self.objet
    
    def set_encrypted_expediteur(self, expediteur):
        """Définit l'expéditeur crypté"""
        if expediteur:
            self.expediteur = expediteur  # Garde aussi en clair pour la compatibilité
            self.expediteur_encrypted = encrypt_sensitive_data(expediteur)
    
    def get_decrypted_expediteur(self):
        """Récupère l'expéditeur décrypté"""
        if self.expediteur_encrypted:
            try:
                return decrypt_sensitive_data(self.expediteur_encrypted)
            except:
                return self.expediteur  # Fallback vers l'expéditeur en clair
        return self.expediteur
    
    def set_encrypted_destinataire(self, destinataire):
        """Définit le destinataire crypté"""
        if destinataire:
            self.destinataire = destinataire  # Garde aussi en clair pour la compatibilité
            self.destinataire_encrypted = encrypt_sensitive_data(destinataire)
    
    def get_decrypted_destinataire(self):
        """Récupère le destinataire décrypté"""
        if self.destinataire_encrypted:
            try:
                return decrypt_sensitive_data(self.destinataire_encrypted)
            except:
                return self.destinataire  # Fallback vers le destinataire en clair
        return self.destinataire
    
    def set_encrypted_reference(self, numero_reference):
        """Définit la référence cryptée"""
        if numero_reference:
            self.numero_reference = numero_reference  # Garde aussi en clair pour la compatibilité
            self.numero_reference_encrypted = encrypt_sensitive_data(numero_reference)
    
    def get_decrypted_reference(self):
        """Récupère la référence décryptée"""
        if self.numero_reference_encrypted:
            try:
                return decrypt_sensitive_data(self.numero_reference_encrypted)
            except:
                return self.numero_reference  # Fallback vers la référence en clair
        return self.numero_reference
    
    def set_file_checksum(self, file_path):
        """Calcule et définit le checksum du fichier"""
        if file_path and os.path.exists(file_path):
            from encryption_utils import encryption_manager
            try:
                self.fichier_checksum = encryption_manager.generate_file_checksum(file_path)
            except Exception as e:
                logging.error(f"Erreur lors du calcul du checksum: {e}")
    
    def verify_file_integrity(self, file_path):
        """Vérifie l'intégrité du fichier"""
        if not self.fichier_checksum or not file_path or not os.path.exists(file_path):
            return False
        
        from encryption_utils import encryption_manager
        try:
            current_checksum = encryption_manager.generate_file_checksum(file_path)
            return current_checksum == self.fichier_checksum
        except Exception as e:
            logging.error(f"Erreur lors de la vérification de l'intégrité: {e}")
            return False

class CourrierModification(db.Model):
    """Historique des modifications des courriers"""
    __tablename__ = 'courrier_modification'
    
    id = db.Column(db.Integer, primary_key=True)
    courrier_id = db.Column(db.Integer, db.ForeignKey('courrier.id'), nullable=False, index=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    champ_modifie = db.Column(db.String(100), nullable=False)  # Nom du champ modifié
    ancienne_valeur = db.Column(db.Text, nullable=True)  # Ancienne valeur
    nouvelle_valeur = db.Column(db.Text, nullable=True)  # Nouvelle valeur
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    
    # Relations
    courrier = db.relationship('Courrier', backref='modifications', lazy=True)
    utilisateur = db.relationship('User', backref='courrier_modifications', lazy=True)
    
    def __repr__(self):
        return f'<CourrierModification {self.champ_modifie} for {self.courrier_id}>'

class LogActivite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    date_action = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    
    # Clé étrangère
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    courrier_id = db.Column(db.Integer, db.ForeignKey('courrier.id'), nullable=True, index=True)
    
    def __repr__(self):
        return f'<LogActivite {self.action} by {self.utilisateur.username}>'

class ParametresSysteme(db.Model):
    """Paramètres de configuration du système"""
    id = db.Column(db.Integer, primary_key=True)
    nom_logiciel = db.Column(db.String(100), nullable=False, default="GEC - Mines RDC")
    logo_url = db.Column(db.String(500), nullable=True)
    
    # Configuration du numéro d'accusé de réception
    mode_numero_accuse = db.Column(db.String(20), nullable=False, default="automatique")  # automatique ou manuel
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
    pays_pdf = db.Column(db.String(200), nullable=True, default="République Démocratique du Congo")
    copyright_text = db.Column(db.Text, nullable=True, default="© 2025 GEC. Made with 💖 and ☕ By MOA-Digital Agency LLC")
    
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
            if self.copyright_text:
                return self.copyright_text
            elif self.copyright_crypte:
                return base64.b64decode(self.copyright_crypte.encode()).decode('utf-8')
            else:
                return "© 2025 GEC. Made with 💖 and ☕ By MOA-Digital Agency LLC"
        except:
            return "© 2025 GEC. Made with 💖 and ☕ By MOA-Digital Agency LLC"
    
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
            # Initialiser les valeurs par défaut
            parametres.copyright_text = "© 2025 GEC. Made with 💖 and ☕ By MOA-Digital Agency LLC"
            parametres.pays_pdf = "République Démocratique du Congo"
            parametres.set_copyright_crypte("© 2025 GEC. Made with 💖 and ☕ By MOA-Digital Agency LLC")
            db.session.add(parametres)
            db.session.commit()
        elif not parametres.copyright_text:
            # Migrer depuis l'ancien système crypté
            parametres.copyright_text = "© 2025 GEC. Made with 💖 and ☕ By MOA-Digital Agency LLC"
            if not parametres.pays_pdf:
                parametres.pays_pdf = "République Démocratique du Congo"
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
                'delete_mail', 'view_trash', 'restore_mail', 'view_all', 'edit_all', 'read_all_mail'
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
