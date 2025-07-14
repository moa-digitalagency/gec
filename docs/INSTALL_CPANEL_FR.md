# Installation sur cPanel - GEC Mines

## Vue d'ensemble

Ce guide détaille l'installation complète du système GEC Mines sur un hébergement partagé utilisant cPanel, couramment utilisé par les hébergeurs web.

## Prérequis

### Hébergement
- **cPanel** avec accès complet
- **Python 3.11+** disponible
- **PostgreSQL** ou **MySQL 8.0+** 
- **SSH** (optionnel mais recommandé)
- **Espace disque** : 500 MB minimum
- **RAM** : 512 MB minimum

### Compétences requises
- Utilisation de base de cPanel
- Notions de ligne de commande (optionnel)
- Configuration de variables d'environnement

## Étape 1 : Préparation de l'hébergement

### 1.1 Vérification des prérequis
1. Connectez-vous à votre cPanel
2. Vérifiez la version Python dans **"Select Python App"** ou **"Python Selector"**
3. Assurez-vous que PostgreSQL est disponible dans **"PostgreSQL Databases"**

### 1.2 Création de la base de données
1. Accédez à **"PostgreSQL Databases"** dans cPanel
2. Créez une nouvelle base de données :
   - Nom : `gec_mines`
   - Utilisateur : `gec_user`
   - Mot de passe fort
3. Notez les informations de connexion

## Étape 2 : Téléchargement et installation

### 2.1 Téléchargement des fichiers
1. Téléchargez le package GEC Mines depuis le dépôt officiel
2. Utilisez le **"File Manager"** de cPanel :
   - Accédez au dossier `public_html` ou `www`
   - Créez un dossier `gec-mines`
   - Téléchargez et extrayez l'archive

### 2.2 Structure recommandée
```
public_html/
└── gec-mines/
    ├── main.py
    ├── app.py
    ├── models.py
    ├── views.py
    ├── utils.py
    ├── requirements.txt
    ├── init_database.py
    ├── static/
    ├── templates/
    ├── uploads/
    ├── exports/
    ├── backups/
    ├── lang/
    └── docs/
```

## Étape 3 : Configuration Python

### 3.1 Création de l'application Python
1. Dans cPanel, accédez à **"Python App"**
2. Cliquez sur **"Create Application"**
3. Configurez :
   - **Python version** : 3.11 ou supérieure
   - **Application root** : `/public_html/gec-mines`
   - **Application URL** : `gec-mines` ou domaine personnalisé
   - **Startup file** : `main.py`

### 3.2 Installation des dépendances
1. Cliquez sur **"Open terminal"** dans l'application Python
2. Exécutez :
```bash
pip install -r requirements.txt
```

Ou utilisez l'interface cPanel pour installer :
- Flask
- Flask-SQLAlchemy
- Flask-Login
- psycopg2-binary
- reportlab
- werkzeug

## Étape 4 : Configuration des variables d'environnement

### 4.1 Configuration via cPanel
1. Dans l'application Python, section **"Environment variables"**
2. Ajoutez :
```
DATABASE_URL=postgresql://gec_user:PASSWORD@localhost:5432/gec_mines
SESSION_SECRET=votre_cle_secrete_unique_et_complexe
FLASK_ENV=production
```

### 4.2 Fichier .env (alternative)
Créez un fichier `.env` dans le répertoire racine :
```bash
DATABASE_URL=postgresql://gec_user:YOUR_PASSWORD@localhost:5432/gec_mines
SESSION_SECRET=your_very_long_and_complex_secret_key_here
FLASK_ENV=production
FLASK_DEBUG=False
```

## Étape 5 : Initialisation de la base de données

### 5.1 Via Terminal (recommandé)
1. Ouvrez le terminal de l'application Python
2. Exécutez :
```bash
python init_database.py
```

### 5.2 Via File Manager (alternative)
1. Utilisez **"phpPgAdmin"** ou équivalent
2. Importez manuellement les fichiers SQL :
   - `docs/init_database.sql`
   - `docs/init_data.sql`

## Étape 6 : Configuration des dossiers

### 6.1 Permissions des dossiers
Configurez les permissions via File Manager :
```
uploads/     → 755 (rwxr-xr-x)
exports/     → 755 (rwxr-xr-x)
backups/     → 755 (rwxr-xr-x)
static/      → 755 (rwxr-xr-x)
lang/        → 644 (rw-r--r--)
```

