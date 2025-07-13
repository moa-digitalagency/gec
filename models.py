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
    
    # Relations
    courriers = db.relationship('Courrier', backref='utilisateur_enregistrement', lazy=True)
    logs = db.relationship('LogActivite', backref='utilisateur', lazy=True)

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
    
    # Clé étrangère
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Courrier {self.numero_accuse_reception}>'
    
    @property
    def reference_display(self):
        return self.numero_reference if self.numero_reference else "Non référencé"

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
