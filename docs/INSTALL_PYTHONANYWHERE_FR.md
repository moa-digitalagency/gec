# Installation GEC Mines sur PythonAnywhere

## 🚀 Guide Simplifié

Ce guide vous permet de déployer rapidement GEC Mines sur PythonAnywhere en 30 minutes.

## Prérequis

- Compte PythonAnywhere (gratuit suffisant pour tests)
- Code source GEC Mines
- 30 minutes de temps libre

## ⚡ Installation Express

### Étape 1 : Créer le Compte
1. Allez sur [pythonanywhere.com](https://www.pythonanywhere.com) 
2. Créez un compte gratuit
3. Connectez-vous au tableau de bord

### Étape 2 : Upload des Fichiers
1. Cliquez sur **"Files"** dans le menu
2. Créez un dossier `gec-mines` dans votre répertoire home
3. Uploadez tous les fichiers du projet GEC Mines dans ce dossier

### Étape 3 : Installer les Dépendances
1. Ouvrez une console **Bash** (onglet "Console")
2. Exécutez ces commandes :
```bash
cd ~/gec-mines
python3.11 -m venv venv
source venv/bin/activate
pip install flask flask-sqlalchemy flask-login werkzeug reportlab pillow
```

### Étape 4 : Base de Données (SQLite pour Gratuit)
```bash
# Dans la console
mkdir -p ~/gec-mines/instance
echo "DATABASE_URL=sqlite:///instance/gec_mines.db" > ~/gec-mines/.env
echo "SESSION_SECRET=votre-cle-secrete-aleatoire-ici" >> ~/gec-mines/.env
```

### Étape 5 : Initialiser la Base
```bash
cd ~/gec-mines
source venv/bin/activate
python init_database.py
```

### Étape 6 : Créer l'Application Web
1. Allez dans l'onglet **"Web"**
2. Cliquez **"Add a new web app"**
3. Choisissez votre domaine gratuit
4. Sélectionnez **"Manual configuration"**
5. Choisissez **Python 3.11**

### Étape 7 : Configuration WSGI
1. Cliquez sur le lien du fichier WSGI (ex: `/var/www/username_pythonanywhere_com_wsgi.py`)
2. Remplacez tout le contenu par :
```python
import sys
import os

# Votre nom d'utilisateur ici
username = "VOTRE_NOM_UTILISATEUR"
path = f'/home/{username}/gec-mines'

if path not in sys.path:
    sys.path.insert(0, path)

# Variables d'environnement
os.environ['DATABASE_URL'] = f'sqlite:///{path}/instance/gec_mines.db'
os.environ['SESSION_SECRET'] = 'cle-secrete-production'

from main import app as application
```

### Étape 8 : Configuration Finale
**Dans l'onglet Web, configurez :**
- **Virtualenv** : `/home/VOTRE_NOM_UTILISATEUR/gec-mines/venv`
- **Static files** : 
  - URL `/static/` → Directory `/home/VOTRE_NOM_UTILISATEUR/gec-mines/static/`
  - URL `/uploads/` → Directory `/home/VOTRE_NOM_UTILISATEUR/gec-mines/uploads/`

### Étape 9 : Tester l'Application
1. Cliquez **"Reload"** dans l'onglet Web
2. Visitez votre site : `https://VOTRE_NOM_UTILISATEUR.pythonanywhere.com`
3. Connectez-vous avec : `admin` / `admin123`

## ✅ Application Prête !

Votre GEC Mines est maintenant en ligne. Changez le mot de passe admin dès la première connexion.

## 🔧 Dépannage Rapide

**Erreur 500 ?** Vérifiez les logs dans l'onglet "Error log" de PythonAnywhere.

**Page blanche ?** Vérifiez que le virtualenv et les static files sont bien configurés.

**Base de données vide ?** Relancez `python init_database.py` dans la console.

## 📞 Support

- [Documentation PythonAnywhere](https://help.pythonanywhere.com/)
- [Aide Flask](https://help.pythonanywhere.com/pages/Flask/)

---

**Guide Version** : Simplifié 1.0 | **Temps d'installation** : ~30 minutes