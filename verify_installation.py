#!/usr/bin/env python3
"""
Script de vérification de l'installation GEC
Vérifie que tous les imports sont corrects et qu'il n'y a pas de référence à PieceJointe
"""

import os
import sys

def check_piecejointe_imports():
    """Vérifie qu'il n'y a pas d'import de PieceJointe"""
    print("🔍 Vérification des imports PieceJointe...")
    
    python_files = [
        'export_import_utils.py',
        'models.py',
        'views.py',
        'utils.py',
        'app.py',
        'email_utils.py',
        'security_utils.py',
        'performance_utils.py'
    ]
    
    errors = []
    
    for filename in python_files:
        if not os.path.exists(filename):
            print(f"  ⚠️  {filename} non trouvé")
            continue
            
        with open(filename, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if 'PieceJointe' in line and not line.strip().startswith('#'):
                    errors.append(f"{filename}:{line_num}: {line.strip()}")
    
    if errors:
        print("  ❌ Erreurs trouvées:")
        for error in errors:
            print(f"     {error}")
        return False
    else:
        print("  ✅ Aucun import de PieceJointe trouvé")
        return True

def check_export_import_utils():
    """Vérifie que export_import_utils.py a les bons imports"""
    print("\n🔍 Vérification de export_import_utils.py...")
    
    if not os.path.exists('export_import_utils.py'):
        print("  ❌ Fichier export_import_utils.py non trouvé")
        return False
    
    with open('export_import_utils.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Vérifier l'import correct
    if 'from models import Courrier, CourrierForward' in content:
        print("  ✅ Import correct trouvé: from models import Courrier, CourrierForward")
        return True
    elif 'from models import' in content and 'PieceJointe' not in content:
        print("  ✅ Imports corrects (sans PieceJointe)")
        return True
    else:
        print("  ❌ Import incorrect ou manquant")
        return False

def check_models():
    """Vérifie que models.py ne définit pas PieceJointe"""
    print("\n🔍 Vérification de models.py...")
    
    if not os.path.exists('models.py'):
        print("  ❌ Fichier models.py non trouvé")
        return False
    
    with open('models.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'class PieceJointe' in content:
        print("  ❌ Classe PieceJointe trouvée (ne devrait pas exister)")
        return False
    else:
        print("  ✅ Pas de classe PieceJointe (correct)")
        return True

def check_courrier_model():
    """Vérifie que le modèle Courrier a les champs de fichier"""
    print("\n🔍 Vérification du modèle Courrier...")
    
    if not os.path.exists('models.py'):
        print("  ❌ Fichier models.py non trouvé")
        return False
    
    with open('models.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_fields = [
        'fichier_nom',
        'fichier_chemin', 
        'fichier_type',
        'fichier_checksum',
        'fichier_encrypted'
    ]
    
    missing = []
    for field in required_fields:
        if field not in content:
            missing.append(field)
    
    if missing:
        print(f"  ❌ Champs manquants: {', '.join(missing)}")
        return False
    else:
        print("  ✅ Tous les champs de fichier présents dans Courrier")
        return True

def main():
    print("=" * 70)
    print("   VÉRIFICATION DE L'INSTALLATION GEC")
    print("   Vérification de la correction PieceJointe")
    print("=" * 70)
    print()
    
    results = []
    
    results.append(check_piecejointe_imports())
    results.append(check_export_import_utils())
    results.append(check_models())
    results.append(check_courrier_model())
    
    print("\n" + "=" * 70)
    print("   RÉSULTAT FINAL")
    print("=" * 70)
    
    if all(results):
        print("✅ SUCCÈS: L'installation est correcte!")
        print("   Aucun problème d'import PieceJointe détecté.")
        return 0
    else:
        print("❌ ÉCHEC: Des problèmes ont été détectés.")
        print("   Consultez FIX_PIECEJOINTE_ERROR.md pour les corrections.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
