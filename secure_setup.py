#!/usr/bin/env python3
"""
Script de configuration sécurisée pour GEC Mines
Génère et sauvegarde les clés de sécurité nécessaires
"""

import os
import sys
import secrets
import base64
from pathlib import Path

def generate_secure_keys():
    """Génère les clés de sécurité nécessaires"""
    
    print("=== Configuration Sécurisée GEC Mines ===")
    print()
    
    # Générer les clés
    master_key = secrets.token_bytes(32)  # 256 bits
    password_salt = secrets.token_bytes(32)  # 256 bits
    session_secret = secrets.token_urlsafe(64)
    
    # Encoder en base64
    master_key_b64 = base64.b64encode(master_key).decode('utf-8')
    password_salt_b64 = base64.b64encode(password_salt).decode('utf-8')
    
    print("✅ Clés de sécurité générées avec succès!")
    print()
    
    # Créer le fichier .env
    env_content = f"""# Clés de sécurité GEC Mines - GARDEZ CES CLÉS SECRÈTES!
# Généré le: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Clé maître pour le cryptage des données (AES-256)
GEC_MASTER_KEY={master_key_b64}

# Sel pour le hachage des mots de passe
GEC_PASSWORD_SALT={password_salt_b64}

# Clé secrète pour les sessions Flask
SESSION_SECRET={session_secret}

# Configuration de base de données (modifiez selon vos besoins)
# DATABASE_URL=postgresql://user:password@localhost/gec_mines
"""
    
    # Sauvegarder dans .env
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Fichier .env créé avec les variables d'environnement")
    print()
    
    # Créer un fichier de sauvegarde sécurisé
    backup_content = f"""=== SAUVEGARDE DES CLÉS GEC MINES ===
Date de génération: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️  IMPORTANT: Gardez ces informations dans un endroit sûr!
⚠️  Ces clés sont nécessaires pour décrypter vos données.
⚠️  Si vous les perdez, vos données cryptées seront irrécupérables!

Variables d'environnement à définir:

GEC_MASTER_KEY={master_key_b64}
GEC_PASSWORD_SALT={password_salt_b64}  
SESSION_SECRET={session_secret}

Instructions de déploiement:
1. Sur votre serveur de production, définissez ces variables d'environnement
2. Ne committez JAMAIS ces clés dans votre dépôt Git
3. Utilisez un gestionnaire de secrets en production (ex: Azure Key Vault, AWS Secrets Manager)
4. Effectuez des sauvegardes régulières de ces clés

Pour Replit:
Allez dans l'onglet "Secrets" et ajoutez chaque variable.

Pour les serveurs:
export GEC_MASTER_KEY="{master_key_b64}"
export GEC_PASSWORD_SALT="{password_salt_b64}"
export SESSION_SECRET="{session_secret}"

=== FIN DE LA SAUVEGARDE ===
"""
    
    backup_filename = f"keys_backup_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(backup_filename, 'w') as f:
        f.write(backup_content)
    
    print(f"✅ Sauvegarde créée: {backup_filename}")
    print()
    
    # Afficher les instructions
    print("🔐 INSTRUCTIONS DE SÉCURITÉ:")
    print("1. Le fichier .env a été créé pour le développement local")
    print("2. Un fichier de sauvegarde a été généré")
    print("3. Ajoutez ces variables à vos Secrets Replit:")
    print()
    print(f"   GEC_MASTER_KEY = {master_key_b64}")
    print(f"   GEC_PASSWORD_SALT = {password_salt_b64}")
    print(f"   SESSION_SECRET = {session_secret}")
    print()
    print("4. ⚠️  IMPORTANT: Ne partagez jamais ces clés!")
    print("5. ⚠️  Sauvegardez le fichier de backup dans un endroit sûr!")
    print()
    
    # Créer un gitignore si nécessaire
    gitignore_content = """
# Fichiers de sécurité - NE PAS COMMITTER!
.env
keys_backup_*.txt
*.key
*.pem

# Dossiers de cache
__pycache__/
*.py[cod]
*$py.class

# Fichiers temporaires
*.tmp
temp/
.temp/

# Logs de sécurité
security.log
audit.log
"""
    
    if not os.path.exists('.gitignore'):
        with open('.gitignore', 'w') as f:
            f.write(gitignore_content)
        print("✅ Fichier .gitignore créé")
    else:
        # Ajouter les règles de sécurité au gitignore existant
        with open('.gitignore', 'r') as f:
            content = f.read()
        
        if '.env' not in content:
            with open('.gitignore', 'a') as f:
                f.write('\n# Fichiers de sécurité\n.env\nkeys_backup_*.txt\n')
            print("✅ Règles de sécurité ajoutées au .gitignore")
    
    print()
    print("🚀 Configuration sécurisée terminée!")
    print("Votre application GEC Mines est maintenant configurée avec un cryptage fort.")

def migrate_existing_data():
    """Migre les données existantes vers le format crypté"""
    print("\n=== Migration des données existantes ===")
    
    try:
        # Import après configuration
        from app import app, db
        from models import User, Courrier
        from encryption_utils import encryption_manager
        
        with app.app_context():
            print("Migration des utilisateurs...")
            users = User.query.all()
            for user in users:
                if not user.email_encrypted and user.email:
                    try:
                        user.set_encrypted_email(user.email)
                        user.set_encrypted_nom_complet(user.nom_complet)
                        if user.matricule:
                            user.set_encrypted_matricule(user.matricule)
                        if user.fonction:
                            user.set_encrypted_fonction(user.fonction)
                        # Re-crypter le hash du mot de passe pour plus de sécurité
                        user.set_encrypted_password(user.password_hash)
                    except Exception as e:
                        print(f"Erreur lors du cryptage des données utilisateur {user.username}: {e}")
            
            print("Migration des courriers...")
            courriers = Courrier.query.all()
            for courrier in courriers:
                if not courrier.objet_encrypted and courrier.objet:
                    try:
                        courrier.set_encrypted_objet(courrier.objet)
                        if courrier.expediteur:
                            courrier.set_encrypted_expediteur(courrier.expediteur)
                        if courrier.destinataire:
                            courrier.set_encrypted_destinataire(courrier.destinataire)
                        if courrier.numero_reference:
                            courrier.set_encrypted_reference(courrier.numero_reference)
                        
                        # Calculer le checksum des fichiers existants
                        if courrier.fichier_chemin and not courrier.fichier_checksum:
                            file_path = os.path.join('uploads', courrier.fichier_chemin)
                            if os.path.exists(file_path):
                                courrier.set_file_checksum(file_path)
                    except Exception as e:
                        print(f"Erreur lors du cryptage des données courrier {courrier.numero_accuse_reception}: {e}")
            
            db.session.commit()
            print("✅ Migration terminée avec succès!")
            
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        print("La migration peut être effectuée manuellement plus tard.")

if __name__ == '__main__':
    generate_secure_keys()
    
    # Demander si l'utilisateur veut migrer les données existantes
    if len(sys.argv) > 1 and sys.argv[1] == '--migrate':
        migrate_existing_data()
    else:
        print("\nPour migrer les données existantes, exécutez:")
        print("python secure_setup.py --migrate")