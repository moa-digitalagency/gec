import os
import uuid
import json
from datetime import datetime
from flask import request, session
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# Imported locally to avoid circular imports
from models import LogActivite

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif', 'svg'}

# Configuration des langues par défaut (peut être étendue automatiquement)
DEFAULT_LANGUAGE_CONFIG = {
    'fr': {'name': 'Français', 'flag': '🇫🇷', 'enabled': True},
    'en': {'name': 'English', 'flag': '🇺🇸', 'enabled': True},
    'es': {'name': 'Español', 'flag': '🇪🇸', 'enabled': True},
    'de': {'name': 'Deutsch', 'flag': '🇩🇪', 'enabled': True},
    'it': {'name': 'Italiano', 'flag': '🇮🇹', 'enabled': False},
    'pt': {'name': 'Português', 'flag': '🇵🇹', 'enabled': False},
    'ar': {'name': 'العربية', 'flag': '🇸🇦', 'enabled': False},
    'zh': {'name': '中文', 'flag': '🇨🇳', 'enabled': False},
    'ja': {'name': '日本語', 'flag': '🇯🇵', 'enabled': False},
    'ru': {'name': 'Русский', 'flag': '🇷🇺', 'enabled': False}
}

def get_available_languages():
    """Retourne la liste des langues disponibles en détectant automatiquement les fichiers JSON"""
    languages = {}
    lang_dir = os.path.join(os.path.dirname(__file__), 'lang')
    
    if os.path.exists(lang_dir):
        for filename in os.listdir(lang_dir):
            if filename.endswith('.json'):
                lang_code = filename[:-5]  # Remove .json
                
                # Utiliser la configuration par défaut si disponible, sinon générer automatiquement
                if lang_code in DEFAULT_LANGUAGE_CONFIG:
                    lang_config = DEFAULT_LANGUAGE_CONFIG[lang_code].copy()
                    # Vérifier si la langue est activée
                    if lang_config.get('enabled', True):
                        languages[lang_code] = lang_config
                else:
                    # Génération automatique pour les nouvelles langues (activées par défaut)
                    languages[lang_code] = {
                        'name': lang_code.upper(),  # Nom par défaut
                        'flag': '🌐',  # Drapeau générique
                        'enabled': True
                    }
    
    return languages

def get_all_languages():
    """Retourne toutes les langues (activées et désactivées)"""
    languages = {}
    lang_dir = os.path.join(os.path.dirname(__file__), 'lang')
    
    if os.path.exists(lang_dir):
        for filename in os.listdir(lang_dir):
            if filename.endswith('.json'):
                lang_code = filename[:-5]  # Remove .json
                
                # Utiliser la configuration par défaut si disponible, sinon générer automatiquement
                if lang_code in DEFAULT_LANGUAGE_CONFIG:
                    languages[lang_code] = DEFAULT_LANGUAGE_CONFIG[lang_code].copy()
                else:
                    # Génération automatique pour les nouvelles langues
                    languages[lang_code] = {
                        'name': lang_code.upper(),  # Nom par défaut
                        'flag': '🌐',  # Drapeau générique
                        'enabled': True
                    }
    
    return languages

def get_language_info(lang_code):
    """Obtient les informations d'une langue spécifique"""
    available_languages = get_available_languages()
    return available_languages.get(lang_code, {'name': lang_code.upper(), 'flag': '🌐'})

def toggle_language_status(lang_code, enabled):
    """Active ou désactive une langue"""
    if lang_code in DEFAULT_LANGUAGE_CONFIG:
        DEFAULT_LANGUAGE_CONFIG[lang_code]['enabled'] = enabled
        return True
    return False

def download_language_file(lang_code):
    """Télécharge le fichier de langue JSON"""
    lang_file = os.path.join(os.path.dirname(__file__), 'lang', f'{lang_code}.json')
    if os.path.exists(lang_file):
        return lang_file
    return None

