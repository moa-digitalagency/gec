import os
import logging
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

# Charger .env AVANT tout le reste pour que DATABASE_URL soit disponible
# immédiatement (encryption.py le chargeait trop tard, après db.init_app)
from security.encryption import load_env_from_file
load_env_from_file()

from extensions import db  # db défini dans extensions.py, pas ici

# Configure logging
logging.basicConfig(level=logging.DEBUG)

csrf = CSRFProtect()

# Create the app
app = Flask(__name__)
_session_secret = os.environ.get("SESSION_SECRET")
if not _session_secret:
    if os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError("SESSION_SECRET est obligatoire en production. Définissez la variable d'environnement.")
    logging.warning("SESSION_SECRET non défini — clé temporaire utilisée (développement uniquement).")
    import secrets
    _session_secret = secrets.token_hex(32)
app.secret_key = _session_secret
app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 7   # 7 jours (réduit de 30 → 7)
app.config['WTF_CSRF_TIME_LIMIT'] = 3600               # Token CSRF valide 1h
app.config['SESSION_IDLE_TIMEOUT'] = 900               # 15 min d'inactivité

# Sécurité cookies de session
_is_production = os.environ.get("FLASK_ENV") == "production"
app.config['SESSION_COOKIE_SECURE']   = _is_production   # HTTPS only en prod
app.config['SESSION_COOKIE_HTTPONLY'] = True             # Inaccessible au JS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'           # Protège contre CSRF cross-site

# ProxyFix : x_for=1 résout REMOTE_ADDR depuis X-Forwarded-For (Nginx → Flask)
# Sans ça, REMOTE_ADDR reste 127.0.0.1 et les logs affichent toujours l'IP du proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Configure the database
# Strict enforcement of DATABASE_URL and PostgreSQL for production
database_url = os.environ.get("DATABASE_URL")
flask_env = os.environ.get("FLASK_ENV", "development")

if flask_env == "production":
    if not database_url:
        raise RuntimeError("En production, une base de données PostgreSQL est obligatoire.")
    if not database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
        raise RuntimeError("En production, une base de données PostgreSQL est obligatoire.")

# Fallback to SQLite only for development if DATABASE_URL is not set
if not database_url:
    database_url = "sqlite:///gec_mines.db"
    logging.warning("DATABASE_URL not set. Using SQLite for development.")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url

# Optimized connection pool settings.
# pool_size / max_overflow n'ont de sens que pour un pool à connexions multiples
# (PostgreSQL en prod). Sous SQLite (StaticPool), SQLAlchemy 2.x lève TypeError
# si on les passe — on restreint donc ces options au moteur non-SQLite.
if database_url.startswith("sqlite"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "echo": False,
    }
else:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 10,           # Keep 10 connections open
        "pool_recycle": 1800,      # Recycle connections every 30 minutes
        "pool_pre_ping": True,     # Check connection health before usage
        "max_overflow": 5,         # Allow 5 extra connections during bursts
        "echo": False,
    }
# Configure upload settings
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Initialize extensions
db.init_app(app)
csrf.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def ensure_dpem_permissions():
    """Attribue par défaut edit_registration_date au rôle admin (idempotent, révocable via l'UI).

    N'attribue PAS add_director_annotation (assignation manuelle réservée au Directeur
    via l'éditeur de rôles). Ne doit jamais faire échouer le boot de l'application.
    """
    try:
        from models import Role, RolePermission
        role = Role.query.filter_by(nom='admin').first()
        if role and not RolePermission.query.filter_by(role_id=role.id,
                                                        permission_nom='edit_registration_date').first():
            db.session.add(RolePermission(role_id=role.id, permission_nom='edit_registration_date'))
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
    except Exception as _e:
        logging.warning(f"ensure_dpem_permissions ignoré: {_e}")


