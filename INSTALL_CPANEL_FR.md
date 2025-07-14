# Guide d'Installation cPanel - GEC Mines
## Installation Step-by-Step sur Hébergement Partagé

---

## 📋 Prérequis

### Hébergement cPanel
- **PHP 8.0+** avec extensions : PDO, SQLite, OpenSSL, Zip, cURL
- **Base de données** : MySQL/MariaDB ou PostgreSQL
- **Espace disque** : Minimum 500MB (recommandé 1GB)
- **Mémoire PHP** : Minimum 256MB (recommandé 512MB)
- **Accès SSH** (optionnel mais recommandé)

### Fichiers nécessaires
- Archive complète du projet GEC Mines
- Identifiants de base de données fournis par l'hébergeur

---

## 🚀 Étape 1 : Préparation des fichiers

### 1.1 Téléchargement et extraction
```bash
# Créer un dossier temporaire sur votre ordinateur
mkdir gec-mines-install
cd gec-mines-install

# Extraire l'archive du projet
unzip gec-mines-complete.zip
```

### 1.2 Configuration de base de données
1. **Connectez-vous à cPanel**
2. **Accédez à "Bases de données MySQL"**
3. **Créez une nouvelle base de données** :
   - Nom : `votre_prefix_gec_mines`
   - Notez le nom complet généré

4. **Créez un utilisateur de base de données** :
   - Nom d'utilisateur : `votre_prefix_gec`
   - Mot de passe : Générez un mot de passe sécurisé
   - Notez ces informations !

5. **Associez l'utilisateur à la base** :
   - Accordez TOUS les privilèges

---

## 🔧 Étape 2 : Upload des fichiers

### 2.1 Via le Gestionnaire de fichiers cPanel
1. **Ouvrez le Gestionnaire de fichiers**
2. **Naviguez vers `public_html`** (ou le sous-dossier de votre choix)
3. **Uploadez l'archive** `gec-mines-complete.zip`
4. **Clic droit → Extraire** l'archive
5. **Déplacez tous les fichiers** du dossier extrait vers `public_html`

### 2.2 Via FTP (alternative)
```bash
# Paramètres FTP (fournis par votre hébergeur)
ftp://votre-domaine.com
Utilisateur : votre_user_ftp
Mot de passe : votre_password_ftp

# Upload de tous les fichiers vers public_html/
```

---

## ⚙️ Étape 3 : Configuration

### 3.1 Variables d'environnement
Créez un fichier `.env` dans le répertoire racine :

```bash
# Base de données
DATABASE_URL=mysql://votre_user_db:mot_de_passe@localhost/votre_nom_db

# Sécurité
SESSION_SECRET=votre_secret_tres_long_et_aleatoire_ici

# Configuration
FLASK_ENV=production
FLASK_DEBUG=False
UPLOAD_FOLDER=uploads
EXPORT_FOLDER=exports
```

### 3.2 Fichier .htaccess
Créez un fichier `.htaccess` dans `public_html` :

```apache
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ index.php [QSA,L]

# Configuration PHP
php_value memory_limit 512M
php_value max_execution_time 300
php_value upload_max_filesize 16M
php_value post_max_size 32M

# Sécurité
<Files ".env">
    Order allow,deny
    Deny from all
</Files>

<Files "*.py">
    Order allow,deny
    Deny from all
</Files>
```

### 3.3 Point d'entrée PHP
Créez un fichier `index.php` dans `public_html` :

```php
<?php
// Point d'entrée pour Python Flask sur cPanel
$command = "cd " . __DIR__ . " && python3 main.py 2>&1";
$output = shell_exec($command);

if ($output === null) {
    // Fallback pour hébergements restrictifs
    header('Content-Type: text/html');
    echo '<html><body>';
    echo '<h1>GEC Mines - Système de Gestion du Courrier</h1>';
    echo '<p>Configuration en cours...</p>';
    echo '<p>Contactez votre administrateur si cette page persiste.</p>';
    echo '</body></html>';
} else {
    echo $output;
}
?>
```

---

## 🗃️ Étape 4 : Initialisation base de données

### 4.1 Via Terminal cPanel (si disponible)
```bash
cd public_html
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Base de données initialisée avec succès!')
"
```

