"""
Script pour afficher les clés de chiffrement configurées dans l'environnement
Affiche uniquement les premiers/derniers caractères pour des raisons de sécurité
"""

import os
import sys

def load_env_file(env_file='.env'):
    """Charge les variables depuis le fichier .env"""
    if os.path.exists(env_file):
        print(f"📂 Lecture du fichier: {env_file}\n")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value.strip()
        return True
    return False

def mask_key(key_value):
    """Masque la clé en affichant seulement début et fin"""
    if not key_value:
        return None
    if len(key_value) <= 8:
        return "****"
    return f"{key_value[:4]}...{key_value[-4:]}"

def show_encryption_keys():
    """Affiche les clés de chiffrement configurées"""
    
    # Charger .env si disponible
    env_loaded = load_env_file()
    
    if not env_loaded:
        print("⚠️  Fichier .env non trouvé - lecture depuis les variables d'environnement système\n")
    
    # Liste des clés à vérifier
    encryption_keys = {
        'GEC_MASTER_KEY': 'Clé maître de chiffrement',
        'GEC_PASSWORD_SALT': 'Sel pour hachage des mots de passe',
        'DATABASE_URL': 'URL de la base de données',
        'SESSION_SECRET': 'Secret pour les sessions Flask',
        'SENDGRID_API_KEY': 'Clé API SendGrid'
    }
    
    print("🔐 CLÉS DE CHIFFREMENT CONFIGURÉES")
    print("=" * 60)
    
    for key, description in encryption_keys.items():
        value = os.environ.get(key)
        
        if value:
            if key in ['GEC_MASTER_KEY', 'GEC_PASSWORD_SALT', 'SENDGRID_API_KEY', 'SESSION_SECRET']:
                # Masquer les clés sensibles
                masked = mask_key(value)
                print(f"\n✅ {key}")
                print(f"   Description: {description}")
                print(f"   Valeur: {masked}")
                print(f"   Longueur: {len(value)} caractères")
            else:
                # Afficher DATABASE_URL en clair (pas de secret)
                print(f"\n✅ {key}")
                print(f"   Description: {description}")
                print(f"   Valeur: {value}")
        else:
            print(f"\n❌ {key}")
            print(f"   Description: {description}")
            print(f"   Status: NON CONFIGURÉE")
    
    print("\n" + "=" * 60)
    
    # Afficher les valeurs COMPLÈTES (si demandé)
    print("\n⚠️  ATTENTION: Pour voir les valeurs COMPLÈTES des clés:")
    print("   Windows PowerShell: echo $env:GEC_MASTER_KEY")
    print("   Linux/macOS: echo $GEC_MASTER_KEY")
    print("\n   Ou lisez directement le fichier .env avec un éditeur de texte")
    
    # Vérifier les clés critiques
    print("\n📋 ÉTAT DES CLÉS CRITIQUES:")
    critical_keys = ['GEC_MASTER_KEY', 'GEC_PASSWORD_SALT']
    all_critical_present = all(os.environ.get(key) for key in critical_keys)
    
    if all_critical_present:
        print("✅ Toutes les clés critiques sont configurées")
    else:
        print("❌ Certaines clés critiques sont manquantes!")
        print("\n⚠️  L'application va générer des clés temporaires au démarrage")
        print("   Pour une configuration persistante, ajoutez-les dans le fichier .env:")
        for key in critical_keys:
            if not os.environ.get(key):
                print(f"   - {key}=<votre_clé_ici>")

if __name__ == "__main__":
    show_encryption_keys()
