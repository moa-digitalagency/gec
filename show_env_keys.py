#!/usr/bin/env python3
"""
Script pour afficher toutes les variables d'environnement GEC
Utilisé pour vérifier la configuration et récupérer les clés
"""

import os
import sys

def show_env_keys():
    """Affiche toutes les variables d'environnement importantes pour GEC"""
    
    print("\n" + "="*80)
    print("VARIABLES D'ENVIRONNEMENT GEC")
    print("GEC ENVIRONMENT VARIABLES")
    print("="*80 + "\n")
    
    # Liste des variables d'environnement importantes
    env_vars = {
        'DATABASE_URL': 'URL de connexion PostgreSQL / PostgreSQL connection URL',
        'SESSION_SECRET': 'Clé secrète Flask / Flask session secret',
        'GEC_MASTER_KEY': 'Clé maître de chiffrement / Master encryption key',
        'GEC_PASSWORD_SALT': 'Sel pour mots de passe / Password salt',
        'ADMIN_PASSWORD': 'Mot de passe admin par défaut / Default admin password',
        'SMTP_SERVER': 'Serveur SMTP / SMTP server',
        'SMTP_PORT': 'Port SMTP / SMTP port',
        'SMTP_EMAIL': 'Email expéditeur / Sender email',
        'SMTP_PASSWORD': 'Mot de passe SMTP / SMTP password',
        'SMTP_USE_TLS': 'Utiliser TLS / Use TLS',
        'SENDGRID_API_KEY': 'Clé API SendGrid / SendGrid API key'
    }
    
    # Variables critiques qui doivent être masquées partiellement
    sensitive_vars = ['DATABASE_URL', 'SESSION_SECRET', 'GEC_MASTER_KEY', 'GEC_PASSWORD_SALT', 
                      'ADMIN_PASSWORD', 'SMTP_PASSWORD', 'SENDGRID_API_KEY']
    
    print("📋 VARIABLES CONFIGURÉES / CONFIGURED VARIABLES:")
    print("-" * 80 + "\n")
    
    configured_count = 0
    missing_count = 0
    
    for var_name, description in env_vars.items():
        value = os.environ.get(var_name)
        
        if value:
            configured_count += 1
            # Masquer partiellement les valeurs sensibles
            if var_name in sensitive_vars:
                if len(value) > 10:
                    masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:]
                else:
                    masked_value = "*" * len(value)
                print(f"✅ {var_name:<25} = {masked_value}")
            else:
                print(f"✅ {var_name:<25} = {value}")
            print(f"   ({description})")
            print()
        else:
            missing_count += 1
            print(f"❌ {var_name:<25} = NON CONFIGURÉE / NOT SET")
            print(f"   ({description})")
            print()
    
    print("-" * 80)
    print(f"\n📊 RÉSUMÉ / SUMMARY:")
    print(f"   Variables configurées / Configured: {configured_count}/{len(env_vars)}")
    print(f"   Variables manquantes / Missing: {missing_count}/{len(env_vars)}")
    print()
    
    # Afficher les variables critiques manquantes
    critical_vars = ['DATABASE_URL', 'SESSION_SECRET', 'GEC_MASTER_KEY', 'GEC_PASSWORD_SALT']
    critical_missing = [var for var in critical_vars if not os.environ.get(var)]
    
    if critical_missing:
        print("⚠️  VARIABLES CRITIQUES MANQUANTES / CRITICAL MISSING VARIABLES:")
        for var in critical_missing:
            print(f"   - {var}")
        print()
        print("💡 Pour générer les clés manquantes / To generate missing keys:")
        print("   python generate_keys.py")
        print()
    
    # Option pour afficher les valeurs complètes (pour export)
    if '--export' in sys.argv or '--full' in sys.argv:
        print("\n" + "="*80)
        print("⚠️  MODE EXPORT - VALEURS COMPLÈTES / FULL VALUES (À GARDER SECRET / KEEP SECRET)")
        print("="*80 + "\n")
        
        for var_name in env_vars.keys():
            value = os.environ.get(var_name)
            if value:
                print(f"{var_name}={value}")
        print()
        print("⚠️  ATTENTION: Ne partagez jamais ces valeurs publiquement!")
        print("⚠️  WARNING: Never share these values publicly!")
        print()
    else:
        print("💡 Pour voir les valeurs complètes (export) / To see full values (export):")
        print("   python show_env_keys.py --export")
        print()
    
    # Afficher des suggestions si des variables sont manquantes
    if missing_count > 0:
        print("📝 SUGGESTIONS:")
        print("-" * 80)
        print()
        print("1. Pour générer les clés de sécurité / To generate security keys:")
        print("   python generate_keys.py")
        print()
        print("2. Pour créer un fichier .env / To create a .env file:")
        print("   Copiez le modèle depuis README-ENV.md")
        print("   Copy the template from README-ENV.md")
        print()
        print("3. Sur Replit, utilisez l'onglet Secrets / On Replit, use the Secrets tab")
        print()
    
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        show_env_keys()
    except Exception as e:
        print(f"❌ Erreur / Error: {e}")
        sys.exit(1)
