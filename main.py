from app import app
from flask_socketio import SocketIO

# Initialiser SocketIO pour le streaming caméra
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Configuration SocketIO pour la caméra
@socketio.on('connect')
def handle_connect():
    print('Client connecté au serveur de caméra')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client déconnecté')

@socketio.on('camera_frame')
def handle_camera_frame(data):
    """Reçoit les frames de la caméra depuis le client"""
    try:
        # Envoyer un accusé de réception
        socketio.emit('frame_received', {'status': 'ok'})
    except Exception as e:
        print(f"Erreur traitement frame: {e}")
        socketio.emit('frame_error', {'error': str(e)})

@socketio.on('capture_photo')
def handle_capture_photo(data):
    """Capture et sauvegarde une photo"""
    import base64
    import io
    from PIL import Image
    import os
    from datetime import datetime
    import uuid
    
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
        socketio.emit('capture_success', {
            'filename': filename,
            'path': filepath,
            'size': os.path.getsize(filepath)
        })
        
    except Exception as e:
        print(f"Erreur capture photo: {e}")
        socketio.emit('capture_error', {'error': str(e)})

if __name__ == '__main__':
    # Lancer avec SocketIO
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
