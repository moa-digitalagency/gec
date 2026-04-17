import os
import uuid
import json
import logging
from datetime import datetime
from flask import request, session

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff", "tif"}

# Configuration des langues par défaut
DEFAULT_LANGUAGE_CONFIG = {
    "fr": {"name": "Français", "flag": "🇫🇷", "enabled": True},
    "en": {"name": "English", "flag": "🇺🇸", "enabled": True},
    "es": {"name": "Español", "flag": "🇪🇸", "enabled": True},
    "de": {"name": "Deutsch", "flag": "🇩🇪", "enabled": True},
    "it": {"name": "Italiano", "flag": "🇮🇹", "enabled": False},
    "pt": {"name": "Português", "flag": "🇵🇹", "enabled": False},
    "ar": {"name": "العربية", "flag": "🇸🇦", "enabled": False},
    "zh": {"name": "中文", "flag": "🇨🇳", "enabled": False},
    "ja": {"name": "日本語", "flag": "🇯🇵", "enabled": False},
    "ru": {"name": "Русский", "flag": "🇷🇺", "enabled": False}
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

def validate_backup_integrity(backup_filename):
    """Valider l'intégrité d'une sauvegarde"""
    import zipfile
    import json as json_module
    
    backup_path = os.path.join('backups', backup_filename)
    if not os.path.exists(backup_path):
        return False, "Fichier de sauvegarde introuvable"
    
    try:
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            # Vérifier les fichiers essentiels
            required_files = ['backup_manifest.json']
            optional_files = ['database_backup.sql', 'database.db', 'environment_variables_documentation.json']
            
            file_list = zipf.namelist()
            
            # Vérifier le manifeste
            if 'backup_manifest.json' not in file_list:
                return False, "Manifeste de sauvegarde manquant"
            
            # Lire le manifeste pour vérifier la version et les composants
            manifest_data = zipf.read('backup_manifest.json')
            manifest = json_module.loads(manifest_data.decode('utf-8'))
            
            # Validation des composants critiques
            issues = []
            
            # Vérifier la base de données
            if 'database_backup.sql' not in file_list and 'database.db' not in file_list:
                issues.append("Aucune sauvegarde de base de données trouvée")
            
            # Vérifier les dossiers importants
            important_folders = ['static/uploads/', 'forward_attachments/', 'lang/', 'templates/', 'static/']
            for folder in important_folders:
                folder_files = [f for f in file_list if f.startswith(folder)]
                if not folder_files and folder != 'forward_attachments/':  # forward_attachments peut être vide
                    issues.append(f"Dossier {folder} vide ou manquant")
            
            if issues:
                return False, "Problèmes détectés: " + "; ".join(issues)
            
            return True, f"Sauvegarde valide (version {manifest.get('version', 'inconnue')})"
            
    except Exception as e:
        return False, f"Erreur lors de la validation: {str(e)}"

def create_pre_update_backup():
    """Créer une sauvegarde spéciale avant mise à jour avec protection des paramètres"""
    import json as json_module
    import logging
    import zipfile
    import subprocess
    import tempfile
    from datetime import datetime
    
    # Créer le dossier de sauvegarde s'il n'existe pas
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    
    # Nom spécial pour les sauvegardes de sécurité
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"backup_security_pre_update_{timestamp}.zip"
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
            'SESSION_SECRET': 'Clé secrète pour les sessions Flask (requise)',
            'GEC_MASTER_KEY': 'Clé maître pour le chiffrement (optionnelle)',
            'GEC_PASSWORD_SALT': 'Sel pour le hashage des mots de passe (optionnel)',
            'backup_created': datetime.now().isoformat(),
            'backup_type': 'pre_update_security'
        }
        
        # Ajouter la documentation d'environnement au zip
        env_doc_json = json_module.dumps(env_doc, indent=2, ensure_ascii=False)
        zipf.writestr('environment_variables_documentation.json', env_doc_json)
        
        # Sauvegarder les templates
        if os.path.exists('templates'):
            for root, dirs, files in os.walk('templates'):
                for file in files:
                    if file.endswith('.html'):
                        file_path = os.path.join(root, file)
                        arc_path = os.path.relpath(file_path, '.')
                        zipf.write(file_path, arc_path)
        
        # Sauvegarder les fichiers statiques importants
        if os.path.exists('static'):
            important_static = ['css', 'js', 'favicon.svg']
            for item in important_static:
                item_path = os.path.join('static', item)
                if os.path.exists(item_path):
                    if os.path.isfile(item_path):
                        zipf.write(item_path, os.path.relpath(item_path, '.'))
                    else:
                        for root, dirs, files in os.walk(item_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arc_path = os.path.relpath(file_path, '.')
                                zipf.write(file_path, arc_path)
        
        # Sauvegarder les exports
        if os.path.exists('exports'):
            for root, dirs, files in os.walk('exports'):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, '.')
                    zipf.write(file_path, arc_path)
        
        # SECURITY FIX: Inclure les paramètres critiques DANS l'archive zip
        try:
            from models import ParametresSysteme
            
            # Récupérer tous les paramètres système critiques
            critical_params = [
                'nom_logiciel', 'nom_organisation', 'adresse_organisation', 
                'telephone_organisation', 'email_organisation', 'logo_organisation',
                'fuseau_horaire', 'format_date', 'langue_defaut', 
                'resend_api_key', 'email_provider', 'smtp_server', 'smtp_port',
                'smtp_username', 'smtp_password', 'smtp_use_tls',
                'notify_superadmin_new_mail', 'titre_responsable_structure'
            ]
            
            protected_settings = {
                'backup_info': {
                    'created': datetime.now().isoformat(),
                    'type': 'pre_update_security',
                    'version': '2.0'
                },
                'critical_settings': {}
            }
            
            for param in critical_params:
                value = ParametresSysteme.get_valeur(param)
                if value:
                    protected_settings['critical_settings'][param] = value
            
            # Sauvegarder les paramètres critiques DANS l'archive zip (SÉCURISÉ)
            protected_json = json_module.dumps(protected_settings, indent=2, ensure_ascii=False)
            zipf.writestr('protected_settings.json', protected_json)
            
            logging.info(f"Paramètres critiques sauvegardés de manière sécurisée dans l'archive")
            
        except Exception as e:
            logging.warning(f"Impossible de sauvegarder les paramètres critiques: {e}")
        
        # Créer le manifeste de sauvegarde
        manifest = {
            'version': '2.0',
            'created': datetime.now().isoformat(),
            'type': 'pre_update_security',
            'components': {
                'database': True,
                'uploads': os.path.exists('uploads'),
                'forward_attachments': os.path.exists('forward_attachments'),
                'languages': os.path.exists('lang'),
                'templates': os.path.exists('templates'),
                'static_files': os.path.exists('static'),
                'exports': os.path.exists('exports'),
                'protected_settings': True
            }
        }
        
        manifest_json = json_module.dumps(manifest, indent=2, ensure_ascii=False)
        zipf.writestr('backup_manifest.json', manifest_json)
    
    logging.info(f"Sauvegarde de sécurité pré-mise à jour créée: {backup_filename}")
    return backup_filename

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
            'RESEND_API_KEY': 'Clé API Resend pour les emails',
            'SMTP_SERVER': 'Serveur SMTP pour les emails',
            'SMTP_PORT': 'Port SMTP',
            'SMTP_EMAIL': 'Adresse email SMTP',
            'SMTP_PASSWORD': 'Mot de passe SMTP',
            'SMTP_USE_TLS': 'Utiliser TLS pour SMTP (true/false)',
            'SESSION_SECRET': 'Clé secrète pour les sessions Flask'
        }
        
        import json as json_module
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as env_file:
            json_module.dump(env_doc, env_file, indent=2, ensure_ascii=False)
            zipf.write(env_file.name, 'environment_variables_documentation.json')
            os.unlink(env_file.name)
        
        # Ajouter un manifeste de sauvegarde complet
        import json as json_module
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
            json_module.dump(manifest, manifest_file, indent=2)
            zipf.write(manifest_file.name, 'backup_manifest.json')
            os.unlink(manifest_file.name)
        
        # Sauvegarder les fichiers de configuration et migration
        config_files = [
            'app.py', 'models.py', 'utils.py', 'views.py', 
            'migration_utils.py', 'email_utils.py', 'security_utils.py',
            'project-dependencies.txt', 'requirements.txt', 'replit.md'
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
        static_folders = ['static/css', 'static/js', 'static/img', 'static/vendor']
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
            # Créer une sauvegarde des uploads existants
            if os.path.exists('uploads'):
                upload_backup_name = f"uploads_backup_{int(time.time())}"
                shutil.move('uploads', upload_backup_name)
            # Restaurer les nouveaux uploads
            shutil.copytree(uploads_backup_path, 'uploads')
        
        # Restaurer les pièces jointes des transmissions
        forward_attachments_backup_path = os.path.join(temp_dir, 'forward_attachments')
        if os.path.exists(forward_attachments_backup_path):
            # Créer une sauvegarde des pièces jointes existantes
            if os.path.exists('forward_attachments'):
                forward_backup_name = f"forward_attachments_backup_{int(time.time())}"
                shutil.move('forward_attachments', forward_backup_name)
            # Restaurer les nouvelles pièces jointes
            shutil.copytree(forward_attachments_backup_path, 'forward_attachments')
        
        # Restaurer tous les templates
        templates_backup_path = os.path.join(temp_dir, 'templates')
        if os.path.exists(templates_backup_path):
            # Créer une sauvegarde des templates existants
            if os.path.exists('templates'):
                templates_backup_name = f"templates_backup_{int(time.time())}"
                shutil.move('templates', templates_backup_name)
            # Restaurer les nouveaux templates
            shutil.copytree(templates_backup_path, 'templates')
        
        # Restaurer les fichiers statiques
        static_backup_path = os.path.join(temp_dir, 'static')
        if os.path.exists(static_backup_path):
            # Créer une sauvegarde des fichiers statiques existants
            if os.path.exists('static'):
                static_backup_name = f"static_backup_{int(time.time())}"
                shutil.move('static', static_backup_name)
            # Restaurer les nouveaux fichiers statiques
            shutil.copytree(static_backup_path, 'static')
        
        # Restaurer les exports
        exports_backup_path = os.path.join(temp_dir, 'exports')
        if os.path.exists(exports_backup_path):
            # Créer le dossier exports s'il n'existe pas
            os.makedirs('exports', exist_ok=True)
            # Copier les fichiers d'export
            for file in os.listdir(exports_backup_path):
                src_file = os.path.join(exports_backup_path, file)
                dst_file = os.path.join('exports', file)
                if os.path.isfile(src_file):
                    # Créer une sauvegarde si le fichier existe déjà
                    if os.path.exists(dst_file):
                        backup_name = f"{dst_file}.backup_{int(time.time())}"
                        shutil.copy2(dst_file, backup_name)
                    shutil.copy2(src_file, dst_file)
        
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
            'project-dependencies.txt', 'requirements.txt', 'replit.md'
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
        
        # Afficher un message informatif pour l'administrateur sur les variables d'environnement
        env_doc_path = os.path.join(temp_dir, 'environment_variables_documentation.json')
        if os.path.exists(env_doc_path):
            logging.info("Documentation des variables d'environnement disponible dans environment_variables_documentation.json")
            logging.info("Vérifiez que toutes les variables requises sont configurées avant de redémarrer l'application")
        
        # Vérifier le manifeste de sauvegarde pour compatibilité
        manifest_path = os.path.join(temp_dir, 'backup_manifest.json')
        if os.path.exists(manifest_path):
            try:
                import json as json_module
                with open(manifest_path, 'r') as f:
                    manifest = json_module.load(f)
                logging.info(f"Restauration depuis sauvegarde version {manifest.get('version', 'inconnue')}")
                logging.info(f"Type de base de données: {manifest.get('database_type', 'inconnue')}")
                logging.info(f"Éléments restaurés: {', '.join(manifest.get('files_included', []))}")
            except Exception as e:
                logging.warning(f"Impossible de lire le manifeste de sauvegarde: {e}")
    
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
            critical_files = ['database_backup.sql', 'database.db', 'static/uploads/', 'lang/']
            found_critical = any(any(f.startswith(critical) for f in files_in_zip) for critical in critical_files)
            
            if not found_critical:
                return False, "Aucun fichier critique trouvé dans la sauvegarde"
            
            return True, "Sauvegarde intègre"
            
    except Exception as e:
        return False, f"Erreur lors de la vérification: {str(e)}"

def log_activity(user_id, action, description, courrier_id=None):
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

