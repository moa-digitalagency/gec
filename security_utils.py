"""
Security utilities for the GEC application
Includes advanced security measures against various attacks
"""
import re
import uuid
import json
import logging
import hashlib
import secrets
import threading
import os
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from flask import request, session, abort, current_app, flash, redirect, url_for, g
from flask_login import current_user
from werkzeug.security import generate_password_hash, check_password_hash
import ipaddress

# Security storage (in production, use Redis or similar)
_rate_limit_storage = {}
_failed_login_attempts = defaultdict(dict)  # Changed to dict to store more info
_blocked_ips = set()
_suspicious_activities = defaultdict(list)
_session_tokens = {}
_security_logs = []  # Store security logs in memory

# SQL injection patterns - Plus précis
SQL_INJECTION_PATTERNS = [
    r"(\\'|(\\\\)+\')|(--;)|(-\s*-)",  # SQL comments et échappements 
    r"\b(union\s+select|union\s+all\s+select)\b",  # UNION attacks
    r"\b(drop\s+table|drop\s+database|truncate\s+table)\b",  # Destructive operations
    r"\b(exec\s*\(|execute\s*\(|sp_executesql)\b",  # Stored procedures
    r"(0x[0-9a-fA-F]+)|(\bhex\s*\()",  # Hex encoding
    r"(\bor\s+1\s*=\s*1)|(\band\s+1\s*=\s*0)",  # Boolean SQL injection
    r"(script.*?/script)|(javascript\s*:)|(vbscript\s*:)",  # Script injections
    r"(eval\s*\(.*?\))|(expression\s*\(.*?\))",  # Code execution
]

# XSS patterns
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"vbscript:",
    r"on\w+\s*=",
    r"<iframe[^>]*>",
    r"<object[^>]*>",
    r"<embed[^>]*>",
    r"<link[^>]*>",
    r"<meta[^>]*>",
]

# Security configuration - Made less restrictive
MAX_LOGIN_ATTEMPTS = 8  # Increased from 5 to 8 attempts
LOGIN_LOCKOUT_DURATION = 15  # Reduced from 30 to 15 minutes
SUSPICIOUS_ACTIVITY_THRESHOLD = 15  # Increased from 10 to 15
AUTO_BLOCK_DURATION = 30  # Reduced from 60 to 30 minutes

def clean_security_storage():
    """Clean expired security entries"""
    now = datetime.now()
    
    # Clean rate limit storage
    expired_keys = [
        key for key, (count, timestamp) in _rate_limit_storage.items()
        if now - timestamp > timedelta(minutes=15)
    ]
    for key in expired_keys:
        del _rate_limit_storage[key]
    
    # Clean failed login attempts
    expired_attempts = [
        ip for ip, data in _failed_login_attempts.items()
        if isinstance(data, dict) and now - data.get('timestamp', now) > timedelta(minutes=LOGIN_LOCKOUT_DURATION)
    ]
    for ip in expired_attempts:
        del _failed_login_attempts[ip]
    
    # Clean suspicious activities
    for ip in list(_suspicious_activities.keys()):
        _suspicious_activities[ip] = [
            activity for activity in _suspicious_activities[ip]
            if now - activity['timestamp'] < timedelta(hours=24)
        ]
        if not _suspicious_activities[ip]:
            del _suspicious_activities[ip]

def get_client_ip():
    """Get the real client IP address"""
    # Check for forwarded IPs first
    forwarded_ips = request.environ.get('HTTP_X_FORWARDED_FOR')
    if forwarded_ips:
        return forwarded_ips.split(',')[0].strip()
    
    return request.environ.get('REMOTE_ADDR', 'unknown')

def is_ip_blocked(ip):
    """Check if IP is blocked - but never block whitelisted IPs"""
    from models import IPBlock, IPWhitelist
    
    # Check whitelist first
    if IPWhitelist.is_ip_whitelisted(ip):
        return False
    
    return IPBlock.is_ip_blocked(ip)

def block_ip(ip, duration_minutes=AUTO_BLOCK_DURATION):
    """Block an IP address temporarily using database storage - but never block whitelisted IPs"""
    from models import IPBlock, IPWhitelist
    
    # Never block whitelisted IPs
    if IPWhitelist.is_ip_whitelisted(ip):
        logging.info(f"IP {ip} is whitelisted, skipping block")
        return False
    
    try:
        IPBlock.block_ip(ip, duration_minutes, "Automatic block due to suspicious activity")
        logging.warning(f"IP blocked: {ip} for {duration_minutes} minutes")
        return True
    except Exception as e:
        logging.error(f"Failed to block IP {ip}: {e}")
        # Fallback to in-memory blocking
        _blocked_ips.add(ip)
        return True

