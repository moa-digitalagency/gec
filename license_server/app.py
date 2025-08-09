#!/usr/bin/env python3
"""
Système Centralisé de Gestion des Licences GEC Mines
Serveur d'administration et de validation des licences
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Configuration de l'application
app = Flask(__name__)
app.secret_key = os.environ.get("LICENSE_SERVER_SECRET") or secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("LICENSE_DATABASE_URL") or "sqlite:///license_server.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db.init_app(app)

# Modèles de base de données
class License(db.Model):
    __tablename__ = 'licenses'
    
    id = db.Column(db.Integer, primary_key=True)
    license_key = db.Column(db.String(12), unique=True, nullable=False, index=True)
    duration_days = db.Column(db.Integer, nullable=False)
    duration_label = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='ACTIVE', nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    
    # Informations de création
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100), default='SYSTEM')
    batch_id = db.Column(db.String(50))
    
    # Informations d'activation
    used_date = db.Column(db.DateTime)
    activation_date = db.Column(db.DateTime)
    expiration_date = db.Column(db.DateTime)
    used_domain = db.Column(db.String(100))
    used_ip = db.Column(db.String(45))
    client_info = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'license_key': self.license_key,
            'duration_days': self.duration_days,
            'duration_label': self.duration_label,
            'status': self.status,
            'is_used': self.is_used,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'used_date': self.used_date.isoformat() if self.used_date else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None
        }

class LicenseActivation(db.Model):
    __tablename__ = 'license_activations'
    
    id = db.Column(db.Integer, primary_key=True)
    license_key = db.Column(db.String(12), db.ForeignKey('licenses.license_key'), nullable=False)
    domain_fingerprint = db.Column(db.String(100), nullable=False)
    activation_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiration_date = db.Column(db.DateTime, nullable=False)
    client_ip = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

class AdminUser(db.Model):
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

# Routes principales
@app.route('/')
def index():
    """Page d'accueil du serveur de licences"""
    try:
        total_licenses = License.query.count()
        active_licenses = License.query.filter_by(status='ACTIVE', is_used=False).count()
        used_licenses = License.query.filter_by(is_used=True).count()
        
        stats = {
            'total': total_licenses,
            'active': active_licenses,
            'used': used_licenses,
            'available': active_licenses
        }
        
        return render_template('index.html', stats=stats)
    except Exception as e:
        return jsonify({'error': 'Erreur serveur', 'details': str(e)}), 500

@app.route('/api/validate/<license_key>')
def api_validate_license(license_key):
    """API de validation de licence"""
    try:
        license_obj = License.query.filter_by(license_key=license_key.upper()).first()
        
        if not license_obj:
            return jsonify({
                'valid': False,
                'message': 'Licence introuvable',
                'error_code': 'NOT_FOUND'
            }), 404
        
        if license_obj.is_used:
            return jsonify({
                'valid': False,
                'message': 'Licence déjà utilisée',
                'error_code': 'ALREADY_USED',
                'used_date': license_obj.used_date.isoformat() if license_obj.used_date else None
            }), 400
        
        if license_obj.status != 'ACTIVE':
            return jsonify({
                'valid': False,
                'message': 'Licence inactive',
                'error_code': 'INACTIVE'
            }), 400
        
        return jsonify({
            'valid': True,
            'license_key': license_obj.license_key,
            'duration_days': license_obj.duration_days,
            'duration_label': license_obj.duration_label,
            'message': 'Licence valide'
        })
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'message': 'Erreur serveur',
            'error_code': 'SERVER_ERROR',
            'details': str(e)
        }), 500

@app.route('/api/activate', methods=['POST'])
def api_activate_license():
    """API d'activation de licence"""
    try:
        data = request.get_json()
        
        if not data or 'license_key' not in data:
            return jsonify({
                'success': False,
                'message': 'Clé de licence requise'
            }), 400
        
        license_key = data['license_key'].upper()
        domain_fingerprint = data.get('domain_fingerprint', '')
        client_ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        # Valide la licence
        license_obj = License.query.filter_by(license_key=license_key).first()
        
        if not license_obj:
            return jsonify({
                'success': False,
                'message': 'Licence introuvable'
            }), 404
        
        if license_obj.is_used:
            return jsonify({
                'success': False,
                'message': 'Licence déjà utilisée'
            }), 400
        
        if license_obj.status != 'ACTIVE':
            return jsonify({
                'success': False,
                'message': 'Licence inactive'
            }), 400
        
        # Marque comme utilisée
        activation_date = datetime.utcnow()
        expiration_date = activation_date + timedelta(days=license_obj.duration_days)
        
        license_obj.is_used = True
        license_obj.used_date = activation_date
        license_obj.activation_date = activation_date
        license_obj.expiration_date = expiration_date
        license_obj.used_domain = domain_fingerprint
        license_obj.used_ip = client_ip
        
        # Enregistre l'activation
        activation = LicenseActivation(
            license_key=license_key,
            domain_fingerprint=domain_fingerprint,
            activation_date=activation_date,
            expiration_date=expiration_date,
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        db.session.add(activation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Licence activée avec succès ({license_obj.duration_label})',
            'activation_date': activation_date.isoformat(),
            'expiration_date': expiration_date.isoformat(),
            'duration_days': license_obj.duration_days
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Erreur lors de l\'activation',
            'details': str(e)
        }), 500

@app.route('/api/stats')
def api_stats():
    """API des statistiques"""
    try:
        stats = {
            'total_licenses': License.query.count(),
            'active_licenses': License.query.filter_by(status='ACTIVE', is_used=False).count(),
            'used_licenses': License.query.filter_by(is_used=True).count(),
            'inactive_licenses': License.query.filter(License.status != 'ACTIVE').count(),
            'by_type': {}
        }
        
        # Statistiques par type
        license_types = db.session.query(License.duration_label, 
                                       db.func.count(License.id).label('count')).group_by(License.duration_label).all()
        
        for license_type, count in license_types:
            stats['by_type'][license_type] = count
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate_licenses', methods=['GET', 'POST'])
def generate_licenses():
    """Génération de nouvelles licences"""
    if request.method == 'POST':
        try:
            count = int(request.form.get('count', 10))
            duration_days = int(request.form.get('duration_days', 30))
            duration_label = request.form.get('duration_label', '1 mois')
            
            if count > 1000:
                flash('Maximum 1000 licences par batch', 'error')
                return redirect(url_for('generate_licenses'))
            
            batch_id = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            generated_licenses = []
            
            for _ in range(count):
                # Génère une clé unique
                while True:
                    license_key = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(12))
                    if not License.query.filter_by(license_key=license_key).first():
                        break
                
                license_obj = License(
                    license_key=license_key,
                    duration_days=duration_days,
                    duration_label=duration_label,
                    batch_id=batch_id
                )
                
                db.session.add(license_obj)
                generated_licenses.append(license_key)
            
            db.session.commit()
            
            flash(f'{count} licences générées avec succès (Batch: {batch_id})', 'success')
            
            return render_template('generated_licenses.html', 
                                 licenses=generated_licenses,
                                 batch_id=batch_id,
                                 duration_label=duration_label)
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la génération: {str(e)}', 'error')
    
    return render_template('generate_licenses.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Crée un utilisateur admin par défaut
        if not AdminUser.query.filter_by(username='admin').first():
            admin = AdminUser(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                email='admin@gec-mines.local'
            )
            db.session.add(admin)
            db.session.commit()
            print("Utilisateur admin créé (admin/admin123)")
    
    app.run(host='0.0.0.0', port=5001, debug=True)