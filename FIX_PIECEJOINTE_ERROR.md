# 🔧 Guide de Correction - Erreur PieceJointe

## Symptôme
```
Erreur lors de l'export/import: cannot import name 'PieceJointe' from 'models' (/root/gec/models.py)
```

## Cause
Le fichier `export_import_utils.py` tente d'importer une classe `PieceJointe` qui n'existe PAS dans le système GEC.

## Solution Rapide

### Étape 1 : Ouvrir le fichier
```bash
nano /root/gec/export_import_utils.py
# ou
vim /root/gec/export_import_utils.py
```

### Étape 2 : Corriger l'import (ligne ~14)

**❌ ANCIEN CODE (INCORRECT):**
```python
from models import Courrier, CourrierForward, PieceJointe
```

**✅ NOUVEAU CODE (CORRECT):**
```python
from models import Courrier, CourrierForward
```

### Étape 3 : Sauvegarder et Redémarrer

**Pour nano:**
- Appuyez sur `Ctrl + O` pour sauvegarder
- Appuyez sur `Entrée` pour confirmer
- Appuyez sur `Ctrl + X` pour quitter

**Pour vim:**
- Appuyez sur `Esc`
- Tapez `:wq` et appuyez sur `Entrée`

**Redémarrer l'application:**
```bash
# Si vous utilisez systemd
sudo systemctl restart gec

# Si vous utilisez gunicorn directement
pkill gunicorn
gunicorn --bind 0.0.0.0:5000 main:app

# Si vous utilisez un autre gestionnaire de processus
# Adaptez selon votre configuration
```

### Étape 4 : Vérifier la Correction

```bash
# Vérifier qu'il n'y a plus de référence à PieceJointe
grep -n "PieceJointe" /root/gec/export_import_utils.py

# Cette commande ne devrait RIEN retourner (aucune ligne trouvée)
```

## Pourquoi cette erreur ?

Le système GEC stocke les pièces jointes directement dans le modèle `Courrier` via ces champs:
- `fichier_nom` - Nom du fichier
- `fichier_chemin` - Chemin de stockage  
- `fichier_type` - Type MIME
- `fichier_checksum` - Somme de contrôle SHA-256
- `fichier_encrypted` - Indicateur de chiffrement

Il n'y a JAMAIS eu de modèle `PieceJointe` séparé dans GEC.

## Si le Problème Persiste

1. Vérifiez que vous modifiez le bon fichier:
   ```bash
   ls -la /root/gec/export_import_utils.py
   ```

2. Assurez-vous d'avoir les permissions d'écriture:
   ```bash
   chmod +w /root/gec/export_import_utils.py
   ```

3. Vérifiez tous les fichiers Python pour des imports de PieceJointe:
   ```bash
   grep -r "PieceJointe" /root/gec/*.py
   ```

4. Si vous trouvez d'autres fichiers avec `PieceJointe`, supprimez ces imports également.

## Versions Corrigées

✅ **Cette installation Replit** est déjà corrigée
❌ **Votre installation `/root/gec/`** nécessite cette correction

## Besoin d'Aide ?

Si vous rencontrez des difficultés, vérifiez le fichier `CHANGELOG.md` pour plus de détails ou consultez la documentation du projet.

---
*Dernière mise à jour: 2025-10-15*