def log_suspicious_activity(ip, activity_type, details=""):
    """Log suspicious activity"""
    now = datetime.now()
    _suspicious_activities[ip].append({
        'timestamp': now,
        'type': activity_type,
        'details': details,
        'user_agent': request.headers.get('User-Agent', 'Unknown')
    })
    
    # Auto-block if too many suspicious activities
    if len(_suspicious_activities[ip]) >= SUSPICIOUS_ACTIVITY_THRESHOLD:
        block_ip(ip)
        logging.warning(f"IP auto-blocked due to suspicious activity: {ip}")

def rate_limit(max_requests=10, per_minutes=15):
    """Enhanced rate limiting decorator with IP blocking"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_app.config.get('TESTING', False):
                clean_security_storage()
                
                client_ip = get_client_ip()
                
                # Check if IP is blocked
                if is_ip_blocked(client_ip):
                    logging.warning(f"Blocked IP attempted access: {client_ip}")
                    abort(403)  # Forbidden
                
                # Get client identifier
                client_id = client_ip
                if current_user.is_authenticated:
                    client_id = f"user_{current_user.id}_{client_ip}"
                
                # Check rate limit
                now = datetime.now()
                if client_id in _rate_limit_storage:
                    count, first_request = _rate_limit_storage[client_id]
                    if now - first_request < timedelta(minutes=per_minutes):
                        if count >= max_requests:
                            log_suspicious_activity(client_ip, "RATE_LIMIT_EXCEEDED", 
                                                  f"Exceeded {max_requests} requests in {per_minutes} minutes")
                            logging.warning(f"Rate limit exceeded for {client_id}")
                            abort(429)
                        _rate_limit_storage[client_id] = (count + 1, first_request)
                    else:
                        _rate_limit_storage[client_id] = (1, now)
                else:
                    _rate_limit_storage[client_id] = (1, now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def detect_sql_injection(input_text):
    """Detect potential SQL injection attempts"""
    if not input_text:
        return False
    
    input_lower = input_text.lower()
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, input_lower, re.IGNORECASE):
            return True
    return False

def detect_xss_attack(input_text):
    """Detect potential XSS attacks"""
    if not input_text:
        return False
    
    for pattern in XSS_PATTERNS:
        if re.search(pattern, input_text, re.IGNORECASE):
            return True
    return False

def sanitize_input(text, strict=False):
    """Enhanced input sanitization with attack detection"""
    if not text:
        return text
    
    client_ip = get_client_ip()
    
    # Detect SQL injection
    if detect_sql_injection(text):
        log_suspicious_activity(client_ip, "SQL_INJECTION_ATTEMPT", f"Detected in: {text[:100]}")
        logging.warning(f"SQL injection attempt from {client_ip}: {text[:100]}")
        if strict:
            abort(400)  # Bad Request
        # Remove dangerous SQL patterns
        for pattern in SQL_INJECTION_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Detect XSS
    if detect_xss_attack(text):
        log_suspicious_activity(client_ip, "XSS_ATTEMPT", f"Detected in: {text[:100]}")
        logging.warning(f"XSS attempt from {client_ip}: {text[:100]}")
        if strict:
            abort(400)  # Bad Request
        # Remove dangerous XSS patterns
        for pattern in XSS_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Additional dangerous patterns
    additional_patterns = [
        r'eval\s*\(',
        r'expression\s*\(',
        r'url\s*\(',
        r'@import',
        r'\\x[0-9a-fA-F]+',
        r'&#[0-9]+;',
    ]
    
    for pattern in additional_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text.strip()

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

def record_failed_login(ip, username=""):
    """Record failed login attempt"""
    now = datetime.now()
    
    if ip not in _failed_login_attempts:
        _failed_login_attempts[ip] = {'count': 0, 'timestamp': now, 'usernames': set()}
    
    _failed_login_attempts[ip]['count'] += 1
    _failed_login_attempts[ip]['timestamp'] = now
    if username:
        _failed_login_attempts[ip]['usernames'].add(username)
    
    # Auto-block after too many failures
    if _failed_login_attempts[ip]['count'] >= MAX_LOGIN_ATTEMPTS:
        block_ip(ip, LOGIN_LOCKOUT_DURATION)
        log_suspicious_activity(ip, "BRUTE_FORCE_LOGIN", 
                              f"Too many failed login attempts: {_failed_login_attempts[ip]['count']}")
        return True  # Blocked
    
    return False  # Not blocked yet

def is_login_locked(ip):
    """Check if login is locked for this IP"""
    if ip in _failed_login_attempts:
        attempts_data = _failed_login_attempts[ip]
        return attempts_data.get('count', 0) >= MAX_LOGIN_ATTEMPTS
    return False

def reset_failed_login_attempts(ip):
    """Reset failed login attempts for IP (on successful login)"""
    if ip in _failed_login_attempts:
        del _failed_login_attempts[ip]

def validate_password_strength(password):
    """Enhanced password strength validation"""
    errors = []
    score = 0
    
    # Length check
    if len(password) < 8:
        errors.append("Le mot de passe doit contenir au moins 8 caractères")
    elif len(password) >= 12:
        score += 2
    else:
        score += 1
    
    # Character variety checks
    if not re.search(r'[A-Z]', password):
        errors.append("Le mot de passe doit contenir au moins une majuscule")
    else:
        score += 1
    
    if not re.search(r'[a-z]', password):
        errors.append("Le mot de passe doit contenir au moins une minuscule")
    else:
        score += 1
    
    if not re.search(r'\d', password):
        errors.append("Le mot de passe doit contenir au moins un chiffre")
    else:
        score += 1
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'"\\|,.<>?]', password):
        errors.append("Le mot de passe doit contenir au moins un caractère spécial")
    else:
        score += 2
    
    # Common patterns check
    common_patterns = [
        r'(012|123|234|345|456|567|678|789)',  # Sequential numbers
        r'(abc|bcd|cde|def|efg|fgh|ghi)',      # Sequential letters
        r'(password|admin|user|login)',         # Common words
        r'(\w)\1{2,}',                          # Repeated characters (3+)
    ]
    
    for pattern in common_patterns:
        if re.search(pattern, password.lower()):
            errors.append("Le mot de passe contient des motifs trop prévisibles")
            score -= 1
            break
    
    # Check against common weak passwords
    weak_passwords = [
        'password', '123456789', 'admin123', 'password123',
        'qwerty', 'azerty', '12345678', 'admin', 'user',
        'login', 'root', 'toor', 'pass', '1234', 'test'
    ]
    
    if password.lower() in weak_passwords:
        errors.append("Ce mot de passe est dans la liste des mots de passe faibles")
        score = 0
    
    # Overall strength assessment
    if errors:
        return False, "; ".join(errors)
    
    if score >= 6:
        strength = "Très fort"
    elif score >= 4:
        strength = "Fort"
    elif score >= 3:
        strength = "Moyen"
    else:
        strength = "Faible"
    
    return True, f"Mot de passe valide - Force: {strength}"

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

def generate_secure_session_token():
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)

def create_session_token(user_id):
    """Create and store a secure session token"""
    token = generate_secure_session_token()
    _session_tokens[token] = {
        'user_id': user_id,
        'created': datetime.now(),
        'last_used': datetime.now(),
        'ip': get_client_ip()
    }
    return token

def validate_session_token(token):
    """Validate a session token"""
    if token in _session_tokens:
        token_data = _session_tokens[token]
        # Check if token is not expired (24 hours max)
        if datetime.now() - token_data['created'] < timedelta(hours=24):
            # Update last used
            token_data['last_used'] = datetime.now()
            return token_data['user_id']
        else:
            # Remove expired token
            del _session_tokens[token]
    return None

def invalidate_session_token(token):
    """Invalidate a session token"""
    if token in _session_tokens:
        del _session_tokens[token]

def clean_expired_session_tokens():
    """Clean expired session tokens"""
    now = datetime.now()
    expired_tokens = [
        token for token, data in _session_tokens.items()
        if now - data['created'] > timedelta(hours=24)
    ]
    for token in expired_tokens:
        del _session_tokens[token]

def secure_file_handling(filename):
    """Secure file name handling"""
    # Remove path traversal attempts
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')
    
    # Sanitize filename
    filename = re.sub(r'[<>:"|?*]', '', filename)
    
    # Limit filename length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    return filename

def check_file_integrity(file_path, expected_checksum=None):
    """Check file integrity using SHA-256"""
    try:
        import hashlib
        
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        file_checksum = hash_sha256.hexdigest()
        
        if expected_checksum:
            return file_checksum == expected_checksum, file_checksum
        
        return True, file_checksum
        
    except Exception as e:
        logging.error(f"Error checking file integrity: {e}")
        return False, None

def secure_redirect(url, allowed_hosts=None):
    """Secure redirect to prevent open redirect vulnerabilities"""
    if not url:
        return url_for('dashboard')
    
    # Parse URL
    try:
        from urllib.parse import urlparse, urljoin
        parsed = urlparse(url)
        
        # Only allow relative URLs or URLs to allowed hosts
        if parsed.netloc:
            if allowed_hosts and parsed.netloc not in allowed_hosts:
                logging.warning(f"Attempted redirect to unauthorized host: {parsed.netloc}")
                return url_for('dashboard')
        
        # Prevent javascript: and data: URLs
        if parsed.scheme in ('javascript', 'data', 'vbscript'):
            logging.warning(f"Attempted redirect to dangerous scheme: {parsed.scheme}")
            return url_for('dashboard')
        
        return url
        
    except Exception as e:
        logging.error(f"Error parsing redirect URL: {e}")
        return url_for('dashboard')

def audit_log(action, details="", severity="INFO"):
    """Create audit log entry"""
    try:
        client_ip = get_client_ip()
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details,
            'user_id': current_user.id if current_user.is_authenticated else None,
            'username': current_user.username if current_user.is_authenticated else 'Anonymous',
            'ip_address': client_ip,
            'user_agent': user_agent,
            'severity': severity
        }
        
        # Log to file (in production, send to SIEM)
        logging.log(
            getattr(logging, severity, logging.INFO),
            f"AUDIT: {json.dumps(audit_entry)}"
        )
        
        # Store in memory for web interface
        from datetime import datetime as dt
        security_log_entry = {
            "timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": severity,
            "event_type": action,
            "message": details,
            "username": current_user.username if current_user and current_user.is_authenticated else "SYSTEM",
            "ip_address": client_ip,
            "source": "GEC_AUDIT"
        }
        _security_logs.append(security_log_entry)
        
        # Keep only last 1000 logs in memory
        if len(_security_logs) > 1000:
            _security_logs.pop(0)
        
        # Store in database if possible
        try:
            from app import db
            from models import LogActivite
            
            if current_user.is_authenticated:
                log = LogActivite()
                log.utilisateur_id = current_user.id
                log.action = f"AUDIT_{action}"
                log.description = details
                log.ip_address = client_ip
                db.session.add(log)
                db.session.commit()
        except Exception as db_e:
            logging.error(f"Failed to store audit log in database: {db_e}")
            
    except Exception as e:
        logging.error(f"Failed to create audit log: {e}")

# Security headers middleware
def add_security_headers(response):
    """Add comprehensive security headers to responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self' data:; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    response.headers['Permissions-Policy'] = (
        "camera=(), microphone=(), geolocation=(), "
        "accelerometer=(), gyroscope=(), magnetometer=()"
    )
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

