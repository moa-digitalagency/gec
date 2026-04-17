from extensions import db
from datetime import datetime
import os
import logging
from security.encryption import encryption_manager, encrypt_sensitive_data, decrypt_sensitive_data


class Courrier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_accuse_reception = db.Column(db.String(50), unique=True, nullable=False, index=True)
    numero_reference = db.Column(db.String(100), nullable=True, index=True)
    objet = db.Column(db.Text, nullable=False)
    type_courrier = db.Column(db.String(20), nullable=False, default='ENTRANT', index=True)
    type_courrier_sortant_id = db.Column(db.Integer, db.ForeignKey('type_courrier_sortant.id'), nullable=True, index=True)
    expediteur = db.Column(db.String(200), nullable=True, index=True)
    destinataire = db.Column(db.String(200), nullable=True, index=True)
    date_redaction = db.Column(db.Date, nullable=True, index=True)
    date_enregistrement = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    autres_informations = db.Column(db.Text, nullable=True)
    fichier_nom = db.Column(db.String(255), nullable=True)
    fichier_chemin = db.Column(db.String(500), nullable=True)
    fichier_type = db.Column(db.String(50), nullable=True, index=True)
    statut = db.Column(db.String(50), nullable=False, default='RECU', index=True)
    date_modification_statut = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    secretaire_general_copie = db.Column(db.Boolean, nullable=True)

    # Colonnes de sécurité et cryptage
    objet_encrypted = db.Column(db.Text, nullable=True)
    expediteur_encrypted = db.Column(db.Text, nullable=True)
    destinataire_encrypted = db.Column(db.Text, nullable=True)
    numero_reference_encrypted = db.Column(db.Text, nullable=True)
    fichier_checksum = db.Column(db.String(64), nullable=True)
    fichier_encrypted = db.Column(db.Boolean, default=False)

    # Rappels et échéances
    due_date = db.Column(db.Date, nullable=True, index=True)
    reminder_sent_at = db.Column(db.DateTime, nullable=True)

    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

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
        if self.type_courrier == 'ENTRANT':
            return self.expediteur
        else:
            return self.destinataire

    def get_label_contact(self):
        if self.type_courrier == 'ENTRANT':
            return "Expéditeur"
        else:
            return "Destinataire"

    def get_type_display(self):
        return "Courrier Entrant" if self.type_courrier == 'ENTRANT' else "Courrier Sortant"

    def get_type_color(self):
        if self.type_courrier == 'ENTRANT':
            return 'bg-blue-100 text-blue-800'
        else:
            return 'bg-green-100 text-green-800'

    @property
    def statut_color(self):
        colors = {
            'RECU': 'bg-blue-100 text-blue-800',
            'EN_COURS': 'bg-yellow-100 text-yellow-800',
            'TRAITE': 'bg-green-100 text-green-800',
            'ARCHIVE': 'bg-gray-100 text-gray-800',
            'URGENT': 'bg-red-100 text-red-800'
        }
        return colors.get(self.statut, 'bg-gray-100 text-gray-800')

    def set_encrypted_objet(self, objet):
        self.objet = objet
        self.objet_encrypted = encrypt_sensitive_data(objet)

    def get_decrypted_objet(self):
        if self.objet_encrypted:
            try:
                return decrypt_sensitive_data(self.objet_encrypted)
            except:
                return self.objet
        return self.objet

    def set_encrypted_expediteur(self, expediteur):
        if expediteur:
            self.expediteur = expediteur
            self.expediteur_encrypted = encrypt_sensitive_data(expediteur)

    def get_decrypted_expediteur(self):
        if self.expediteur_encrypted:
            try:
                return decrypt_sensitive_data(self.expediteur_encrypted)
            except:
                return self.expediteur
        return self.expediteur

    def set_encrypted_destinataire(self, destinataire):
        if destinataire:
            self.destinataire = destinataire
            self.destinataire_encrypted = encrypt_sensitive_data(destinataire)

    def get_decrypted_destinataire(self):
        if self.destinataire_encrypted:
            try:
                return decrypt_sensitive_data(self.destinataire_encrypted)
            except:
                return self.destinataire
        return self.destinataire

    def set_encrypted_reference(self, numero_reference):
        if numero_reference:
            self.numero_reference = numero_reference
            self.numero_reference_encrypted = encrypt_sensitive_data(numero_reference)

    def get_decrypted_reference(self):
        if self.numero_reference_encrypted:
            try:
                return decrypt_sensitive_data(self.numero_reference_encrypted)
            except:
                return self.numero_reference
        return self.numero_reference

    def set_file_checksum(self, file_path):
        if file_path and os.path.exists(file_path):
            try:
                self.fichier_checksum = encryption_manager.generate_file_checksum(file_path)
            except Exception as e:
                logging.error(f"Erreur lors du calcul du checksum: {e}")

    def verify_file_integrity(self, file_path):
        if not self.fichier_checksum or not file_path or not os.path.exists(file_path):
            return False
        try:
            current_checksum = encryption_manager.generate_file_checksum(file_path)
            return current_checksum == self.fichier_checksum
        except Exception as e:
            logging.error(f"Erreur lors de la vérification de l'intégrité: {e}")
            return False


