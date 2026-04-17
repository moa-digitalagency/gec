from app import db
from datetime import datetime


class Departement(db.Model):
    """Modèle pour les départements"""
    __tablename__ = 'departement'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    chef_departement_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    chef_departement = db.relationship('User', foreign_keys=[chef_departement_id], backref='departement_chef', post_update=True)

    def __repr__(self):
        return f'<Departement {self.nom}>'

    @staticmethod
    def get_departements_actifs():
        return Departement.query.filter_by(actif=True).order_by(Departement.nom).all()

    @staticmethod
    def init_default_departments():
        from app import db
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

    cree_par = db.relationship('User', backref='types_courrier_crees')
    courriers = db.relationship('Courrier', backref='type_sortant', lazy='dynamic')

    def __repr__(self):
        return f'<TypeCourrierSortant {self.nom}>'

    @staticmethod
    def get_types_actifs():
        return TypeCourrierSortant.query.filter_by(actif=True).order_by(TypeCourrierSortant.ordre_affichage, TypeCourrierSortant.nom).all()

    @staticmethod
    def init_default_types():
        from app import db
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
        return StatutCourrier.query.filter_by(actif=True).order_by(StatutCourrier.ordre).all()

    @staticmethod
    def init_default_statuts():
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
