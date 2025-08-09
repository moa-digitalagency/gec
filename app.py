import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-gec-mines")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///gec_mines.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# Configure upload settings
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

with app.app_context():
    # Import models
    import models
    
    # Create all tables
    db.create_all()
    
    # Import security utilities
    from security_utils import add_security_headers, clean_security_storage, audit_log
    
    @app.before_request
    def before_request():
        """Execute before each request for security checks"""
        # Clean expired security data
        clean_security_storage()
        
        # Log all requests for audit
        from flask_login import current_user
        if current_user.is_authenticated:
            audit_log("REQUEST", f"{request.method} {request.path}")
    
    @app.after_request
    def after_request(response):
        """Execute after each request to add security headers"""
        return add_security_headers(response)
    
    # Initialize language support - will be done in views.py
    
    # Context processor pour les paramètres système
    @app.context_processor
    def inject_parametres():
        """Injecte les paramètres système dans tous les templates"""
        try:
            parametres = models.ParametresSysteme.get_parametres()
            return {'parametres': parametres}
        except:
            return {'parametres': None}
    
    # Create default admin user if none exists
    from werkzeug.security import generate_password_hash
    admin_user = models.User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = models.User(
            username='admin',
            email='admin@mines.gov.cd',
            nom_complet='Administrateur Système',
            password_hash=generate_password_hash('admin123'),
            role='super_admin',
            langue='fr'
        )
        db.session.add(admin_user)
        db.session.commit()
        logging.info("Default super admin user created (username: admin, password: admin123)")
    
    # Initialize system parameters
    parametres = models.ParametresSysteme.get_parametres()
    
    # Initialize default statuses
    models.StatutCourrier.init_default_statuts()
    
    logging.info("System parameters and statuses initialized")

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Add language functions to template context
@app.context_processor
def inject_language_functions():
    from utils import get_current_language, get_available_languages, t
    return {
        'get_current_language': get_current_language,
        'get_available_languages': get_available_languages,
        't': t
    }

# Import security utilities
from security_utils import add_security_headers

# Add security headers to all responses
@app.after_request
def security_headers(response):
    return add_security_headers(response)

# Enhanced error handlers with security logging
@app.errorhandler(429)
def rate_limit_error(error):
    from security_utils import log_security_event
    try:
        log_security_event("RATE_LIMIT_EXCEEDED", f"Rate limit exceeded from IP: {request.remote_addr}")
    except:
        pass
    return render_template('429.html'), 429

@app.errorhandler(403)
def forbidden_error(error):
    from security_utils import log_security_event
    try:
        log_security_event("ACCESS_DENIED", f"403 error for URL: {request.url}")
    except:
        pass
    return render_template('403.html'), 403

# Import views
import views
