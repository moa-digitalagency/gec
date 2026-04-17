from app import db
from datetime import datetime


class Tag(db.Model):
    """Étiquettes libres pour les courriers"""
    __tablename__ = 'tag'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False, unique=True, index=True)
    couleur = db.Column(db.String(7), nullable=False, default='#6B7280')
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def __repr__(self):
        return f'<Tag {self.nom}>'


class CourrierTag(db.Model):
    """Table de liaison Courrier ↔ Tag"""
    __tablename__ = 'courrier_tag'

    courrier_id = db.Column(db.Integer, db.ForeignKey('courrier.id'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), primary_key=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    added_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    courrier = db.relationship('Courrier', backref=db.backref('tags', lazy='dynamic'))
    tag = db.relationship('Tag', backref=db.backref('courriers', lazy='dynamic'))
    added_by = db.relationship('User', foreign_keys=[added_by_id])
