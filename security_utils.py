"""
Security utilities for the GEC Mines application
"""
import re
import uuid
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, session, abort, current_app, flash, redirect, url_for
from flask_login import current_user

# Rate limiting storage (in production, use Redis or similar)
_rate_limit_storage = {}

def clean_rate_limit_storage():
    """Clean expired rate limit entries"""
    now = datetime.now()
    expired_keys = [
        key for key, (count, timestamp) in _rate_limit_storage.items()
        if now - timestamp > timedelta(minutes=15)
    ]
    for key in expired_keys:
        del _rate_limit_storage[key]

def rate_limit(max_requests=10, per_minutes=15):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_app.config.get('TESTING', False):  # Skip in testing
                # Clean old entries
                clean_rate_limit_storage()
                
                # Get client identifier
                client_id = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
                if current_user.is_authenticated:
                    client_id = f"user_{current_user.id}_{client_id}"
                
                # Check rate limit
                now = datetime.now()
                if client_id in _rate_limit_storage:
                    count, first_request = _rate_limit_storage[client_id]
                    if now - first_request < timedelta(minutes=per_minutes):
                        if count >= max_requests:
                            logging.warning(f"Rate limit exceeded for {client_id}")
                            abort(429)  # Too Many Requests
                        _rate_limit_storage[client_id] = (count + 1, first_request)
                    else:
                        _rate_limit_storage[client_id] = (1, now)
                else:
                    _rate_limit_storage[client_id] = (1, now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def sanitize_input(text):
    """Sanitize user input to prevent XSS"""
    if not text:
        return text
    
    # Remove dangerous HTML tags and scripts
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
        r'javascript:',
        r'vbscript:',
        r'onload=',
        r'onerror=',
        r'onclick=',
        r'onmouseover=',
    ]
    
    for pattern in dangerous_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text

def validate_file_upload(file):
    """Validate uploaded files for security"""
    if not file or not file.filename:
        return False, "Aucun fichier sélectionné"
    
    # Check file size (16MB max)
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Seek back to beginning
    
    if file_size > 16 * 1024 * 1024:  # 16MB
        return False, "Fichier trop volumineux (maximum 16MB)"
    
    # Check file extension
    allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif'}
    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if file_ext not in allowed_extensions:
        return False, f"Type de fichier non autorisé. Extensions autorisées: {', '.join(allowed_extensions)}"
    
    # Basic file header validation
    file_headers = {
        'pdf': b'%PDF',
        'png': b'\x89PNG\r\n\x1a\n',
        'jpg': b'\xff\xd8\xff',
        'jpeg': b'\xff\xd8\xff',
        'tiff': b'II*\x00',
        'tif': b'II*\x00'
    }
    
    header = file.read(10)
    file.seek(0)  # Reset file pointer
    
    expected_header = file_headers.get(file_ext)
    if expected_header and not header.startswith(expected_header):
        return False, "Le contenu du fichier ne correspond pas à son extension"
    
    return True, "Fichier valide"

def check_permission(permission_required, redirect_route='dashboard'):
    """Decorator to check user permissions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            
            if not current_user.has_permission(permission_required):
                flash('Accès refusé. Permissions insuffisantes.', 'error')
                return redirect(url_for(redirect_route))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_password_strength(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères"
    
    if not re.search(r'[A-Z]', password):
        return False, "Le mot de passe doit contenir au moins une majuscule"
    
    if not re.search(r'[a-z]', password):
        return False, "Le mot de passe doit contenir au moins une minuscule"
    
    if not re.search(r'\d', password):
        return False, "Le mot de passe doit contenir au moins un chiffre"
    
    # Check for common weak passwords
    weak_passwords = [
        'password', '123456789', 'admin123', 'password123',
        'qwerty', 'azerty', '12345678', 'admin'
    ]
    
    if password.lower() in weak_passwords:
        return False, "Ce mot de passe est trop faible. Choisissez un mot de passe plus complexe"
    
    return True, "Mot de passe valide"

def log_security_event(event_type, description, user_id=None, ip_address=None):
    """Log security events"""
    try:
        from app import db
        from models import LogActivite
        
        if not ip_address:
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
        
        if not user_id and current_user.is_authenticated:
            user_id = current_user.id
        
        if user_id:  # Only log if we have a user
            log = LogActivite()
            log.utilisateur_id = user_id
            log.action = f"SECURITY_{event_type}"
            log.description = description
            log.ip_address = ip_address
            db.session.add(log)
            db.session.commit()
            
    except Exception as e:
        logging.error(f"Failed to log security event: {e}")

def generate_csrf_token():
    """Generate CSRF token for forms"""
    if '_csrf_token' not in session:
        session['_csrf_token'] = str(uuid.uuid4())
    return session['_csrf_token']

def validate_csrf_token(token):
    """Validate CSRF token"""
    return token == session.get('_csrf_token')

# Security headers middleware
def add_security_headers(response):
    """Add security headers to responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' cdn.tailwindcss.com; font-src 'self' cdnjs.cloudflare.com;"
    return response