### 6.2 Sécurité des dossiers
Créez des fichiers `.htaccess` pour protéger les dossiers sensibles :

**uploads/.htaccess** :
```apache
<Files ~ "\.(jpg|jpeg|png|gif|pdf|doc|docx)$">
    Order allow,deny
    Allow from all
</Files>
<Files ~ "\.php$">
    Order allow,deny
    Deny from all
</Files>
```

**backups/.htaccess** :
```apache
Order allow,deny
Deny from all
```

## Étape 7 : Configuration du serveur web

### 7.1 Domaine personnalisé (optionnel)
1. Dans cPanel, **"Subdomains"**
2. Créez un sous-domaine : `gec.votredomaine.com`
3. Pointez vers `/public_html/gec-mines`

### 7.2 Redirection HTTPS
Créez un fichier `.htaccess` dans le répertoire racine :
```apache
RewriteEngine On

# Redirection HTTPS
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

# Protection des fichiers sensibles
<Files ~ "^\.">
    Order allow,deny
    Deny from all
</Files>

<Files ~ "\.py$">
    Order allow,deny
    Deny from all
</Files>

# Configuration pour l'application Python
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ passenger_wsgi.py/$1 [QSA,L]
```

## Étape 8 : Test et vérification

### 8.1 Test de l'application
1. Redémarrez l'application Python dans cPanel
2. Accédez à votre URL : `https://votredomaine.com/gec-mines`
3. Connectez-vous avec :
   - Username : `admin`
   - Password : `admin123`

### 8.2 Vérifications post-installation
- [ ] Interface utilisateur s'affiche correctement
- [ ] Connexion administrateur fonctionnelle
- [ ] Enregistrement d'un courrier test
- [ ] Upload de fichier test
- [ ] Export PDF fonctionnel
- [ ] Système de sauvegarde accessible

## Étape 9 : Configuration de production

### 9.1 Sécurité
1. **Changez le mot de passe administrateur**
2. **Configurez SSL/TLS** via cPanel
3. **Limitez l'accès IP** si nécessaire
4. **Configurez les sauvegardes automatiques**

### 9.2 Optimisation
1. **Cache statique** : activez la mise en cache des ressources CSS/JS
2. **Compression** : activez gzip dans cPanel
3. **Monitoring** : configurez les logs d'erreur

### 9.3 Maintenance
Configurez une tâche cron pour la maintenance :
```bash
# Nettoyage quotidien à 2h du matin
0 2 * * * cd /home/username/public_html/gec-mines && python -c "import os; os.system('find uploads/ -name \"*.tmp\" -mtime +1 -delete')"

# Sauvegarde hebdomadaire
0 3 * * 0 cd /home/username/public_html/gec-mines && python -c "from views import create_system_backup; create_system_backup()"
```

## Étape 10 : Dépannage

### 10.1 Problèmes courants

**Application ne démarre pas** :
- Vérifiez les logs Python dans cPanel
- Vérifiez que tous les modules sont installés
- Contrôlez les variables d'environnement

**Base de données inaccessible** :
- Vérifiez les informations de connexion
- Testez la connexion via phpPgAdmin
- Vérifiez les permissions utilisateur

**Erreurs de permissions** :
- Ajustez les permissions des dossiers (755)
- Vérifiez la propriété des fichiers
- Contrôlez les règles .htaccess

### 10.2 Logs et débogage
1. **Logs Python** : `/tmp/` ou dossier logs de l'application
2. **Logs Apache** : cPanel → "Error Logs"
3. **Logs application** : Consultez les logs d'activité dans GEC

### 10.3 Support technique
- Contactez le support de votre hébergeur pour les problèmes de configuration
- Vérifiez la documentation Python de votre hébergeur
- Consultez les forums de la communauté cPanel

## Maintenance et mises à jour

### Sauvegarde régulière
1. Utilisez la fonction de sauvegarde intégrée de GEC
2. Téléchargez régulièrement les sauvegardes via File Manager
3. Sauvegardez la base de données via phpPgAdmin

### Mises à jour
1. Sauvegardez avant toute mise à jour
2. Téléchargez la nouvelle version
3. Remplacez les fichiers (conservez uploads/ et backups/)
4. Exécutez les scripts de migration si nécessaire

---

**Support** : Pour une assistance technique, consultez la documentation complète dans le dossier `docs/` ou contactez l'équipe de développement.

**Sécurité** : Changez TOUJOURS les mots de passe par défaut et activez HTTPS en production.