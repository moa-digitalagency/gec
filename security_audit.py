#!/usr/bin/env python3
"""
Script d'audit de sécurité pour GEC Mines
Vérifie l'état de la sécurité et génère un rapport
"""

import os
import sys
import hashlib
from datetime import datetime, timedelta

def check_security_configuration():
    """Vérifie la configuration de sécurité"""
    
    print("=== AUDIT DE SÉCURITÉ GEC MINES ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    issues = []
    warnings = []
    
    # 1. Vérifier les variables d'environnement de sécurité
    print("\n1. Variables d'environnement de sécurité:")
    required_vars = ['GEC_MASTER_KEY', 'GEC_PASSWORD_SALT', 'SESSION_SECRET']
    
    for var in required_vars:
        if os.environ.get(var):
            print(f"   ✅ {var}: Configurée")
        else:
            print(f"   ❌ {var}: MANQUANTE")
            issues.append(f"Variable d'environnement manquante: {var}")
    
    # 2. Vérifier les permissions des fichiers
    print("\n2. Permissions des fichiers:")
    sensitive_files = ['.env', 'keys_backup_*.txt']
    
    for pattern in sensitive_files:
        if '*' in pattern:
            import glob
            files = glob.glob(pattern)
            for file in files:
                if os.path.exists(file):
                    stat = os.stat(file)
                    perms = oct(stat.st_mode)[-3:]
                    if perms != '600':
                        print(f"   ⚠️  {file}: Permissions {perms} (recommandé: 600)")
                        warnings.append(f"Permissions faibles sur {file}")
                    else:
                        print(f"   ✅ {file}: Permissions sécurisées")
        else:
            if os.path.exists(pattern):
                stat = os.stat(pattern)
                perms = oct(stat.st_mode)[-3:]
                if perms != '600':
                    print(f"   ⚠️  {pattern}: Permissions {perms} (recommandé: 600)")
                    warnings.append(f"Permissions faibles sur {pattern}")
                else:
                    print(f"   ✅ {pattern}: Permissions sécurisées")
    
    # 3. Vérifier la base de données
    print("\n3. Configuration de la base de données:")
    
    try:
        from app import app, db
        from models import User, Courrier
        
        with app.app_context():
            # Vérifier les colonnes cryptées
            user_count = User.query.count()
            encrypted_users = User.query.filter(User.email_encrypted.isnot(None)).count()
            
            courrier_count = Courrier.query.count()
            encrypted_courriers = Courrier.query.filter(Courrier.objet_encrypted.isnot(None)).count()
            
            print(f"   Utilisateurs: {encrypted_users}/{user_count} cryptés")
            print(f"   Courriers: {encrypted_courriers}/{courrier_count} cryptés")
            
            if encrypted_users < user_count:
                warnings.append(f"{user_count - encrypted_users} utilisateurs non cryptés")
            
            if encrypted_courriers < courrier_count:
                warnings.append(f"{courrier_count - encrypted_courriers} courriers non cryptés")
    
    except Exception as e:
        print(f"   ❌ Erreur lors de la vérification: {e}")
        issues.append("Impossible de vérifier la base de données")
    
    # 4. Vérifier l'intégrité des fichiers
    print("\n4. Intégrité des fichiers:")
    
    try:
        from app import app
        from models import Courrier
        from encryption_utils import encryption_manager
        
        with app.app_context():
            courriers_avec_fichiers = Courrier.query.filter(
                Courrier.fichier_chemin.isnot(None)
            ).all()
            
            files_ok = 0
            files_error = 0
            
            for courrier in courriers_avec_fichiers[:10]:  # Vérifier les 10 premiers
                file_path = os.path.join('uploads', courrier.fichier_chemin)
                if os.path.exists(file_path):
                    if courrier.verify_file_integrity(file_path):
                        files_ok += 1
                    else:
                        files_error += 1
                        warnings.append(f"Fichier corrompu: {courrier.fichier_nom}")
                else:
                    files_error += 1
                    warnings.append(f"Fichier manquant: {courrier.fichier_nom}")
            
            print(f"   Fichiers vérifiés: {files_ok} OK, {files_error} erreurs")
            
    except Exception as e:
        print(f"   ❌ Erreur lors de la vérification: {e}")
        warnings.append("Impossible de vérifier l'intégrité des fichiers")
    
    # 5. Vérifier les logs de sécurité
    print("\n5. Logs de sécurité:")
    
    # Vérifier si les logs d'audit existent
    if os.path.exists('security.log'):
        stat = os.stat('security.log')
        size = stat.st_size
        print(f"   ✅ security.log: {size} bytes")
    else:
        print("   ⚠️  security.log: Non trouvé")
        warnings.append("Logs de sécurité non configurés")
    
    # 6. Vérifier les dossiers sécurisés
    print("\n6. Sécurité des dossiers:")
    
    secure_dirs = ['uploads', 'exports', 'backups']
    for directory in secure_dirs:
        if os.path.exists(directory):
            stat = os.stat(directory)
            perms = oct(stat.st_mode)[-3:]
            if perms in ['755', '750']:
                print(f"   ✅ {directory}/: Permissions OK ({perms})")
            else:
                print(f"   ⚠️  {directory}/: Permissions {perms}")
                warnings.append(f"Permissions du dossier {directory} à vérifier")
        else:
            print(f"   ℹ️  {directory}/: N'existe pas")
    
    # Générer le rapport
    print("\n" + "=" * 50)
    print("RÉSUMÉ DE L'AUDIT")
    print("=" * 50)
    
    if not issues and not warnings:
        print("🎉 EXCELLENTE SÉCURITÉ! Aucun problème détecté.")
        return 0
    
    if issues:
        print(f"\n❌ PROBLÈMES CRITIQUES ({len(issues)}):")
        for issue in issues:
            print(f"   • {issue}")
    
    if warnings:
        print(f"\n⚠️  AVERTISSEMENTS ({len(warnings)}):")
        for warning in warnings:
            print(f"   • {warning}")
    
    print("\n📝 RECOMMANDATIONS:")
    if issues:
        print("1. Corrigez immédiatement les problèmes critiques")
        print("2. Relancez cet audit après corrections")
    if warnings:
        print("3. Planifiez la résolution des avertissements")
    
    print("4. Effectuez cet audit régulièrement")
    print("5. Surveillez les logs de sécurité")
    
    return len(issues)

def generate_security_report():
    """Génère un rapport de sécurité détaillé"""
    
    report_filename = f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(report_filename, 'w') as f:
        f.write("RAPPORT D'AUDIT DE SÉCURITÉ GEC MINES\n")
        f.write("=" * 50 + "\n")
        f.write(f"Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Rediriger la sortie vers le fichier temporairement
        original_stdout = sys.stdout
        sys.stdout = f
        
        try:
            check_security_configuration()
        finally:
            sys.stdout = original_stdout
    
    print(f"\n📊 Rapport détaillé sauvegardé: {report_filename}")
    return report_filename

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--report':
        generate_security_report()
    else:
        exit_code = check_security_configuration()
        sys.exit(exit_code)