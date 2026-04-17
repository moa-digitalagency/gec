from extensions import db
from datetime import datetime


class Notification(db.Model):
    """Modèle pour les notifications dans l'application"""
    __tablename__ = 'notification'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    type_notification = db.Column(db.String(50), nullable=False, index=True)
    titre = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    courrier_id = db.Column(db.Integer, db.ForeignKey('courrier.id'), nullable=True, index=True)
    lu = db.Column(db.Boolean, default=False, index=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    date_lecture = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref='notifications')
    courrier = db.relationship('Courrier', backref='notifications')

    def __repr__(self):
        return f'<Notification {self.titre}>'

    def mark_as_read(self):
        self.lu = True
        self.date_lecture = datetime.utcnow()
        if self.type_notification == 'mail_forwarded' and self.courrier_id:
            from models.courrier import CourrierForward
            forward = CourrierForward.query.filter_by(
                courrier_id=self.courrier_id,
                forwarded_to_id=self.user_id
            ).order_by(CourrierForward.date_transmission.desc()).first()
            if forward and not forward.lu:
                forward.lu = True
                forward.date_lecture = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def create_notification(user_id, type_notification, titre, message, courrier_id=None):
        notification = Notification(
            user_id=user_id,
            type_notification=type_notification,
            titre=titre,
            message=message,
            courrier_id=courrier_id
        )
        db.session.add(notification)
        db.session.commit()
        return notification

    @staticmethod
    def get_unread_count(user_id):
        return Notification.query.filter_by(user_id=user_id, lu=False).count()