class CourrierAttachment(db.Model):
    """Pièces jointes supplémentaires d'un courrier"""
    __tablename__ = 'courrier_attachment'

    id = db.Column(db.Integer, primary_key=True)
    courrier_id = db.Column(db.Integer, db.ForeignKey('courrier.id'), nullable=False, index=True)
    fichier_nom = db.Column(db.String(255), nullable=False)
    fichier_chemin = db.Column(db.String(500), nullable=False)
    fichier_type = db.Column(db.String(50), nullable=True)
    fichier_taille = db.Column(db.Integer, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    courrier = db.relationship('Courrier', backref=db.backref('attachments', lazy='dynamic'))
    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id])

    def __repr__(self):
        return f'<CourrierAttachment {self.fichier_nom}>'


class CourrierModification(db.Model):
    """Historique des modifications des courriers"""
    __tablename__ = 'courrier_modification'

    id = db.Column(db.Integer, primary_key=True)
    courrier_id = db.Column(db.Integer, db.ForeignKey('courrier.id'), nullable=False, index=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    champ_modifie = db.Column(db.String(100), nullable=False)
    ancienne_valeur = db.Column(db.Text, nullable=True)
    nouvelle_valeur = db.Column(db.Text, nullable=True)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45), nullable=True)

    courrier = db.relationship('Courrier', backref='modifications', lazy=True)
    utilisateur = db.relationship('User', backref='courrier_modifications', lazy=True)

    def __repr__(self):
        return f'<CourrierModification {self.champ_modifie} for {self.courrier_id}>'


class CourrierForward(db.Model):
    """Modèle pour le suivi des transmissions de courriers"""
    __tablename__ = 'courrier_forward'

    id = db.Column(db.Integer, primary_key=True)
    courrier_id = db.Column(db.Integer, db.ForeignKey('courrier.id'), nullable=False, index=True)
    forwarded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    forwarded_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    message = db.Column(db.Text, nullable=True)
    attached_file = db.Column(db.String(255), nullable=True)
    attached_file_original_name = db.Column(db.String(255), nullable=True)
    attached_file_size = db.Column(db.Integer, nullable=True)
    date_transmission = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    lu = db.Column(db.Boolean, default=False, index=True)
    date_lecture = db.Column(db.DateTime, nullable=True)
    email_sent = db.Column(db.Boolean, default=False, index=True)

    courrier = db.relationship('Courrier', backref='forwards')
    forwarded_by = db.relationship('User', foreign_keys=[forwarded_by_id], backref='forwards_sent')
    forwarded_to = db.relationship('User', foreign_keys=[forwarded_to_id], backref='forwards_received')

    def __repr__(self):
        return f'<CourrierForward {self.id}>'

    def mark_as_read(self):
        self.lu = True
        self.date_lecture = datetime.utcnow()
        if self.courrier_id and self.forwarded_to_id:
            from models.notification import Notification
            notification = Notification.query.filter_by(
                courrier_id=self.courrier_id,
                user_id=self.forwarded_to_id,
                type_notification='mail_forwarded'
            ).order_by(Notification.date_creation.desc()).first()
            if notification and not notification.lu:
                notification.lu = True
                notification.date_lecture = datetime.utcnow()
        db.session.commit()


class CourrierComment(db.Model):
    """Modèle pour les commentaires sur les courriers"""
    __tablename__ = 'courrier_comment'

    id = db.Column(db.Integer, primary_key=True)
    courrier_id = db.Column(db.Integer, db.ForeignKey('courrier.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    commentaire = db.Column(db.Text, nullable=False)
    type_comment = db.Column(db.String(50), default='comment', index=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    date_modification = db.Column(db.DateTime, nullable=True)
    modifie_par_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    actif = db.Column(db.Boolean, default=True, index=True)

    courrier = db.relationship('Courrier', backref='comments')
    user = db.relationship('User', foreign_keys=[user_id], backref='comments_created')
    modifie_par = db.relationship('User', foreign_keys=[modifie_par_id], backref='comments_modified')

    def __repr__(self):
        return f'<CourrierComment {self.id}>'

    def update_comment(self, new_comment, modified_by_id):
        self.commentaire = new_comment
        self.date_modification = datetime.utcnow()
        self.modifie_par_id = modified_by_id
        db.session.commit()


class CourrierSignature(db.Model):
    """Circuit de signature hiérarchique"""
    __tablename__ = 'courrier_signature'

    id = db.Column(db.Integer, primary_key=True)
    courrier_id = db.Column(db.Integer, db.ForeignKey('courrier.id'), nullable=False, index=True)
    signataire_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    ordre = db.Column(db.Integer, nullable=False)
    statut = db.Column(db.String(20), nullable=False, default='PENDING', index=True)
    commentaire = db.Column(db.Text, nullable=True)
    signed_at = db.Column(db.DateTime, nullable=True)
    initiated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    initiated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    courrier = db.relationship('Courrier',
                               backref=db.backref('signatures', lazy='dynamic',
                                                  order_by='CourrierSignature.ordre'))
    signataire = db.relationship('User', foreign_keys=[signataire_id],
                                 backref='signatures_demandees')
    initiated_by = db.relationship('User', foreign_keys=[initiated_by_id])

    def __repr__(self):
        return f'<CourrierSignature courrier={self.courrier_id} user={self.signataire_id} ordre={self.ordre} statut={self.statut}>'
