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
    "echo": False,
}
# Configure upload settings
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore
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
        from flask import request
        from flask_login import current_user
        
        # Clean expired security data
        clean_security_storage()
        
        # Skip request logging to prevent performance issues
        # if current_user.is_authenticated and not request.path.startswith('/static'):
        #     audit_log("REQUEST", f"{request.method} {request.path}")
    
    @app.after_request
    def after_request(response):
        """Execute after each request to add security headers"""
        return add_security_headers(response)
    
    # Initialize language support - will be done in views.py
    
    # Ajouter la fonction format_date au contexte Jinja2
    from utils import format_date
    app.jinja_env.globals.update(format_date=format_date)
    
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
    admin_user = models.User.query.filter_by(username='sa.gec001').first()
    if not admin_user:
        # Check if old admin exists
        old_admin = models.User.query.filter_by(username='admin').first()
        if old_admin:
            # Just update the username
            old_admin.username = 'sa.gec001'
            old_admin.password_hash = generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'TempPassword123!'))
            db.session.commit()
            logging.info("Admin user updated (username: sa.gec001)")
        else:
            # Create new admin
            admin_user = models.User()
            admin_user.username = 'sa.gec001'
            admin_user.email = 'admin@mines.gov.cd'
            admin_user.nom_complet = 'Administrateur Système'
            admin_user.password_hash = generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'TempPassword123!'))
            admin_user.role = 'super_admin'
            admin_user.langue = 'fr'
            db.session.add(admin_user)
            db.session.commit()
            logging.info("Default super admin user created (username: sa.gec001)")
    
    # Initialize system parameters
    parametres = models.ParametresSysteme.get_parametres()
    
    # Initialize default statuses
    models.StatutCourrier.init_default_statuts()
    
    # Initialize default roles and permissions
    models.Role.init_default_roles()
    models.RolePermission.init_default_permissions()
    
    # Initialize default departments
    models.Departement.init_default_departments()
    
    # Initialize default outgoing mail types
    models.TypeCourrierSortant.init_default_types()
    
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

# Security headers are already handled in the after_request function above

# Enhanced error handlers with security logging
@app.errorhandler(429)
def rate_limit_error(error):
    from flask import request, render_template
    from security_utils import audit_log
    try:
        audit_log("RATE_LIMIT_EXCEEDED", f"Rate limit exceeded from IP: {request.remote_addr}")
    except:
        pass
    return render_template('429.html'), 429

@app.errorhandler(403)
def forbidden_error(error):
    from flask import request, render_template
    from security_utils import audit_log
    try:
        audit_log("ACCESS_DENIED", f"403 error for URL: {request.url}")
    except:
        pass
    return render_template('403.html'), 403

# Import views
import views
