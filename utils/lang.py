import json
import os
from flask import session, request

# Languages disponibles
AVAILABLE_LANGUAGES = {
    'fr': {'name': 'Français', 'flag': '🇫🇷'},
    'en': {'name': 'English', 'flag': '🇺🇸'}
}

def get_available_languages():
    """Retourne la liste des langues disponibles"""
    languages = {}
    lang_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lang')
    
    if os.path.exists(lang_dir):
        for filename in os.listdir(lang_dir):
            if filename.endswith('.json'):
                lang_code = filename[:-5]  # Remove .json
                if lang_code in AVAILABLE_LANGUAGES:
                    languages[lang_code] = AVAILABLE_LANGUAGES[lang_code]
    
    return languages

def get_current_language():
    """Obtient la langue actuelle depuis la session ou les préférences utilisateur"""
    # 1. Vérifier la session
    if 'language' in session:
        return session['language']
    
    # 2. Vérifier les préférences du navigateur
    if hasattr(request, 'accept_languages'):
        best_match = request.accept_languages.best_match(['fr', 'en'])
        if best_match:
            return best_match
    
    # 3. Langue par défaut
    return 'fr'

def set_language(lang_code):
    """Définit la langue dans la session"""
    if lang_code in get_available_languages():
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