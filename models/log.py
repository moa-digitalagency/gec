from app import db
from datetime import datetime


class LogActivite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    date_action = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45), nullable=True)

    utilisateur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    courrier_id = db.Column(db.Integer, db.ForeignKey('courrier.id'), nullable=True, index=True)

    def __repr__(self):
        return f'<LogActivite {self.action} by {self.utilisateur.username}>'