def upload_language_file(lang_code, file_content):
    """Upload un nouveau fichier de langue JSON"""
    try:
        # Vérifier que le contenu est du JSON valide
        json.loads(file_content)
        
        # Créer le dossier lang s'il n'existe pas
        lang_dir = os.path.join(os.path.dirname(__file__), 'lang')
        os.makedirs(lang_dir, exist_ok=True)
        
        # Sauvegarder le fichier
        lang_file = os.path.join(lang_dir, f'{lang_code}.json')
        with open(lang_file, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        return True
    except (json.JSONDecodeError, Exception) as e:
        return False

def delete_language_file(lang_code):
    """Supprime un fichier de langue"""
    lang_file = os.path.join(os.path.dirname(__file__), 'lang', f'{lang_code}.json')
    if os.path.exists(lang_file) and lang_code != 'fr':  # Ne pas supprimer le français
        try:
            os.remove(lang_file)
            return True
        except Exception:
            return False
    return False

def get_current_language():
    """Obtient la langue actuelle depuis la session, cookies ou les préférences utilisateur"""
    available_languages = get_available_languages()
    
    # 1. Vérifier la session en premier
    if 'language' in session and session['language']:
        lang = session['language']
        if lang in available_languages:
            return lang
    
    # 2. Vérifier les cookies pour la persistance
    try:
        if hasattr(request, 'cookies') and request.cookies:
            lang_cookie = request.cookies.get('language')
            if lang_cookie and lang_cookie in available_languages:
                session['language'] = lang_cookie
                return lang_cookie
    except Exception:
        pass
    
    # 3. Si utilisateur connecté, vérifier ses préférences
    try:
        from flask_login import current_user
        if current_user.is_authenticated and hasattr(current_user, 'langue') and current_user.langue:
            if current_user.langue in available_languages:
                # Mettre à jour la session pour la cohérence
                session['language'] = current_user.langue
                return current_user.langue
    except Exception:
        pass  # Ignorer les erreurs si current_user n'est pas disponible
    
    # 4. Vérifier les préférences du navigateur
    try:
        if hasattr(request, 'accept_languages') and request.accept_languages:
            # Créer une liste des codes de langue disponibles
            available_codes = list(available_languages.keys())
            best_match = request.accept_languages.best_match(available_codes)
            if best_match and best_match in available_languages:
                session['language'] = best_match
                return best_match
    except Exception:
        pass
    
    # 5. Langue par défaut (français si disponible, sinon la première disponible)
    default_lang = 'fr' if 'fr' in available_languages else list(available_languages.keys())[0] if available_languages else 'fr'
    session['language'] = default_lang
    return default_lang

def format_date(date_obj, include_time=False):
    """Formate une date selon la langue courante"""
    if date_obj is None:
        return 'Non renseignée'
    
    lang = get_current_language()
    
    # Noms des jours en français
    jours_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    
    # Mois en français
    mois_fr = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 
               'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
    
    # Noms des jours en anglais
    jours_en = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Mois en anglais
    mois_en = ['January', 'February', 'March', 'April', 'May', 'June', 
               'July', 'August', 'September', 'October', 'November', 'December']
    
    if lang == 'fr':
        # Format français : Jour DD mois YYYY
        jour_idx = date_obj.weekday()  # 0 = Lundi, 6 = Dimanche
        mois_idx = date_obj.month - 1  # 0-11 pour l'index
        
        if include_time:
            return f"{jours_fr[jour_idx]} {date_obj.day} {mois_fr[mois_idx]} {date_obj.year} à {date_obj.strftime('%H:%M')}"
        else:
            return f"{date_obj.day} {mois_fr[mois_idx]} {date_obj.year}"
    else:
        # Format anglais : Day, Month DD, YYYY
        jour_idx = date_obj.weekday()
        mois_idx = date_obj.month - 1
        
        if include_time:
            return f"{jours_en[jour_idx]}, {mois_en[mois_idx]} {date_obj.day}, {date_obj.year} at {date_obj.strftime('%I:%M %p')}"
        else:
            return f"{mois_en[mois_idx]} {date_obj.day}, {date_obj.year}"

def set_language(lang_code):
    """Définit la langue dans la session"""
    available_languages = get_available_languages()
    if lang_code in available_languages:
        session['language'] = lang_code
        return True
    return False

def load_translations(lang_code='fr'):
    """Charge les traductions pour une langue donnée"""
    lang_dir = os.path.join(os.path.dirname(__file__), 'lang')
    lang_file = os.path.join(lang_dir, f'{lang_code}.json')
    
    if not os.path.exists(lang_file):
        lang_file = os.path.join(lang_dir, 'fr.json')
    
    try:
        with open(lang_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def t(key, lang_code=None, **kwargs):
    """Fonction de traduction"""
    if lang_code is None:
        lang_code = get_current_language()
    
    translations = load_translations(lang_code)
    
    keys = key.split('.')
    value = translations
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return key
    
    if kwargs and isinstance(value, str):
        try:
            return value.format(**kwargs)
        except (KeyError, ValueError):
            return value
    
    return value

def allowed_file(filename):
    """Vérifier si l'extension du fichier est autorisée"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_titre_responsable():
    """Récupère le titre du responsable de structure depuis les paramètres système"""
    try:
        from models import ParametresSysteme
        parametres = ParametresSysteme.get_parametres()
        return parametres.titre_responsable_structure if parametres.titre_responsable_structure else "Secrétaire Général"
    except:
        return "Secrétaire Général"

def generate_accuse_reception():
    """Générer un numéro d'accusé de réception unique selon le format configuré"""
    import re
    
    # Import dynamique pour éviter les dépendances circulaires
    from models import ParametresSysteme, Courrier
    
    # Récupérer le format configuré
    try:
        parametres = ParametresSysteme.get_parametres()
        format_string = parametres.format_numero_accuse
    except:
        # Fallback si les paramètres ne sont pas disponibles
        format_string = "GEC-{year}-{counter:05d}"
    
    now = datetime.now()
    
    # Remplacer les variables de base
    numero = format_string.replace('{year}', str(now.year))
    numero = numero.replace('{month}', f"{now.month:02d}")
    numero = numero.replace('{day}', f"{now.day:02d}")
    
    # Calculer le compteur pour l'année en cours
    try:
        count = Courrier.query.filter(
            Courrier.date_enregistrement >= datetime(now.year, 1, 1)
        ).count() + 1
    except:
        count = 1
    
    # Traiter les compteurs avec format
    counter_pattern = r'\{counter:(\d+)d\}'
    matches = re.findall(counter_pattern, numero)
    for match in matches:
        width = int(match)
        formatted_counter = f"{count:0{width}d}"
        numero = re.sub(r'\{counter:\d+d\}', formatted_counter, numero, count=1)
    
    # Compteur simple
    numero = numero.replace('{counter}', str(count))
    
    # Nombre aléatoire
    import random
    random_pattern = r'\{random:(\d+)\}'
    matches = re.findall(random_pattern, numero)
    for match in matches:
        width = int(match)
        random_num = random.randint(10**(width-1), 10**width-1)
        numero = re.sub(r'\{random:\d+\}', str(random_num), numero, count=1)
    
    return numero

def generate_format_preview(format_string):
    """Générer un aperçu du format de numéro d'accusé"""
    import re
    from datetime import datetime
    
    if not format_string:
        format_string = "GEC-{year}-{counter:05d}"
    
    now = datetime.now()
    preview = format_string
    
    # Remplacer les variables de base
    preview = preview.replace('{year}', str(now.year))
    preview = preview.replace('{month}', f"{now.month:02d}")
    preview = preview.replace('{day}', f"{now.day:02d}")
    
    # Traiter les compteurs avec format
    counter_pattern = r'\{counter:(\d+)d\}'
    matches = re.findall(counter_pattern, preview)
    for match in matches:
        width = int(match)
        formatted_counter = f"{1:0{width}d}"  # Exemple avec 1
        preview = re.sub(r'\{counter:\d+d\}', formatted_counter, preview, count=1)
    
    # Compteur simple
    preview = preview.replace('{counter}', '1')
    
    # Nombre aléatoire (exemple fixe pour la prévisualisation)
    random_pattern = r'\{random:(\d+)\}'
    matches = re.findall(random_pattern, preview)
    for match in matches:
        width = int(match)
        example_random = '1' * width  # Exemple avec des 1
        preview = re.sub(r'\{random:\d+\}', example_random, preview, count=1)
    
    return preview

def get_backup_files():
    """Obtenir la liste des fichiers de sauvegarde disponibles"""
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        return []
    
    backup_files = []
    for filename in os.listdir(backup_dir):
        if filename.endswith('.zip'):
            file_path = os.path.join(backup_dir, filename)
            file_stat = os.stat(file_path)
            backup_files.append({
                'filename': filename,
                'size': file_stat.st_size,
                'date': datetime.fromtimestamp(file_stat.st_mtime)
            })
    
    # Trier par date décroissante
    backup_files.sort(key=lambda x: x['date'], reverse=True)
    return backup_files

def create_system_backup():
    """Créer une sauvegarde complète du système avec support PostgreSQL"""
    import zipfile
    import subprocess
    import tempfile
    from datetime import datetime
    
    # Créer le dossier de sauvegarde s'il n'existe pas
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    
    # Nom du fichier de sauvegarde avec timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"backup_gec_{timestamp}.zip"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Sauvegarder la base de données PostgreSQL
        try:
            database_url = os.environ.get('DATABASE_URL')
            if database_url and 'postgresql' in database_url:
                # Extraire les paramètres de connexion
                import urllib.parse
                parsed = urllib.parse.urlparse(database_url)
                
                # Créer un dump PostgreSQL
                with tempfile.NamedTemporaryFile(suffix='.sql', delete=False) as temp_sql:
                    env = os.environ.copy()
                    env['PGPASSWORD'] = parsed.password
                    
                    cmd = [
                        'pg_dump',
                        '-h', parsed.hostname,
                        '-p', str(parsed.port or 5432),
                        '-U', parsed.username,
                        '-d', parsed.path[1:],  # Enlever le '/' initial
                        '--no-password',
                        '--clean',
                        '--if-exists'
                    ]
                    
                    with open(temp_sql.name, 'w') as f:
                        result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env)
                        
                    if result.returncode == 0:
                        zipf.write(temp_sql.name, 'database_backup.sql')
                        logging.info("Sauvegarde PostgreSQL créée avec succès")
                    else:
                        logging.warning(f"Erreur pg_dump: {result.stderr.decode()}")
                    
                    os.unlink(temp_sql.name)
                    
        except Exception as e:
            logging.warning(f"Impossible de créer la sauvegarde PostgreSQL: {e}")
        
        # Sauvegarder la base de données SQLite (si applicable)
        if os.path.exists('instance/database.db'):
            zipf.write('instance/database.db', 'database.db')
        
        # Sauvegarder les fichiers uploadés
        if os.path.exists('uploads'):
            for root, dirs, files in os.walk('uploads'):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, '.')
                    zipf.write(file_path, arc_path)
        
        # Sauvegarder les pièces jointes des transmissions
        if os.path.exists('forward_attachments'):
            for root, dirs, files in os.walk('forward_attachments'):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, '.')
                    zipf.write(file_path, arc_path)
        
        # Sauvegarder les fichiers de langues
        if os.path.exists('lang'):
            for root, dirs, files in os.walk('lang'):
                for file in files:
                    if file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        arc_path = os.path.relpath(file_path, '.')
                        zipf.write(file_path, arc_path)
        
        # Créer un fichier de documentation des variables d'environnement
        env_doc = {
            'DATABASE_URL': 'URL de connexion PostgreSQL (requise)',
            'GEC_MASTER_KEY': 'Clé maître pour le chiffrement (64 caractères hex)',
            'GEC_PASSWORD_SALT': 'Sel pour les mots de passe (64 caractères hex)',
            'SENDGRID_API_KEY': 'Clé API SendGrid pour les emails',
            'SMTP_SERVER': 'Serveur SMTP pour les emails',
            'SMTP_PORT': 'Port SMTP',
            'SMTP_EMAIL': 'Adresse email SMTP',
            'SMTP_PASSWORD': 'Mot de passe SMTP',
            'SMTP_USE_TLS': 'Utiliser TLS pour SMTP (true/false)',
            'SESSION_SECRET': 'Clé secrète pour les sessions Flask'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as env_file:
            json.dump(env_doc, env_file, indent=2, ensure_ascii=False)
            zipf.write(env_file.name, 'environment_variables_documentation.json')
            os.unlink(env_file.name)
        
        # Ajouter un manifeste de sauvegarde complet
        import json
        import tempfile
        manifest = {
            'timestamp': timestamp,
            'version': '1.2.0',
            'database_type': 'postgresql' if 'postgresql' in os.environ.get('DATABASE_URL', '') else 'sqlite',
            'backup_type': 'full_system_complete',
            'files_included': [
                'database', 'uploads', 'forward_attachments', 'lang', 'config', 
                'templates', 'static', 'exports', 'environment_doc'
            ],
            'description': 'Sauvegarde complète du système GEC incluant toutes les données, fichiers et configurations',
            'restore_instructions': {
                'database': 'Restaurer avec psql sur PostgreSQL ou copier pour SQLite',
                'files': 'Extraire tous les dossiers à la racine du nouveau système',
                'environment': 'Configurer les variables d\'environnement selon environment_variables_documentation.json',
                'post_restore': 'Redémarrer l\'application après restauration'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as manifest_file:
            json.dump(manifest, manifest_file, indent=2)
            zipf.write(manifest_file.name, 'backup_manifest.json')
            os.unlink(manifest_file.name)
        
        # Sauvegarder les fichiers de configuration et migration
        config_files = [
            'app.py', 'models.py', 'utils.py', 'views.py', 
            'migration_utils.py', 'email_utils.py', 'security_utils.py',
            'project-dependencies.txt', 'replit.md'
        ]
        for config_file in config_files:
            if os.path.exists(config_file):
                zipf.write(config_file)
        
        # Sauvegarder TOUS les templates 
        if os.path.exists('templates'):
            for root, dirs, files in os.walk('templates'):
                for file in files:
                    if file.endswith(('.html', '.htm', '.jinja2')):
                        file_path = os.path.join(root, file)
                        arc_path = os.path.relpath(file_path, '.')
                        zipf.write(file_path, arc_path)
        
        # Sauvegarder les fichiers statiques critiques (CSS, JS, images)
        static_folders = ['static/css', 'static/js', 'static/images', 'static/vendor']
        for folder in static_folders:
            if os.path.exists(folder):
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_path = os.path.relpath(file_path, '.')
                        zipf.write(file_path, arc_path)
        
        # Sauvegarder les exports et backups existants comme référence
        if os.path.exists('exports'):
            for file in os.listdir('exports'):
                if file.endswith('.pdf') or file.endswith('.xlsx'):
                    file_path = os.path.join('exports', file)
                    arc_path = os.path.relpath(file_path, '.')
                    zipf.write(file_path, arc_path)
    
    return backup_filename

def restore_system_from_backup(backup_file):
    """Restaurer le système depuis un fichier de sauvegarde avec support PostgreSQL"""
    import zipfile
    import tempfile
    import subprocess
    import shutil
    
    # Créer un dossier temporaire pour extraire la sauvegarde
    with tempfile.TemporaryDirectory() as temp_dir:
        # Sauvegarder le fichier uploadé
        backup_path = os.path.join(temp_dir, 'backup.zip')
        backup_file.save(backup_path)
        
        # Extraire la sauvegarde
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        # Restaurer la base de données PostgreSQL
        db_sql_backup = os.path.join(temp_dir, 'database_backup.sql')
        if os.path.exists(db_sql_backup):
            try:
                database_url = os.environ.get('DATABASE_URL')
                if database_url and 'postgresql' in database_url:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(database_url)
                    
                    env = os.environ.copy()
                    env['PGPASSWORD'] = parsed.password
                    
                    # Restaurer la base de données PostgreSQL
                    cmd = [
                        'psql',
                        '-h', parsed.hostname,
                        '-p', str(parsed.port or 5432),
                        '-U', parsed.username,
                        '-d', parsed.path[1:],
                        '-f', db_sql_backup,
                        '--no-password'
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
                    if result.returncode == 0:
                        logging.info("Base de données PostgreSQL restaurée avec succès")
                    else:
                        logging.error(f"Erreur lors de la restauration PostgreSQL: {result.stderr}")
                        
            except Exception as e:
                logging.error(f"Erreur lors de la restauration PostgreSQL: {e}")
        
        # Restaurer la base de données SQLite (si applicable)
        db_backup_path = os.path.join(temp_dir, 'database.db')
        if os.path.exists(db_backup_path):
            os.makedirs('instance', exist_ok=True)
            shutil.copy2(db_backup_path, 'instance/database.db')
        
        # Restaurer les fichiers uploadés
        uploads_backup_path = os.path.join(temp_dir, 'uploads')
        if os.path.exists(uploads_backup_path):
            if os.path.exists('uploads'):
                shutil.rmtree('uploads')
            shutil.copytree(uploads_backup_path, 'uploads')
        
        # Restaurer les fichiers de langues
        lang_backup_path = os.path.join(temp_dir, 'lang')
        if os.path.exists(lang_backup_path):
            if os.path.exists('lang'):
                # Sauvegarder les langues existantes avant remplacement
                backup_existing_lang = f'lang_backup_{int(time.time())}'
                shutil.move('lang', backup_existing_lang)
            shutil.copytree(lang_backup_path, 'lang')
        
        # Restaurer les fichiers de configuration critiques (optionnel et sécurisé)
        config_files_to_restore = [
            'project-dependencies.txt', 'replit.md'
        ]
        for config_file in config_files_to_restore:
            backup_config_path = os.path.join(temp_dir, config_file)
            if os.path.exists(backup_config_path):
                # Créer une sauvegarde de l'existant
                if os.path.exists(config_file):
                    backup_name = f"{config_file}.backup_{int(time.time())}"
                    shutil.copy2(config_file, backup_name)
                # Restaurer le fichier
                shutil.copy2(backup_config_path, config_file)
    
    return True

def recover_files_from_old_backup(backup_filename, file_patterns):
    """Récupérer des fichiers spécifiques d'une ancienne sauvegarde"""
    import zipfile
    import tempfile
    import fnmatch
    import time
    
    backup_path = os.path.join('backups', backup_filename)
    if not os.path.exists(backup_path):
        return False, f"Fichier de sauvegarde {backup_filename} non trouvé"
    
    recovered_files = []
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extraire la sauvegarde
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                all_files = zipf.namelist()
                
                # Trouver les fichiers correspondant aux patterns
                files_to_extract = []
                for pattern in file_patterns:
                    files_to_extract.extend(fnmatch.filter(all_files, pattern))
                
                # Extraire uniquement les fichiers demandés
                for file_path in files_to_extract:
                    zipf.extract(file_path, temp_dir)
                    
                    # Créer le répertoire de destination si nécessaire
                    dest_path = file_path
                    dest_dir = os.path.dirname(dest_path)
                    if dest_dir:
                        os.makedirs(dest_dir, exist_ok=True)
                    
                    # Copier le fichier récupéré
                    src_path = os.path.join(temp_dir, file_path)
                    if os.path.exists(src_path):
                        # Créer une sauvegarde du fichier existant
                        if os.path.exists(dest_path):
                            backup_name = f"{dest_path}.backup_{int(time.time())}"
                            import shutil
                            shutil.copy2(dest_path, backup_name)
                        
                        # Copier le fichier récupéré
                        import shutil
                        shutil.copy2(src_path, dest_path)
                        recovered_files.append(dest_path)
        
        return True, f"Fichiers récupérés avec succès: {', '.join(recovered_files)}"
        
    except Exception as e:
        return False, f"Erreur lors de la récupération: {str(e)}"

def create_automatic_backup_before_migration():
    """Créer une sauvegarde automatique avant migration"""
    import logging
    try:
        backup_filename = create_system_backup()
        logging.info(f"Sauvegarde pré-migration créée: {backup_filename}")
        return backup_filename
    except Exception as e:
        logging.error(f"Impossible de créer la sauvegarde pré-migration: {e}")
        return None

def verify_backup_integrity(backup_filename):
    """Vérifier l'intégrité d'un fichier de sauvegarde"""
    import zipfile
    
    backup_path = os.path.join('backups', backup_filename)
    if not os.path.exists(backup_path):
        return False, "Fichier de sauvegarde non trouvé"
    
    try:
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            # Tester l'intégrité du ZIP
            bad_files = zipf.testzip()
            if bad_files:
                return False, f"Fichiers corrompus détectés: {bad_files}"
            
            # Vérifier la présence des fichiers critiques
            files_in_zip = zipf.namelist()
            critical_files = ['database_backup.sql', 'database.db', 'uploads/', 'lang/']
            found_critical = any(any(f.startswith(critical) for f in files_in_zip) for critical in critical_files)
            
            if not found_critical:
                return False, "Aucun fichier critique trouvé dans la sauvegarde"
            
            return True, "Sauvegarde intègre"
            
    except Exception as e:
        return False, f"Erreur lors de la vérification: {str(e)}"

def log_activity(user_id, action, description, courrier_id=None):
    """Enregistrer une activité dans les logs"""
    try:
        from flask import request
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
        
        from models import LogActivite
        from app import db  # Import locally to avoid circular import
        log = LogActivite(
            utilisateur_id=user_id,
            action=action,
            description=description,
            courrier_id=courrier_id,
            ip_address=ip_address
        )
        
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        from app import db  # Import locally to avoid circular import
        db.session.rollback()
        print(f"Erreur lors de l'enregistrement du log: {e}")

def log_courrier_modification(courrier_id, user_id, champ_modifie, ancienne_valeur, nouvelle_valeur):
    """Enregistrer une modification de courrier"""
    try:
        from flask import request
        from models import CourrierModification
        from app import db  # Import locally to avoid circular import
        
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
        
        modification = CourrierModification(
            courrier_id=courrier_id,
            utilisateur_id=user_id,
            champ_modifie=champ_modifie,
            ancienne_valeur=str(ancienne_valeur) if ancienne_valeur is not None else None,
            nouvelle_valeur=str(nouvelle_valeur) if nouvelle_valeur is not None else None,
            ip_address=ip_address
        )
        
        db.session.add(modification)
        db.session.commit()
        
    except Exception as e:
        print(f"Erreur lors de l'enregistrement de la modification: {e}")
        from app import db  # Import locally to avoid circular import
        db.session.rollback()

def get_all_senders():
    """Récupérer la liste de tous les expéditeurs/destinataires uniques"""
    try:
        from models import Courrier
        from app import db  # Import locally to avoid circular import
        from sqlalchemy import or_, func
        
        # Récupérer tous les expéditeurs et destinataires non vides
        senders_query = db.session.query(
            Courrier.expediteur.label('contact'),
            func.count(Courrier.id).label('count_courriers'),
            func.max(Courrier.date_enregistrement).label('derniere_date')
        ).filter(
            Courrier.expediteur.isnot(None),
            Courrier.expediteur != ''
        ).group_by(Courrier.expediteur)
        
        destinataires_query = db.session.query(
            Courrier.destinataire.label('contact'),
            func.count(Courrier.id).label('count_courriers'),
            func.max(Courrier.date_enregistrement).label('derniere_date')
        ).filter(
            Courrier.destinataire.isnot(None),
            Courrier.destinataire != ''
        ).group_by(Courrier.destinataire)
        
        # Combiner les résultats
        all_contacts = []
        
        # Ajouter les expéditeurs
        for sender in senders_query.all():
            all_contacts.append({
                'nom': sender.contact,
                'type': 'Expéditeur',
                'nombre_courriers': sender.count_courriers,
                'derniere_date': sender.derniere_date
            })
        
        # Ajouter les destinataires
        for dest in destinataires_query.all():
            # Vérifier s'il n'existe pas déjà comme expéditeur
            existing = next((c for c in all_contacts if c['nom'] == dest.contact), None)
            if existing:
                existing['type'] = 'Expéditeur/Destinataire'
                existing['nombre_courriers'] += dest.count_courriers
                if dest.derniere_date > existing['derniere_date']:
                    existing['derniere_date'] = dest.derniere_date
            else:
                all_contacts.append({
                    'nom': dest.contact,
                    'type': 'Destinataire',
                    'nombre_courriers': dest.count_courriers,
                    'derniere_date': dest.derniere_date
                })
        
        # Trier par nombre de courriers décroissant
        all_contacts.sort(key=lambda x: x['nombre_courriers'], reverse=True)
        
        return all_contacts
        
    except Exception as e:
        print(f"Erreur lors de la récupération des contacts: {e}")
        return []

def export_courrier_pdf(courrier):
    """Exporter un courrier en PDF avec ses métadonnées"""
    # Créer le dossier exports s'il n'existe pas
    exports_dir = 'exports'
    os.makedirs(exports_dir, exist_ok=True)
    
    # Nom du fichier PDF
    filename = f"courrier_{courrier.numero_accuse_reception}.pdf"
    pdf_path = os.path.join(exports_dir, filename)
    
    # Classe personnalisée pour les numéros de page
    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []
            
        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()
            
        def save(self):
            """Add page info to each page (page x of y)"""
            num_pages = len(self._saved_page_states)
            for (page_num, page_state) in enumerate(self._saved_page_states):
                self.__dict__.update(page_state)
                self.draw_page_number(page_num + 1, num_pages)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)
            
        def draw_page_number(self, page_num, total_pages):
            """Draw the footer with copyright and page number at the bottom on two lines"""
            from models import ParametresSysteme
            from flask_login import current_user
            parametres = ParametresSysteme.get_parametres()
            
            # Première ligne : Système et Copyright
            line1_parts = []
            if parametres.texte_footer:
                line1_parts.append(parametres.texte_footer)
            
            copyright = parametres.copyright_text or parametres.get_copyright_decrypte()
            line1_parts.append(copyright)
            
            line1_text = " | ".join(line1_parts)
            
            # Deuxième ligne : Date, utilisateur et pagination
            line2_parts = []
            
            # Date de génération
            now = datetime.now()
            date_str = now.strftime('%A %d %B %Y à %H:%M')
            # Traduire en français
            mois_fr = {
                'January': 'janvier', 'February': 'février', 'March': 'mars', 'April': 'avril',
                'May': 'mai', 'June': 'juin', 'July': 'juillet', 'August': 'août',
                'September': 'septembre', 'October': 'octobre', 'November': 'novembre', 'December': 'décembre'
            }
            jours_fr = {
                'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi', 'Thursday': 'Jeudi',
                'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'
            }
            for en, fr in mois_fr.items():
                date_str = date_str.replace(en, fr)
            for en, fr in jours_fr.items():
                date_str = date_str.replace(en, fr)
            
            # Essayer d'obtenir l'utilisateur actuel
            try:
                if current_user and current_user.is_authenticated:
                    user_info = f"par {current_user.nom_complet}"
                else:
                    user_info = "par le système GEC"
            except:
                user_info = "par le système GEC"
            
            line2_parts.append(f"Document généré le {date_str} {user_info}")
            line2_parts.append(f"Page {page_num} sur {total_pages}")
            
            line2_text = " | ".join(line2_parts)
            
            # Configuration du texte
            self.setFont("Helvetica", 8)
            page_width = A4[0]
            left_margin = 0.75*inch
            right_margin = 0.75*inch
            text_width = page_width - left_margin - right_margin
            
            # Dessiner la première ligne
            line1_width = self.stringWidth(line1_text, "Helvetica", 8)
            if line1_width <= text_width:
                x_position1 = (page_width - line1_width) / 2
            else:
                x_position1 = left_margin
            self.drawString(x_position1, 0.6*inch, line1_text)
            
            # Dessiner la deuxième ligne
            line2_width = self.stringWidth(line2_text, "Helvetica", 8)
            if line2_width <= text_width:
                x_position2 = (page_width - line2_width) / 2
            else:
                x_position2 = left_margin
            self.drawString(x_position2, 0.4*inch, line2_text)
    
    # Créer le document PDF avec la classe personnalisée
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, topMargin=1*inch, bottomMargin=1.2*inch, 
                          leftMargin=0.75*inch, rightMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1,  # Centré
        textColor=colors.darkblue
    )
    
    # Style pour le texte avec wrap automatique
    text_style = ParagraphStyle(
        'CustomText',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=12,
        wordWrap='CJK',  # Permettre le wrap sur les mots longs
        splitLongWords=True,
        allowWidows=1,
        allowOrphans=1
    )
    
    # Style pour les labels
    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        textColor=colors.darkblue,
        fontName='Helvetica-Bold'
    )
    
    # Récupérer les paramètres système pour le PDF
    from models import ParametresSysteme
    parametres = ParametresSysteme.get_parametres()
    
    # Ajouter le logo s'il existe
    logo_path = None
    if parametres.logo_pdf:
        # Convertir l'URL relative en chemin de fichier absolu
        if parametres.logo_pdf.startswith('/uploads/'):
            logo_file_path = parametres.logo_pdf[9:]  # Enlever '/uploads/'
            logo_abs_path = os.path.join('uploads', logo_file_path)
            if os.path.exists(logo_abs_path):
                logo_path = logo_abs_path
    elif parametres.logo_url:
        # Convertir l'URL relative en chemin de fichier absolu
        if parametres.logo_url.startswith('/uploads/'):
            logo_file_path = parametres.logo_url[9:]  # Enlever '/uploads/'
            logo_abs_path = os.path.join('uploads', logo_file_path)
            if os.path.exists(logo_abs_path):
                logo_path = logo_abs_path
    
    if logo_path:
        try:
            # Charger l'image pour obtenir ses dimensions originales
            from PIL import Image as PILImage
            pil_img = PILImage.open(logo_path)
            original_width, original_height = pil_img.size
            
            # Calculer les dimensions en préservant le ratio
            max_width = 1.5*inch
            max_height = 1*inch
            
            # Calculer le ratio de redimensionnement
            width_ratio = max_width / original_width
            height_ratio = max_height / original_height
            ratio = min(width_ratio, height_ratio)
            
            # Nouvelles dimensions préservant le ratio
            new_width = original_width * ratio
            new_height = original_height * ratio
            
            logo = Image(logo_path, width=new_width, height=new_height)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 10))
        except Exception as e:
            print(f"Erreur chargement logo: {e}")  # Pour debug
    
    # Titre configuré du document
    titre_pdf = parametres.titre_pdf or "Ministère des Mines"
    sous_titre_pdf = parametres.sous_titre_pdf or "Secrétariat Général"
    
    # En-tête pays - PREMIER ÉLÉMENT
    pays_style = ParagraphStyle(
        'PaysStyle',
        parent=styles['Normal'],
        fontSize=16,
        fontName='Helvetica-Bold',
        alignment=1,  # Center
        spaceAfter=10,
        textColor=colors.darkblue
    )
    pays_text = parametres.pays_pdf or "République Démocratique du Congo"
    story.append(Paragraph(pays_text, pays_style))
    
    title = Paragraph(f"{titre_pdf}<br/>{sous_titre_pdf}", title_style)
    story.append(title)
    story.append(Spacer(1, 20))
    
    # Sous-titre selon le type
    type_display = "COURRIER ENTRANT" if courrier.type_courrier == 'ENTRANT' else "COURRIER SORTANT"
    subtitle = Paragraph(f"ACCUSÉ DE RÉCEPTION - {type_display}", styles['Heading2'])
    story.append(subtitle)
    story.append(Spacer(1, 20))
    
    # Tableau des métadonnées avec text wrapping pour les champs longs
    data = [
        [Paragraph('N° d\'Accusé de Réception:', label_style), Paragraph(courrier.numero_accuse_reception, text_style)],
        [Paragraph('Type de Courrier:', label_style), Paragraph(courrier.type_courrier, text_style)],
        [Paragraph('N° de Référence:', label_style), Paragraph(courrier.numero_reference if courrier.numero_reference else 'Non référencé', text_style)],
        [Paragraph(courrier.get_label_contact() + ':', label_style), Paragraph(courrier.get_contact_principal() if courrier.get_contact_principal() else 'Non spécifié', text_style)],
    ]
    
    # Ajouter le champ SG en copie seulement pour les courriers entrants
    if courrier.type_courrier == 'ENTRANT' and hasattr(courrier, 'secretaire_general_copie'):
        sg_copie_text = 'Oui' if courrier.secretaire_general_copie else 'Non'
        if courrier.secretaire_general_copie is None:
            sg_copie_text = 'Non renseigné'
        data.append([Paragraph('En copie:', label_style), Paragraph(sg_copie_text, text_style)])
    
    # Utiliser le bon label selon le type de courrier
    date_label = "Date d'Émission:" if courrier.type_courrier == 'SORTANT' else "Date de Rédaction:"
    
    data.extend([
        [Paragraph('Objet:', label_style), Paragraph(courrier.objet, text_style)],
        [Paragraph(date_label, label_style), Paragraph(format_date(courrier.date_redaction), text_style)],
        [Paragraph('Date d\'Enregistrement:', label_style), Paragraph(format_date(courrier.date_enregistrement, include_time=True), text_style)],
        [Paragraph('Enregistré par:', label_style), Paragraph(courrier.utilisateur_enregistrement.nom_complet, text_style)],
        [Paragraph('Statut:', label_style), Paragraph(courrier.statut, text_style)],
        [Paragraph('Fichier Joint:', label_style), Paragraph(courrier.fichier_nom if courrier.fichier_nom else 'Aucun', text_style)],
    ])
    
    table = Table(data, colWidths=[2.5*inch, 4*inch], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Alignement vertical en haut
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('WORDWRAP', (1, 0), (1, -1), 'CJK')  # Permettre le wrap des mots dans la colonne de droite
    ]))
    
    story.append(table)
    story.append(Spacer(1, 30))
    
    # Ajouter une note qui indique que les commentaires et transmissions sont en page 2
    from models import CourrierComment, CourrierForward
    comments = CourrierComment.query.filter_by(courrier_id=courrier.id, actif=True)\
                                   .order_by(CourrierComment.date_creation.desc()).all()
    forwards = CourrierForward.query.filter_by(courrier_id=courrier.id)\
                                   .order_by(CourrierForward.date_transmission.desc()).all()
    
    # Note d'information si il y a des commentaires ou transmissions
    if comments or forwards:
        info_note_style = ParagraphStyle(
            'InfoNote',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            textColor=colors.darkblue,
            fontName='Helvetica-Oblique',
            alignment=1  # Centré
        )
        
        elements_page2 = []
        if comments:
            elements_page2.append("commentaires")
        if forwards:
            elements_page2.append("historique des transmissions")
        
        note_text = f"Voir page suivante pour : {' et '.join(elements_page2)}"
        info_note = Paragraph(note_text, info_note_style)
        story.append(info_note)
        story.append(Spacer(1, 20))
    
    # Saut de page vers page 2 pour les commentaires et transmissions
    from reportlab.platypus import PageBreak
    if comments or forwards:
        story.append(PageBreak())
    
    # PAGE 2 : Commentaires et transmissions
    if comments:
        # Titre section commentaires
        comment_title = Paragraph('Commentaires et Annotations', title_style)
        story.append(comment_title)
        story.append(Spacer(1, 12))
        
        # Tableau des commentaires
        comment_data = [['Utilisateur', 'Type', 'Commentaire', 'Date']]
        
        for comment in comments:
            type_display = {
                'comment': 'Commentaire',
                'annotation': 'Annotation', 
                'instruction': 'Instruction'
            }.get(comment.type_comment, comment.type_comment)
            
            date_str = comment.date_creation.strftime('%d/%m/%Y %H:%M')
            if comment.date_modification:
                date_str += f" (modifié le {comment.date_modification.strftime('%d/%m/%Y %H:%M')})"
            
            # Style spécial pour les commentaires avec meilleur contrôle des retours à la ligne
            comment_text_style = ParagraphStyle(
                'CommentText',
                parent=text_style,
                wordWrap='CJK',
                splitLongWords=False,  # Éviter de couper les mots courts
                allowWidows=1,
                allowOrphans=1,
                breakLongWords=False,  # Ne pas casser les mots courts comme "commentaire"
                fontSize=9,
                leading=11
            )
            
            comment_data.append([
                Paragraph(comment.user.nom_complet, text_style),
                Paragraph(type_display, text_style),
                Paragraph(comment.commentaire, comment_text_style),
                Paragraph(date_str, text_style)
            ])
        
        comment_table = Table(comment_data, colWidths=[1.5*inch, 1.2*inch, 3.5*inch, 1.3*inch])
        comment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkblue),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('WORDWRAP', (0, 0), (-1, -1), 'CJK')
        ]))
        
        story.append(comment_table)
        story.append(Spacer(1, 20))
    
    # Ajouter l'historique des transmissions si présent
    forwards = CourrierForward.query.filter_by(courrier_id=courrier.id)\
                                   .order_by(CourrierForward.date_transmission.desc()).all()
    
    if forwards:
        # Titre section transmissions
        forward_title = Paragraph('Historique des Transmissions', title_style)
        story.append(forward_title)
        story.append(Spacer(1, 12))
        
        # Tableau des transmissions avec mêmes colonnes que commentaires
        forward_data = [['Transmis par', 'Transmis à', 'Message', 'Date']]
        
        for forward in forwards:
            date_str = forward.date_transmission.strftime('%d/%m/%Y %H:%M')
            
            status_parts = []
            if forward.lu:
                status_parts.append(f"Lu le {forward.date_lecture.strftime('%d/%m/%Y %H:%M')}")
            else:
                status_parts.append("Non lu")
            
            if forward.email_sent:
                status_parts.append("Email envoyé")
            
            status_str = " | ".join(status_parts)
            message_str = forward.message if forward.message else "-"
            
            # Ajouter l'information de pièce jointe si présente
            if forward.attached_file and forward.attached_file_original_name:
                attachment_info = f"📎 Pièce jointe: {forward.attached_file_original_name}"
                if forward.attached_file_size:
                    size_mb = forward.attached_file_size / 1024 / 1024
                    attachment_info += f" ({size_mb:.1f} MB)"
                    
                if message_str == "-":
                    message_str = attachment_info
                else:
                    message_str += f"\n{attachment_info}"
            
            # Combiner message et statut pour garder 4 colonnes comme les commentaires
            message_status = f"{message_str}"
            if status_str != "Non lu":
                message_status += f" ({status_str})"
            
            forward_data.append([
                Paragraph(forward.forwarded_by.nom_complet, text_style),
                Paragraph(forward.forwarded_to.nom_complet, text_style),
                Paragraph(message_status, text_style),
                Paragraph(date_str, text_style)
            ])
        
        forward_table = Table(forward_data, colWidths=[1.5*inch, 1.2*inch, 3.5*inch, 1.3*inch])
        forward_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkgreen),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('WORDWRAP', (0, 0), (-1, -1), 'CJK')
        ]))
        
        story.append(forward_table)
        story.append(Spacer(1, 20))
    
    # Si commentaires ou transmissions étaient sur la page 2, ajouter un saut de page avant le footer
    if comments or forwards:
        story.append(PageBreak())
    
    # Le footer est maintenant géré automatiquement par la classe NumberedCanvas
    # sur chaque page, donc on n'ajoute plus rien ici
    
    # Construire le PDF avec numérotation des pages
    doc.build(story, canvasmaker=NumberedCanvas)
    
    return pdf_path

