from extensions import db
from datetime import datetime


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
    modifiable = db.Column(db.Boolean, default=True)
    niveau = db.Column(db.Integer, nullable=False, default=10)  # Hiérarchie : super_admin>admin>bureau_courrier>user
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cree_par_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    cree_par = db.relationship('User', foreign_keys=[cree_par_id], backref='roles_crees')

    permissions = db.relationship('RolePermission', backref='role', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Role {self.nom}>'

    def has_permission(self, permission_nom):
        return any(p.permission_nom == permission_nom for p in self.permissions)

    def get_permissions_list(self):
        return [p.permission_nom for p in self.permissions]

    @staticmethod
    def init_default_roles():
        from app import db
        if Role.query.count() > 0:
            return
        roles_defaut = [
            {
                'nom': 'super_admin',
                'nom_affichage': 'Super Administrateur',
                'description': 'Accès complet au système avec toutes les permissions',
                'couleur': 'bg-yellow-100 text-yellow-800',
                'icone': 'fas fa-crown',
                'modifiable': False,
                'niveau': 100
            },
            {
                'nom': 'admin',
                'nom_affichage': 'Administrateur',
                'description': 'Gestion des utilisateurs et configuration système limitée',
                'couleur': 'bg-blue-100 text-blue-800',
                'icone': 'fas fa-shield-alt',
                'modifiable': True,
                'niveau': 80
            },
            {
                'nom': 'bureau_courrier',
                'nom_affichage': 'Bureau Courrier / Accueil',
                'description': 'Réception : enregistre, consulte et recherche ses propres courriers',
                'couleur': 'bg-green-100 text-green-800',
                'icone': 'fas fa-clipboard-list',
                'modifiable': True,
                'niveau': 40
            },
            {
                'nom': 'user',
                'nom_affichage': 'Utilisateur',
                'description': 'Accès de base pour enregistrer et consulter les courriers',
                'couleur': 'bg-gray-100 text-gray-800',
                'icone': 'fas fa-user',
                'modifiable': True,
                'niveau': 20
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

    @staticmethod
    def ensure_hierarchy():
        """Idempotent : garantit les niveaux de hiérarchie des rôles et l'existence du
        rôle Bureau Courrier. S'exécute à chaque démarrage (corrige les instances existantes)."""
        from app import db
        niveaux = {'super_admin': 100, 'admin': 80, 'bureau_courrier': 40, 'user': 20}
        changed = False
        for nom, niv in niveaux.items():
            role = Role.query.filter_by(nom=nom).first()
            if role and (role.niveau or 0) != niv:
                role.niveau = niv
                changed = True
        if not Role.query.filter_by(nom='bureau_courrier').first():
            role = Role(nom='bureau_courrier', nom_affichage='Bureau Courrier / Accueil',
                        description='Réception : enregistre, consulte et recherche ses propres courriers',
                        couleur='bg-green-100 text-green-800', icone='fas fa-clipboard-list',
                        modifiable=True, niveau=40)
            db.session.add(role)
            db.session.flush()
            for perm in ('register_mail', 'view_mail', 'search_mail', 'read_own_mail'):
                db.session.add(RolePermission(role_id=role.id, permission_nom=perm))
            changed = True
        if changed:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Erreur ensure_hierarchy: {e}")


class RolePermission(db.Model):
    """Permissions associées aux rôles"""
    __tablename__ = 'role_permission'

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    permission_nom = db.Column(db.String(100), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    accorde_par_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    accorde_par = db.relationship('User', backref='permissions_accordees')

    def __repr__(self):
        return f'<RolePermission {self.permission_nom} pour {self.role.nom}>'

    @staticmethod
    def init_default_permissions():
        from app import db
        if RolePermission.query.count() > 0:
            return
        permissions_defaut = {
            'super_admin': [
                'manage_users', 'manage_roles', 'manage_system_settings',
                'view_all_logs', 'manage_statuses', 'manage_departments',
                'register_mail', 'view_mail', 'search_mail', 'export_data',
                'delete_mail', 'view_trash', 'restore_mail', 'view_all', 'edit_all', 'read_all_mail',
                'manage_updates', 'manage_backup'
            ],
            'admin': [
                'manage_statuses', 'register_mail', 'view_mail',
                'search_mail', 'export_data', 'manage_system_settings',
                'view_department', 'edit_department', 'read_department_mail'
            ],
            'user': [
                'register_mail', 'view_mail', 'search_mail', 'export_data',
                'view_own', 'edit_own', 'read_own_mail'
            ],
            'bureau_courrier': [
                'register_mail', 'view_mail', 'search_mail', 'read_own_mail'
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
