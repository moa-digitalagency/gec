"""
Module de capture caméra en temps réel avec Flask-SocketIO
Permet un vrai streaming vidéo depuis la caméra du navigateur
"""

from flask import Blueprint, render_template, jsonify
from flask_socketio import SocketIO, emit
from flask_login import login_required
import base64
import io
from PIL import Image
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import uuid

# Blueprint pour les routes caméra
camera_bp = Blueprint('camera', __name__)

# SocketIO sera initialisé dans main.py
socketio = None

def init_socketio(app):
    """Initialise SocketIO avec l'app Flask"""
    global socketio
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    @socketio.on('connect')
    def handle_connect():
        print('Client connecté au serveur de caméra')
        emit('connected', {'status': 'Connexion établie'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client déconnecté')
    
    @socketio.on('camera_frame')
    def handle_camera_frame(data):
        """Reçoit les frames de la caméra depuis le client"""
        try:
            # Décoder l'image base64
            image_data = data.get('image', '')
            if image_data.startswith('data:image'):
                # Retirer le header data:image/jpeg;base64,
                image_data = image_data.split(',')[1]
            
            # Convertir en bytes
            image_bytes = base64.b64decode(image_data)
            
            # Ouvrir avec PIL pour vérification
            image = Image.open(io.BytesIO(image_bytes))
            
            # Émettre un accusé de réception
            emit('frame_received', {'status': 'ok', 'size': len(image_bytes)})
            
        except Exception as e:
            print(f"Erreur traitement frame: {e}")
            emit('frame_error', {'error': str(e)})
    
    @socketio.on('capture_photo')
    def handle_capture_photo(data):
        """Capture et sauvegarde une photo"""
        try:
            image_data = data.get('image', '')
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            # Décoder l'image
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Générer un nom de fichier unique
            filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join('uploads', filename)
            
            # Créer le dossier si nécessaire
            os.makedirs('uploads', exist_ok=True)
            
            # Sauvegarder l'image
            image.save(filepath, 'JPEG', quality=90)
            
            # Renvoyer le succès avec le nom du fichier
            emit('capture_success', {
                'filename': filename,
                'path': filepath,
                'size': os.path.getsize(filepath)
            })
            
        except Exception as e:
            print(f"Erreur capture photo: {e}")
            emit('capture_error', {'error': str(e)})
    
    return socketio

@camera_bp.route('/camera_capture')
@login_required
def camera_capture():
    """Page de capture caméra en temps réel"""
    return render_template('camera_capture.html')

@camera_bp.route('/camera_status')
def camera_status():
    """Vérifie le statut du serveur de caméra"""
    return jsonify({
        'status': 'active',
        'socketio': socketio is not None,
        'timestamp': datetime.now().isoformat()
    })