def export_mail_list_pdf(courriers, filters):
    """Exporter une liste de courriers en PDF"""
    # Créer le dossier exports s'il n'existe pas
    exports_dir = 'exports'
    os.makedirs(exports_dir, exist_ok=True)
    
    # Nom du fichier PDF
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"liste_courriers_{timestamp}.pdf"
    pdf_path = os.path.join(exports_dir, filename)
    
    # Créer le document PDF en orientation paysage pour plus d'espace
    from reportlab.lib.pagesizes import landscape, A4
    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4), 
                          leftMargin=0.5*inch, rightMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Récupérer les paramètres système
    from models import ParametresSysteme
    parametres = ParametresSysteme.get_parametres()
    
    # Ajouter le logo s'il existe
    logo_path = None
    if parametres.logo_pdf:
        # Convertir l'URL relative en chemin de fichier absolu
        if parametres.logo_pdf.startswith('/uploads/'):
            logo_file_path = parametres.logo_pdf[9:]  # Enlever '/uploads/'
            logo_abs_path = os.path.join('uploads', logo_file_path)
            if os.path.exists(logo_abs_path):
                logo_path = logo_abs_path
    elif parametres.logo_url:
        # Convertir l'URL relative en chemin de fichier absolu
        if parametres.logo_url.startswith('/uploads/'):
            logo_file_path = parametres.logo_url[9:]  # Enlever '/uploads/'
            logo_abs_path = os.path.join('uploads', logo_file_path)
            if os.path.exists(logo_abs_path):
                logo_path = logo_abs_path
    
    if logo_path:
        try:
            # Charger l'image pour obtenir ses dimensions originales
            from PIL import Image as PILImage
            pil_img = PILImage.open(logo_path)
            original_width, original_height = pil_img.size
            
            # Calculer les dimensions en préservant le ratio (plus petit pour liste)
            max_width = 1.2*inch
            max_height = 0.8*inch
            
            # Calculer le ratio de redimensionnement
            width_ratio = max_width / original_width
            height_ratio = max_height / original_height
            ratio = min(width_ratio, height_ratio)
            
            # Nouvelles dimensions préservant le ratio
            new_width = original_width * ratio
            new_height = original_height * ratio
            
            logo = Image(logo_path, width=new_width, height=new_height)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 8))
        except Exception as e:
            print(f"Erreur chargement logo: {e}")  # Pour debug
    
    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=20,
        alignment=1,  # Centré
        textColor=colors.darkblue
    )
    
    # En-tête
    titre_pdf = parametres.titre_pdf or "Ministère des Mines"
    sous_titre_pdf = parametres.sous_titre_pdf or "Secrétariat Général"
    
    # En-tête pays - PREMIER ÉLÉMENT
    pays_style = ParagraphStyle(
        'PaysStyle',
        parent=styles['Normal'],
        fontSize=16,
        fontName='Helvetica-Bold',
        alignment=1,  # Center
        spaceAfter=10,
        textColor=colors.darkblue
    )
    pays_text = parametres.pays_pdf or "République Démocratique du Congo"
    story.append(Paragraph(pays_text, pays_style))
    
    title = Paragraph(f"{titre_pdf}<br/>{sous_titre_pdf}", title_style)
    story.append(title)
    story.append(Spacer(1, 15))
    
    # Titre de la liste
    liste_title = Paragraph("LISTE DES COURRIERS", styles['Heading2'])
    story.append(liste_title)
    story.append(Spacer(1, 10))
    
    # Informations sur les filtres appliqués
    filter_info = []
    if filters['search']:
        filter_info.append(f"Recherche: {filters['search']}")
    if filters['type_courrier']:
        type_display = 'Entrant' if filters['type_courrier'] == 'ENTRANT' else 'Sortant'
        filter_info.append(f"Type: {type_display}")
    if filters['statut']:
        filter_info.append(f"Statut: {filters['statut']}")
    if filters['date_from'] or filters['date_to']:
        period = "Période Enr.: "
        if filters['date_from']:
            period += f"du {filters['date_from']}"
        if filters['date_to']:
            period += f" au {filters['date_to']}"
        filter_info.append(period)
    
    if filters.get('date_redaction_from') or filters.get('date_redaction_to'):
        period_red = "Période Réd.: "
        if filters.get('date_redaction_from'):
            period_red += f"du {filters['date_redaction_from']}"
        if filters.get('date_redaction_to'):
            period_red += f" au {filters['date_redaction_to']}"
        filter_info.append(period_red)
    
    if filter_info:
        filter_text = " | ".join(filter_info)
        filter_para = Paragraph(f"Filtres appliqués: {filter_text}", styles['Normal'])
        story.append(filter_para)
        story.append(Spacer(1, 10))
    
    # Informations sur le rapport
    count = len(courriers)
    date_generation = format_date(datetime.now(), include_time=True)
    info_para = Paragraph(f"Total: {count} courrier{'s' if count > 1 else ''} | Généré le: {date_generation}", styles['Normal'])
    story.append(info_para)
    story.append(Spacer(1, 15))
    
    if not courriers:
        # Message si aucun courrier
        no_data = Paragraph("Aucun courrier trouvé avec les critères spécifiés.", styles['Normal'])
        story.append(no_data)
    else:
        # Style pour le texte dans les cellules avec wrapping
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            alignment=0,  # Left alignment
            leftIndent=2,
            rightIndent=2,
            spaceAfter=2
        )
        
        # Style pour les en-têtes
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            alignment=0,  # Left alignment
            textColor=colors.whitesmoke,
            leftIndent=2,
            rightIndent=2
        )
        
        # Déterminer si on a des courriers sortants pour ajuster le label de date
        has_sortant = any(c.type_courrier == 'SORTANT' for c in courriers)
        has_entrant = any(c.type_courrier == 'ENTRANT' for c in courriers)
        
        # Choisir le label approprié
        if has_sortant and not has_entrant:
            date_header = 'Date d\'Émission'
        elif has_entrant and not has_sortant:
            date_header = 'Date de Rédaction'
        else:
            # Mix des deux types
            date_header = 'Date Réd./Émission'
        
        # Créer le tableau des courriers avec le nouveau champ Observation
        headers = [
            Paragraph('N° Accusé de Réception', header_style),
            Paragraph('Type', header_style),
            Paragraph('N° de Référence', header_style),
            Paragraph('Contact Principal', header_style),
            Paragraph('Objet', header_style),
            Paragraph(date_header, header_style),
            Paragraph('Date d\'Enregistrement', header_style),
            Paragraph('Statut', header_style),
            Paragraph('En Copie', header_style),
            Paragraph('Observation', header_style)
        ]
        data = [headers]
        
        for courrier in courriers:
            # Contact principal selon le type - texte complet avec wrapping
            contact = courrier.expediteur if courrier.type_courrier == 'ENTRANT' else courrier.destinataire
            contact_text = contact if contact else 'Non spécifié'
            
            # Référence - texte complet avec wrapping
            reference_text = courrier.numero_reference if courrier.numero_reference else 'Non référencé'
            
            # Objet - texte complet avec wrapping
            objet_text = courrier.objet
            
            # Date de rédaction/émission formatée
            date_redaction_str = format_date(courrier.date_redaction)
            
            # Date d'enregistrement formatée
            date_enr_str = format_date(courrier.date_enregistrement, include_time=True).replace(' à ', '<br/>')
            
            # Type complet
            type_text = 'Courrier Entrant' if courrier.type_courrier == 'ENTRANT' else 'Courrier Sortant'
            
            # Statut formatté
            statut_text = courrier.statut.replace('_', ' ')
            
            # SG en copie (pour courriers entrants)
            sg_copie_text = '-'
            if courrier.type_courrier == 'ENTRANT' and hasattr(courrier, 'secretaire_general_copie'):
                if courrier.secretaire_general_copie is not None:
                    sg_copie_text = 'Oui' if courrier.secretaire_general_copie else 'Non'
            
            # Observation - champ vide pour remplissage manuel
            observation_text = ''
            
            row = [
                Paragraph(courrier.numero_accuse_reception, cell_style),
                Paragraph(type_text, cell_style),
                Paragraph(reference_text, cell_style),
                Paragraph(contact_text, cell_style),
                Paragraph(objet_text, cell_style),
                Paragraph(date_redaction_str, cell_style),
                Paragraph(date_enr_str, cell_style),
                Paragraph(statut_text, cell_style),
                Paragraph(sg_copie_text, cell_style),
                Paragraph(observation_text, cell_style)
            ]
            data.append(row)
        
        # Créer le tableau avec largeurs optimisées pour paysage A4 (11.69 x 8.27 inches utilisables)
        # Total width disponible: environ 10.69 inches (en retirant les marges)
        col_widths = [
            1.1*inch,   # N° Accusé de Réception
            0.8*inch,   # Type  
            1.0*inch,   # N° de Référence
            1.5*inch,   # Contact Principal
            2.5*inch,   # Objet (plus large pour le texte long)
            0.8*inch,   # Date de Rédaction/Émission
            0.9*inch,   # Date d'Enregistrement
            0.8*inch,   # Statut
            0.6*inch,   # SG Copie
            1.4*inch    # Observation (plus d'espace)
        ]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        
        # Style du tableau amélioré pour une meilleure lisibilité
        table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Alignement vertical en haut
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            
            # Corps du tableau avec plus d'espace pour le texte
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('ROWSIZE', (0, 1), (-1, -1), 'auto'),  # Hauteur automatique pour accommoder le texte
            
            # Bordures plus épaisses pour la lisibilité
            ('GRID', (0, 0), (-1, -1), 0.8, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.darkblue),  # Ligne plus épaisse sous l'en-tête
            
            # Alternance de couleur pour les lignes
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            
            # Style spécial pour la colonne Observation (dernière colonne)
            ('BACKGROUND', (-1, 1), (-1, -1), colors.lightyellow),  # Fond jaune clair pour Observation
            
            # Espacement entre les mots et retour à la ligne automatique
            ('WORDWRAP', (0, 0), (-1, -1), 'CJK'),
        ]))
        
        story.append(table)
    
    story.append(Spacer(1, 20))
    
    # Pied de page
    footer_lines = []
    
    # Texte footer configurable
    if parametres.texte_footer:
        footer_lines.append(parametres.texte_footer)
    
    # Copyright crypté
    copyright = parametres.get_copyright_decrypte()
    footer_lines.append(copyright)
    
    for line in footer_lines:
        footer = Paragraph(line, styles['Normal'])
        story.append(footer)
        story.append(Spacer(1, 4))
    
    # Construire le PDF
    doc.build(story)
    
    return pdf_path

