import json
import os
from flask import session, request

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
    lang_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lang')
    
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
    lang_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lang')
    
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

def get_current_language():
    """Obtient la langue actuelle depuis la session ou les préférences utilisateur"""
    available_languages = get_available_languages()
    
    # 1. Vérifier la session en premier
    if 'language' in session and session['language']:
        lang = session['language']
        if lang in available_languages:
            return lang
    
    # 2. Si utilisateur connecté, vérifier ses préférences
    try:
        from flask_login import current_user
        if current_user.is_authenticated and hasattr(current_user, 'langue') and current_user.langue:
            if current_user.langue in available_languages:
                # Mettre à jour la session pour la cohérence
                session['language'] = current_user.langue
                return current_user.langue
    except Exception:
        pass  # Ignorer les erreurs si current_user n'est pas disponible
    
    # 3. Vérifier les préférences du navigateur
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
    
    # 4. Langue par défaut (français si disponible, sinon la première disponible)
    default_lang = 'fr' if 'fr' in available_languages else list(available_languages.keys())[0] if available_languages else 'fr'
    session['language'] = default_lang
    return default_lang

def set_language(lang_code):
    """Définit la langue dans la session"""
    available_languages = get_available_languages()
    if lang_code in available_languages:
        session['language'] = lang_code
        return True
    return False

def load_translations(lang_code='fr'):
    """Charge les traductions pour une langue donnée"""
    lang_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lang')
    lang_file = os.path.join(lang_dir, f'{lang_code}.json')
    
    if not os.path.exists(lang_file):
        # Fallback vers français
        lang_file = os.path.join(lang_dir, 'fr.json')
    
    try:
        with open(lang_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Retourner un dictionnaire vide en cas d'erreur
        return {}

def t(key, lang_code=None, **kwargs):
    """Fonction de traduction - équivalent de translate"""
    if lang_code is None:
        lang_code = get_current_language()
    
    translations = load_translations(lang_code)
    
    # Naviguer dans les clés imbriquées (ex: "auth.login")
    keys = key.split('.')
    value = translations
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            # Retourner la clé si traduction non trouvée
            return key
    
    # Gestion des paramètres (ex: "Bonjour {name}")
    if kwargs and isinstance(value, str):
        try:
            return value.format(**kwargs)
        except (KeyError, ValueError):
            return value
    
    return value

def get_user_language(user):
    """Obtient la langue préférée d'un utilisateur"""
    if user and hasattr(user, 'langue') and user.langue:
        return user.langue
    return get_current_language()

# Template function for Flask
def init_language_support(app):
    """Initialise le support des langues dans Flask"""
    
    @app.context_processor
    def inject_language():
        """Injecte les fonctions de langue dans tous les templates"""
        current_lang = get_current_language()
        return {
            't': lambda key, **kwargs: t(key, current_lang, **kwargs),
            'current_language': current_lang,
            'available_languages': get_available_languages(),
            'get_available_languages': get_available_languages
        }
    
    @app.before_request
    def before_request():
        """Exécuté avant chaque requête pour gérer la langue"""
        # Si l'utilisateur est connecté, utiliser sa langue préférée
        from flask_login import current_user
        if current_user.is_authenticated and hasattr(current_user, 'langue'):
            if current_user.langue and current_user.langue != session.get('language'):
                session['language'] = current_user.langue