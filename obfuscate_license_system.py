#!/usr/bin/env python3
"""
Script d'obfuscation et de sécurisation des fichiers du système de licence
Rend les fichiers critiques du système de licence plus difficiles à craquer
"""

import os
import shutil
import base64
import zlib
import random
import string

def obfuscate_python_file(filepath: str, output_path: str = None) -> bool:
    """Obfusque un fichier Python"""
    try:
        if not output_path:
            output_path = filepath
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Compresse le contenu
        compressed = zlib.compress(content.encode())
        
        # Encode en base64
        encoded = base64.b64encode(compressed).decode()
        
        # Génère des noms de variables aléatoires
        var_names = [''.join(random.choices(string.ascii_lowercase, k=8)) for _ in range(5)]
        
        # Crée le code obfusqué
        obfuscated_code = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import zlib
{var_names[0]} = "{encoded}"
{var_names[1]} = base64.b64decode({var_names[0]})
{var_names[2]} = zlib.decompress({var_names[1]})
{var_names[3]} = {var_names[2]}.decode()
exec({var_names[3]})
"""
        
        # Sauvegarde le fichier obfusqué
        with open(output_path, 'w') as f:
            f.write(obfuscated_code)
        
        return True
        
    except Exception as e:
        print(f"Erreur obfuscation {filepath}: {e}")
        return False

def secure_license_files():
    """Sécurise les fichiers du système de licence"""
    files_to_secure = [
        ('secure_license_system.py', '_secure_license_system_obf.py'),
        ('license_system.py', '_license_system_obf.py'),
        ('license_generator.py', '_license_generator_obf.py')
    ]
    
    print("🔒 Sécurisation des fichiers du système de licence...")
    
    for original, obfuscated in files_to_secure:
        if os.path.exists(original):
            print(f"  • Obfuscation de {original}...")
            
            if obfuscate_python_file(original, obfuscated):
                print(f"    ✅ {obfuscated} créé")
                
                # Renomme l'original avec un préfixe caché
                backup_name = f".{original}.backup"
                shutil.move(original, backup_name)
                print(f"    📁 Fichier original sauvegardé dans {backup_name}")
                
                # Renomme le fichier obfusqué
                shutil.move(obfuscated, original)
                print(f"    🔄 {obfuscated} activé comme {original}")
            else:
                print(f"    ❌ Échec obfuscation de {original}")
        else:
            print(f"  ⚠️  Fichier {original} introuvable")
    
    # Crée des fichiers de distraction
    print("\n🎭 Création de fichiers de distraction...")
    
    distraction_files = [
        ('fake_license_check.py', 'def check_license(): return True'),
        ('license_bypass.py', 'BYPASS_CODE = "NOT_REAL_BYPASS"'),
        ('dummy_validator.py', 'class DummyValidator: pass')
    ]
    
    for filename, content in distraction_files:
        with open(filename, 'w') as f:
            f.write(f"# Fichier de distraction - Ne pas utiliser\n{content}\n")
        print(f"  • Créé {filename}")
    
    # Cache des fichiers critiques
    print("\n👻 Dissimulation de fichiers critiques...")
    
    critical_files = [
        'gec_licenses.xlsx',
        'keys_backup_*.txt'
    ]
    
    for pattern in critical_files:
        import glob
        for filepath in glob.glob(pattern):
            if os.path.exists(filepath):
                hidden_name = f".{filepath}"
                shutil.move(filepath, hidden_name)
                print(f"  • {filepath} → {hidden_name}")
    
    print("\n✨ Sécurisation terminée !")
    print("📋 Fichiers sécurisés:")
    print("   - Fichiers Python obfusqués et compressés")
    print("   - Fichiers originaux sauvegardés avec préfixe '.'")
    print("   - Fichiers de distraction créés")
    print("   - Fichiers critiques cachés")
    
    return True

def restore_license_files():
    """Restaure les fichiers originaux du système de licence"""
    files_to_restore = [
        'secure_license_system.py',
        'license_system.py', 
        'license_generator.py'
    ]
    
    print("🔓 Restauration des fichiers originaux...")
    
    for filename in files_to_restore:
        backup_name = f".{filename}.backup"
        
        if os.path.exists(backup_name):
            # Supprime le fichier obfusqué
            if os.path.exists(filename):
                os.remove(filename)
            
            # Restaure l'original
            shutil.move(backup_name, filename)
            print(f"  ✅ {filename} restauré")
        else:
            print(f"  ⚠️  Backup {backup_name} introuvable")
    
    # Supprime les fichiers de distraction
    distraction_files = [
        'fake_license_check.py',
        'license_bypass.py', 
        'dummy_validator.py'
    ]
    
    for filename in distraction_files:
        if os.path.exists(filename):
            os.remove(filename)
            print(f"  🗑️  Supprimé {filename}")
    
    # Restaure les fichiers cachés
    import glob
    for filepath in glob.glob(".*"):
        if filepath.startswith('.gec_licenses') or filepath.startswith('.keys_backup'):
            original_name = filepath[1:]  # Supprime le point
            if not os.path.exists(original_name):
                shutil.move(filepath, original_name)
                print(f"  👁️  {filepath} → {original_name}")
    
    print("✅ Restauration terminée !")

def main():
    """Menu principal"""
    print("🛡️  Utilitaire de Sécurisation du Système de Licence GEC Mines")
    print("=" * 60)
    print("1. Sécuriser les fichiers (obfuscation + dissimulation)")
    print("2. Restaurer les fichiers originaux")
    print("3. Quitter")
    
    while True:
        choice = input("\nVotre choix (1-3): ").strip()
        
        if choice == '1':
            secure_license_files()
            break
        elif choice == '2':
            restore_license_files()
            break
        elif choice == '3':
            print("👋 Au revoir !")
            break
        else:
            print("❌ Choix invalide. Veuillez choisir 1, 2 ou 3.")

if __name__ == "__main__":
    main()