def send_comment_notification(email, courrier_data):
    """Envoyer un email de notification pour les commentaires/annotations/instructions"""
    try:
        # Charger les paramètres système pour l'email
        parametres = get_system_config_for_email()
        if not parametres:
            logging.error("Impossible de charger les paramètres système pour l'email")
            return False
        
        # Textes selon le type de commentaire
        type_labels = {
            'comment': 'Commentaire',
            'annotation': 'Annotation', 
            'instruction': 'Instruction'
        }
        type_label = type_labels.get(courrier_data['comment_type'], 'Commentaire')
        
        subject = f"Nouveau {type_label} - {courrier_data['numero_accuse_reception']}"
        
        # Template HTML pour l'email
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background-color: #003087; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .details {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        .comment {{ background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 10px 0; }}
        .footer {{ background-color: #f1f1f1; padding: 10px; text-align: center; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>GEC - Nouveau {type_label}</h2>
    </div>
    <div class="content">
        <p>Bonjour,</p>
        <p>Un nouveau {type_label.lower()} a été ajouté sur un courrier dans le système GEC.</p>
        
        <div class="details">
            <h3>Détails du courrier :</h3>
            <p><strong>Numéro d'accusé de réception :</strong> {courrier_data['numero_accuse_reception']}</p>
            <p><strong>Type :</strong> {courrier_data['type_courrier']}</p>
            <p><strong>Objet :</strong> {courrier_data['objet']}</p>
            <p><strong>Contact :</strong> {courrier_data['expediteur']}</p>
            <p><strong>{type_label} ajouté par :</strong> {courrier_data['added_by']}</p>
        </div>
        
        <div class="comment">
            <h3>{type_label} :</h3>
            <p>{courrier_data['comment_text']}</p>
        </div>
        
        <p>Vous pouvez consulter ce courrier et répondre en vous connectant au système GEC.</p>
    </div>
    <div class="footer">
        <p>GEC - Système de Gestion du Courrier<br>
        Secrétariat Général - République Démocratique du Congo</p>
    </div>
</body>
</html>
        """
        
        # Envoyer l'email
        return send_email_from_system_config(email, subject, html_content)
        
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi de la notification de commentaire: {e}")
        return False
