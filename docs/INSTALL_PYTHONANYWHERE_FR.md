# Installation de GEC Mines sur PythonAnywhere

## Vue d'ensemble

Ce guide vous accompagne pour déployer le système GEC Mines sur PythonAnywhere, une plateforme d'hébergement Python spécialement conçue pour les applications Flask et Django.

## Prérequis

- **Compte PythonAnywhere** : Compte gratuit ou payant
- **Fichiers du projet** : Code source de GEC Mines
- **Base de données** : PostgreSQL ou MySQL (selon votre plan)

## Étape 1 : Préparation du Compte

### 1.1 Création du Compte
1. Allez sur [https://www.pythonanywhere.com](https://www.pythonanywhere.com)
2. Créez un compte (gratuit ou payant selon vos besoins)
3. Connectez-vous à votre tableau de bord

### 1.2 Vérification du Plan
- **Compte gratuit** : Limité à 1 application web, SQLite uniquement
- **Compte payant** : Applications multiples, PostgreSQL/MySQL disponibles

## Étape 2 : Upload des Fichiers

### 2.1 Via l'Interface Web
1. Allez dans l'onglet **"Files"**
2. Naviguez vers votre répertoire home (`/home/yourusername/`)
3. Créez un dossier `gec-mines`
4. Uploadez tous les fichiers du projet

### 2.2 Via Git (Recommandé)
```bash
# Dans la console Bash de PythonAnywhere
cd ~
git clone https://github.com/votre-repo/gec-mines.git
cd gec-mines
```

## Étape 3 : Configuration de l'Environnement Virtuel

### 3.1 Création de l'Environnement
```bash
# Dans la console Bash
cd ~/gec-mines
python3.11 -m venv venv
source venv/bin/activate
```

### 3.2 Installation des Dépendances
```bash
# Mise à jour de pip
pip install --upgrade pip

# Installation des packages requis
pip install flask flask-sqlalchemy flask-login
pip install werkzeug reportlab
pip install psycopg2-binary  # Pour PostgreSQL
pip install gunicorn
pip install pillow  # Pour la gestion des images/logos
```

### 3.3 Création du fichier requirements.txt
```bash
pip freeze > requirements.txt
```

## Étape 4 : Configuration de la Base de Données

### 4.1 Pour PostgreSQL (Comptes Payants)
1. Allez dans l'onglet **"Databases"**
2. Créez une nouvelle base PostgreSQL
3. Notez les informations de connexion :
   - Host : `nom-utilisateur-xxxx.postgres.pythonanywhere-services.com`
   - Database : `nom-utilisateur$gec_mines`
   - Username : `nom-utilisateur`
   - Password : `votre-mot-de-passe`

### 4.2 Pour MySQL (Alternative)
```sql
-- Création de la base de données
CREATE DATABASE nom_utilisateur$gec_mines CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4.3 Pour SQLite (Compte Gratuit)
```bash
# La base sera créée automatiquement
mkdir -p ~/gec-mines/instance
```

## Étape 5 : Configuration des Variables d'Environnement

### 5.1 Création du fichier .env
```bash
cd ~/gec-mines
nano .env
```

### 5.2 Contenu du fichier .env
```bash
# Pour PostgreSQL
DATABASE_URL=postgresql://nom-utilisateur:mot-de-passe@nom-utilisateur-xxxx.postgres.pythonanywhere-services.com/nom-utilisateur$gec_mines

# Pour MySQL
# DATABASE_URL=mysql://nom-utilisateur:mot-de-passe@nom-utilisateur.mysql.pythonanywhere-services.com/nom-utilisateur$gec_mines

# Pour SQLite (compte gratuit)
# DATABASE_URL=sqlite:///instance/gec_mines.db

# Clé secrète pour les sessions
SESSION_SECRET=votre-cle-secrete-tres-longue-et-aleatoire

# Mode production
FLASK_ENV=production
```

## Étape 6 : Initialisation de la Base de Données

### 6.1 Modification du script d'initialisation
```bash
cd ~/gec-mines
nano init_database.py
```

Ajoutez en début de fichier :
```python
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
```

### 6.2 Exécution de l'initialisation
```bash
source venv/bin/activate
python init_database.py
```

## Étape 7 : Configuration de l'Application Web

### 7.1 Création de l'Application Web
1. Allez dans l'onglet **"Web"**
2. Cliquez sur **"Add a new web app"**
3. Choisissez votre domaine (ex: `nom-utilisateur.pythonanywhere.com`)
4. Sélectionnez **"Manual configuration"**
5. Choisissez **Python 3.11**

### 7.2 Configuration du fichier WSGI
```python
# Contenu de /var/www/nom_utilisateur_pythonanywhere_com_wsgi.py

import sys
import os
from dotenv import load_dotenv

# Ajouter le répertoire du projet au path
path = '/home/nom-utilisateur/gec-mines'
if path not in sys.path:
    sys.path.insert(0, path)

# Charger les variables d'environnement
load_dotenv(os.path.join(path, '.env'))

# Importer l'application Flask
from main import app as application

if __name__ == "__main__":
    application.run()
```

### 7.3 Configuration des Dossiers Statiques
1. Dans l'onglet **"Web"**, section **"Static files"**
2. Ajoutez :
   - URL : `/static/`
   - Directory : `/home/nom-utilisateur/gec-mines/static/`
3. Ajoutez pour les uploads :
   - URL : `/uploads/`
   - Directory : `/home/nom-utilisateur/gec-mines/uploads/`

### 7.4 Configuration de l'Environnement Virtuel
1. Dans l'onglet **"Web"**, section **"Virtualenv"**
2. Entrez : `/home/nom-utilisateur/gec-mines/venv`

## Étape 8 : Sécurisation et Optimisation

### 8.1 Création des Dossiers Nécessaires
```bash
cd ~/gec-mines
mkdir -p uploads/{profiles,backups}
mkdir -p exports
mkdir -p logs
chmod 755 uploads exports logs
```

### 8.2 Configuration des Logs
```bash
# Création du fichier de log
touch ~/gec-mines/logs/app.log
chmod 644 ~/gec-mines/logs/app.log
```

### 8.3 Sécurisation des Fichiers
```bash
# Protection des fichiers sensibles
chmod 600 ~/gec-mines/.env
chmod 644 ~/gec-mines/*.py
```

## Étape 9 : Test et Validation

### 9.1 Redémarrage de l'Application
1. Dans l'onglet **"Web"**
2. Cliquez sur **"Reload nom-utilisateur.pythonanywhere.com"**

### 9.2 Vérification du Fonctionnement
1. Visitez `https://nom-utilisateur.pythonanywhere.com`
2. Vérifiez que la page de connexion s'affiche
3. Testez la connexion avec les identifiants admin
4. Vérifiez toutes les fonctionnalités principales

### 9.3 Vérification des Logs
```bash
# Consulter les logs d'erreur
tail -f /var/log/nom-utilisateur.pythonanywhere.com.error.log

# Consulter les logs d'accès
tail -f /var/log/nom-utilisateur.pythonanywhere.com.access.log
```

## Étape 10 : Maintenance et Monitoring

### 10.1 Sauvegardes Automatiques
```bash
#!/bin/bash
# Script de sauvegarde à placer dans ~/backup_gec.sh

cd ~/gec-mines
source venv/bin/activate

# Sauvegarde de la base de données
if [[ $DATABASE_URL == postgresql* ]]; then
    pg_dump $DATABASE_URL > backups/db_backup_$(date +%Y%m%d_%H%M%S).sql
elif [[ $DATABASE_URL == mysql* ]]; then
    mysqldump --single-transaction --routines --triggers gec_mines > backups/db_backup_$(date +%Y%m%d_%H%M%S).sql
else
    cp instance/gec_mines.db backups/db_backup_$(date +%Y%m%d_%H%M%S).db
fi

# Sauvegarde des fichiers uploads
tar -czf backups/uploads_backup_$(date +%Y%m%d_%H%M%S).tar.gz uploads/

# Nettoyage des anciennes sauvegardes (garder 7 jours)
find backups/ -name "*.sql" -mtime +7 -delete
find backups/ -name "*.tar.gz" -mtime +7 -delete
find backups/ -name "*.db" -mtime +7 -delete
```

### 10.2 Tâches Cron
```bash
# Ajouter au crontab (commande: crontab -e)
# Sauvegarde quotidienne à 2h du matin
0 2 * * * /home/nom-utilisateur/backup_gec.sh

# Nettoyage des logs hebdomadaire
0 3 * * 0 find /home/nom-utilisateur/gec-mines/logs/ -name "*.log" -mtime +30 -delete
```

## Étape 11 : Optimisations Avancées

### 11.1 Configuration de Cache
```python
# Ajout dans main.py pour la mise en cache statique
from flask import Flask
from datetime import timedelta

app = Flask(__name__)

@app.after_request
def add_header(response):
    if request.endpoint == 'static':
        response.cache_control.max_age = 31536000  # 1 an
    return response
```

### 11.2 Compression Gzip
```python
# Installation et configuration de Flask-Compress
# pip install Flask-Compress

from flask_compress import Compress

app = Flask(__name__)
Compress(app)
```

## Dépannage

### Problèmes Courants

#### 1. Erreur "Internal Server Error"
```bash
# Vérifier les logs
tail -f /var/log/nom-utilisateur.pythonanywhere.com.error.log
```

#### 2. Base de données inaccessible
- Vérifiez les informations de connexion dans `.env`
- Testez la connexion depuis la console

#### 3. Fichiers statiques non servis
- Vérifiez la configuration des dossiers statiques
- Vérifiez les permissions des dossiers

#### 4. Upload de fichiers non fonctionnel
```bash
# Vérifier les permissions
chmod 755 uploads/
chmod 644 uploads/*
```

### Commandes Utiles

```bash
# Redémarrer l'application
touch /var/www/nom_utilisateur_pythonanywhere_com_wsgi.py

# Voir les processus Python
ps aux | grep python

# Tester la configuration
cd ~/gec-mines
source venv/bin/activate
python -c "from main import app; print('Configuration OK')"
```

## Ressources Supplémentaires

- [Documentation PythonAnywhere](https://help.pythonanywhere.com/)
- [Guide Flask sur PythonAnywhere](https://help.pythonanywhere.com/pages/Flask/)
- [Configuration des bases de données](https://help.pythonanywhere.com/pages/Databases/)

## Support

Pour obtenir de l'aide :
1. Consultez les logs d'erreur
2. Vérifiez la documentation PythonAnywhere
3. Contactez le support PythonAnywhere si nécessaire

---

**Version du guide** : 1.0  
**Dernière mise à jour** : Juillet 2025  
**Compatibilité** : PythonAnywhere, Python 3.11+, PostgreSQL/MySQL/SQLite