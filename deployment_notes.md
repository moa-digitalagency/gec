# Notes de déploiement pour PythonAnywhere

## Corrections appliquées pour la production

### 1. Problèmes résolus
- **Export PDF** : Correction de l'utilisation de `send_file` remplacé par `send_from_directory`
- **Téléchargement de fichiers** : Gestion des chemins relatifs et absolus
- **Visualisation de fichiers** : Support des différents types MIME
- **Chemins de fichiers** : Migration des chemins absolus vers des chemins relatifs

### 2. Changements effectués

#### Views.py
- Ajout de `send_from_directory` pour tous les téléchargements
- Gestion intelligente des chemins (relatifs/absolus)
- Détection automatique des types MIME
- Création automatique des dossiers nécessaires

#### Fix_file_paths.py
- Script de migration pour corriger les chemins existants
- Conversion automatique des chemins absolus en relatifs
- Vérification de l'existence des fichiers

### 3. Structure des dossiers requise
```
/
├── uploads/       # Fichiers uploadés
├── exports/       # PDFs générés
├── backups/       # Sauvegardes système
└── instance/      # Base de données
```

### 4. Installation sur PythonAnywhere

1. **Créer les dossiers nécessaires** :
```bash
mkdir -p uploads exports backups instance
```

2. **Exécuter la migration des chemins** (si nécessaire) :
```bash
python fix_file_paths.py
```

3. **Vérifier les permissions** :
```bash
chmod 755 uploads exports backups
```

4. **Variables d'environnement à configurer** :
- `DATABASE_URL` : URL de votre base de données PostgreSQL
- `SESSION_SECRET` : Clé secrète pour les sessions
- `GEC_MASTER_KEY` : Clé de chiffrement (optionnel)
- `GEC_PASSWORD_SALT` : Sel pour les mots de passe (optionnel)

### 5. Configuration Flask pour PythonAnywhere

Dans le fichier de configuration WSGI :
```python
import sys
import os

# Ajouter le chemin du projet
path = '/home/votre_username/votre_projet'
if path not in sys.path:
    sys.path.append(path)

# Importer l'application
from main import app as application

# Créer les dossiers nécessaires
os.makedirs('uploads', exist_ok=True)
os.makedirs('exports', exist_ok=True)
os.makedirs('backups', exist_ok=True)
```

### 6. Problèmes potentiels et solutions

**Problème** : Les fichiers ne se téléchargent pas
**Solution** : Vérifier que les dossiers existent et ont les bonnes permissions

**Problème** : Les PDFs ne s'exportent pas
**Solution** : S'assurer que ReportLab est installé et que le dossier exports existe

**Problème** : Les chemins de fichiers sont incorrects
**Solution** : Exécuter le script `fix_file_paths.py`

### 7. Test de vérification

Après déploiement, tester :
1. Upload d'un fichier dans un nouveau courrier
2. Téléchargement du fichier uploadé
3. Visualisation du fichier (view_file)
4. Export PDF d'un courrier
5. Export PDF de la liste des courriers

## Contact

Si vous rencontrez des problèmes, vérifiez les logs d'erreur dans PythonAnywhere et assurez-vous que tous les dossiers nécessaires existent avec les bonnes permissions.