with app.app_context():
    # Import models
    import models
    
    # Create all tables
    db.create_all()
    
    # Execute automatic migrations to handle new columns
    from utils.migrations import run_automatic_migrations, apply_database_specific_fixes
    run_automatic_migrations(app, db)
    apply_database_specific_fixes(db.engine)
    
    # Import security utilities
    from security import add_security_headers, clean_security_storage, audit_log
    
    @app.before_request
    def before_request():
        """Execute before each request for security checks"""
        from flask import request, session
        from flask_login import current_user
        import time

        # Clean expired security data
        clean_security_storage()
        # NB : l'expiration de session par inactivité est gérée de façon UNIFIÉE et
        # configurable dans routes/auth.py → enforce_session_expiry (Paramètres → Sécurité).
    
    @app.after_request
    def after_request(response):
        """Execute after each request to add security headers"""
        return add_security_headers(response)
    
    # Context processors sont maintenant définis dans views.py pour éviter les dépendances circulaires
    
    # Compte super admin initial — configurable par variables d'environnement
    # (les instances existantes ne sont pas affectées : le bloc ne s'exécute que si absent).
    from werkzeug.security import generate_password_hash
    _admin_username = os.environ.get('FIRST_ADMIN_USERNAME', 'sa.gec001')
    _admin_email = os.environ.get('FIRST_ADMIN_EMAIL', 'admin@gec.cd')
    _admin_password = os.environ.get('ADMIN_PASSWORD', 'TempPassword123!')
    admin_user = models.User.query.filter_by(username=_admin_username).first()
    if not admin_user:
        # Check if old admin exists
        old_admin = models.User.query.filter_by(username='admin').first()
        if old_admin:
            # Just update the username
            old_admin.username = _admin_username
            old_admin.password_hash = generate_password_hash(_admin_password)
            db.session.commit()
            logging.info(f"Admin user updated (username: {_admin_username})")
        else:
            # Create new admin
            admin_user = models.User()
            admin_user.username = _admin_username
            admin_user.email = _admin_email
            admin_user.nom_complet = 'Administrateur Système'
            admin_user.password_hash = generate_password_hash(_admin_password)
            admin_user.role = 'super_admin'
            admin_user.langue = 'fr'
            db.session.add(admin_user)
            db.session.commit()
            logging.info(f"Default super admin user created (username: {_admin_username})")
    
    # Initialize system parameters
    parametres = models.ParametresSysteme.get_parametres()

    # Appliquer les paramètres de sécurité configurables (Paramètres → Sécurité).
    # Modifiables en UI ; durée de session et taille d'upload prennent effet au redémarrage.
    try:
        from datetime import timedelta as _td
        app.config['PERMANENT_SESSION_LIFETIME'] = _td(days=parametres.session_lifetime_days or 7)
        app.config['MAX_CONTENT_LENGTH'] = (parametres.max_upload_mb or 100) * 1024 * 1024
        app.config['SESSION_IDLE_TIMEOUT'] = (parametres.session_idle_timeout_min or 15) * 60
    except Exception as _e:
        logging.warning(f"Paramètres de sécurité non appliqués: {_e}")

    # Initialize default statuses
    models.StatutCourrier.init_default_statuts()
    
    # Initialize default roles and permissions
    models.Role.init_default_roles()
    models.RolePermission.init_default_permissions()
    models.Role.ensure_hierarchy()
    ensure_dpem_permissions()

    # Initialize default departments
    models.Departement.init_default_departments()
    
    # Initialize default outgoing mail types
    models.TypeCourrierSortant.init_default_types()
    
    logging.info("System parameters and statuses initialized")

    # Planificateur de rappels (s'exécute une fois toutes les 6h dans ce processus)
    import threading

    def _reminder_job():
        """Job périodique : rappels d'échéances (intervalle configurable, défaut 6h)."""
        _interval_h = 6
        try:
            with app.app_context():
                _interval_h = models.ParametresSysteme.get_parametres().reminder_interval_h or 6
                from routes import _send_overdue_reminders
                n = _send_overdue_reminders()
                if n:
                    logging.info(f"Scheduler: {n} rappel(s) d'échéance envoyé(s)")
        except Exception as e:
            logging.error(f"Scheduler reminder error: {e}")
        finally:
            # Re-planifier selon l'intervalle configuré
            t = threading.Timer(_interval_h * 3600, _reminder_job)
            t.daemon = True
            t.start()

    # Démarrer uniquement hors mode test
    if not app.config.get('TESTING'):
        t0 = threading.Timer(60, _reminder_job)  # 1ère exécution après 1 min
        t0.daemon = True
        t0.start()

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# SEO : expose le flag noindex aux templates (activé via SEO_NOINDEX dans .env)
@app.context_processor
def inject_seo_flags():
    return {
        'seo_noindex': os.environ.get('SEO_NOINDEX', '').strip().lower() in ('1', 'true', 'yes', 'on')
    }

# Cache-busting : les assets statiques sont servis avec Cache-Control immutable (30 j).
# asset_url() ajoute ?v=<mtime> pour que toute mise à jour d'un CSS/JS soit rechargée
# automatiquement par le navigateur, sans avoir à vider le cache manuellement.
@app.context_processor
def inject_asset_helpers():
    from flask import url_for as _url_for

    def asset_url(filename):
        try:
            mtime = int(os.path.getmtime(os.path.join(app.static_folder, filename)))
        except Exception:
            mtime = 1
        return _url_for('static', filename=filename) + '?v=' + str(mtime)

    return {'asset_url': asset_url}

# Add language functions to template context
@app.context_processor
def inject_language_functions():
    from utils import get_current_language, get_available_languages, t
    return {
        'get_current_language': get_current_language,
        'get_available_languages': get_available_languages,
        't': t
    }

# Add system parameters to template context
@app.context_processor
def inject_system_parameters():
    from models import ParametresSysteme
    # Récupérer l'appellation depuis la base de données
    try:
        parametres = ParametresSysteme.get_parametres()
        appellation = getattr(parametres, 'appellation_departement', 'Départements') or 'Départements'
    except:
        appellation = 'Départements'
    
    return {
        'get_appellation_entites': lambda: appellation
    }

# Security headers are already handled in the after_request function above

# Enhanced error handlers are now in views.py

# Import views
import routes