### 4.2 Via phpMyAdmin (alternative)
1. **Connectez-vous à phpMyAdmin**
2. **Sélectionnez votre base de données**
3. **Importez le fichier SQL** : `database_schema.sql`
4. **Exécutez les requêtes d'initialisation**

---

## 🔐 Étape 5 : Configuration sécurité

### 5.1 Permissions des dossiers
```bash
# Via Gestionnaire de fichiers ou SSH
chmod 755 public_html/
chmod 755 uploads/
chmod 755 exports/
chmod 755 static/
chmod 644 *.py
chmod 600 .env
```

### 5.2 Protection des dossiers sensibles
Créez des fichiers `.htaccess` dans :

**uploads/.htaccess** :
```apache
Options -Indexes
<Files "*.py">
    Order allow,deny
    Deny from all
</Files>
```

**backups/.htaccess** :
```apache
Order allow,deny
Deny from all
```

---

## 🎯 Étape 6 : Test et validation

### 6.1 Accès initial
1. **Visitez votre site** : `https://votre-domaine.com`
2. **Page de connexion** doit s'afficher
3. **Connectez-vous avec** :
   - Login : `admin`
   - Mot de passe : `admin123`

### 6.2 Tests fonctionnels
- ✅ **Connexion administrateur**
- ✅ **Enregistrement d'un courrier test**
- ✅ **Upload d'un fichier**
- ✅ **Export PDF**
- ✅ **Recherche**
- ✅ **Paramètres système**

### 6.3 Configuration SSL (recommandé)
1. **Activez SSL** dans cPanel
2. **Forcez HTTPS** via .htaccess :
```apache
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
```

---

## 🔧 Étape 7 : Optimisations

### 7.1 Performance
Ajoutez dans `.htaccess` :
```apache
# Compression
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/html text/css text/javascript application/javascript
</IfModule>

# Cache navigateur
<IfModule mod_expires.c>
    ExpiresActive on
    ExpiresByType text/css "access plus 1 month"
    ExpiresByType application/javascript "access plus 1 month"
    ExpiresByType image/png "access plus 1 month"
    ExpiresByType image/jpg "access plus 1 month"
    ExpiresByType image/jpeg "access plus 1 month"
</IfModule>
```

### 7.2 Logs d'erreur
Créez un dossier `logs/` avec permissions 755 :
```bash
mkdir logs
chmod 755 logs
```

### 7.3 Tâches CRON (optionnel)
Dans cPanel → Tâches CRON, ajoutez :
```bash
# Nettoyage des fichiers temporaires (quotidien)
0 2 * * * cd /home/username/public_html && python3 -c "import os; [os.remove(f) for f in os.listdir('exports') if f.endswith('.pdf') and os.path.getmtime(f'exports/{f}') < time.time() - 604800]"
```

---

## 🚨 Dépannage

### Problèmes courants

**"Internal Server Error"**
- Vérifiez les permissions des fichiers
- Consultez les logs d'erreur cPanel
- Vérifiez la configuration .htaccess

**"Base de données inaccessible"**
- Validez DATABASE_URL dans .env
- Vérifiez les privilèges utilisateur MySQL
- Testez la connexion via phpMyAdmin

**"Module Python introuvable"**
- Vérifiez que Python 3.8+ est installé
- Contactez votre hébergeur pour l'activation Python
- Utilisez l'alternative PHP si nécessaire

**"Upload de fichiers échoue"**
- Vérifiez upload_max_filesize en PHP
- Augmentez post_max_size
- Vérifiez les permissions du dossier uploads/

### Support technique
- **Documentation** : Consultez DOCUMENTATION.md
- **Logs** : Activez le mode debug temporairement
- **Hébergeur** : Contactez le support pour problèmes serveur

---

## ✅ Checklist finale

- [ ] Base de données créée et configurée
- [ ] Fichiers uploadés et permissions définies
- [ ] Variables d'environnement configurées
- [ ] Tests de connexion réussis
- [ ] Upload et export fonctionnels
- [ ] SSL activé
- [ ] Mot de passe admin changé
- [ ] Sauvegarde initiale créée

---

**🎉 Félicitations ! Votre système GEC Mines est opérationnel sur cPanel.**

Pour toute assistance technique, consultez la documentation complète ou contactez votre administrateur système.