def require_https():
    """Require HTTPS for sensitive operations"""
    if not request.is_secure and not current_app.config.get('TESTING', False):
        return redirect(request.url.replace('http://', 'https://'))
    return None

def get_security_logs(filters=None):
    """Get security logs with filtering and pagination"""
    logs = _security_logs.copy()
    
    if filters:
        # Filter by level
        if filters.get('level'):
            logs = [log for log in logs if log['level'] == filters['level']]
        
        # Filter by event type
        if filters.get('event_type'):
            logs = [log for log in logs if log['event_type'] == filters['event_type']]
        
        # Filter by date range
        if filters.get('date_start'):
            from datetime import datetime
            start_date = datetime.strptime(filters['date_start'], '%Y-%m-%d').date()
            logs = [log for log in logs if datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S').date() >= start_date]
        
        if filters.get('date_end'):
            from datetime import datetime
            end_date = datetime.strptime(filters['date_end'], '%Y-%m-%d').date()
            logs = [log for log in logs if datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S').date() <= end_date]
    
    # Sort by timestamp (newest first)
    logs.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Pagination
    page = filters.get('page', 1) if filters else 1
    per_page = filters.get('per_page', 50) if filters else 50
    
    total = len(logs)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_logs = logs[start:end]
    
    # Create mock log objects for template
    class MockLog:
        def __init__(self, data):
            from datetime import datetime
            self.timestamp = datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S')
            self.level = data['level']
            self.event_type = data['event_type']
            self.message = data['message']
            self.username = data.get('username')
            self.ip_address = data.get('ip_address')
    
    mock_logs = [MockLog(log) for log in paginated_logs]
    
    # Mock pagination object
    class MockPagination:
        def __init__(self, page, per_page, total):
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None
        
        def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
            last = self.pages
            for num in range(1, last + 1):
                if num <= left_edge or \
                   (num > self.page - left_current - 1 and num < self.page + right_current) or \
                   num > last - right_edge:
                    yield num
    
    pagination = MockPagination(page, per_page, total)
    
    return {
        'logs': mock_logs,
        'pagination': pagination
    }

def get_security_stats():
    """Get security statistics"""
    logs = _security_logs
    
    stats = {
        'successful_logins': len([log for log in logs if log['event_type'] == 'LOGIN_SUCCESS']),
        'failed_logins': len([log for log in logs if log['event_type'] == 'LOGIN_FAILED']),
        'blocked_ips': len([log for log in logs if log['event_type'] == 'LOGIN_BLOCKED']),
        'encrypted_files': len([log for log in logs if log['event_type'] == 'FILE_ENCRYPTED']),
    }
    
    return stats