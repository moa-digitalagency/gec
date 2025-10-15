# Guide de Mise à Jour via GitHub

Ce guide explique comment forcer la mise à jour de votre code GEC depuis GitHub **sans toucher** à votre base de données et vos configurations existantes.

## 🎯 Objectif

Mettre à jour **uniquement le code** de l'application depuis GitHub, tout en préservant :
- ✅ Base de données existante (intacte)
- ✅ Variables d'environnement (GEC_MASTER_KEY, etc.)
- ✅ Fichiers uploadés (uploads/)
- ✅ Configuration personnalisée

Les migrations de base de données se font **automatiquement** au démarrage de l'application.

## 📋 Prérequis

- Git installé sur votre système
- Accès au dépôt GitHub du projet GEC
- Application arrêtée avant la mise à jour

## ⚡ Mise à Jour Rapide (Recommandée)

### Linux / macOS

```bash
# 1. Arrêter l'application
pkill -f "gunicorn.*main:app" || pkill -f "python.*main.py"

# 2. Forcer la mise à jour du code (écrase les modifications locales du code)
git fetch origin
git reset --hard origin/main

# 3. Mettre à jour les dépendances Python
pip install -r requirements.txt --upgrade
# OU avec uv
uv pip install -r pyproject.toml --upgrade

# 4. Redémarrer l'application
gunicorn --bind 0.0.0.0:5000 --reload main:app
# OU
python main.py
```

### Windows (PowerShell)

```powershell
# 1. Arrêter l'application
Get-Process -Name python,gunicorn -ErrorAction SilentlyContinue | Stop-Process -Force

# 2. Forcer la mise à jour du code
git fetch origin
git reset --hard origin/main

# 3. Mettre à jour les dépendances Python
pip install -r requirements.txt --upgrade

# 4. Redémarrer l'application
python main.py
```

## 🔐 Fichiers Protégés (Ne Seront PAS Écrasés)

Ces fichiers/dossiers sont automatiquement ignorés par Git (via `.gitignore`) :

### Données et Configuration
```
.env                    # Variables d'environnement (GEC_MASTER_KEY, etc.)
.env.backup            # Sauvegarde des secrets
gec_mines.db           # Base de données SQLite
```

### Fichiers de l'Application
```
uploads/               # Fichiers uploadés par les utilisateurs
exports/               # Exports de courriers
backups/               # Sauvegardes système
attached_assets/       # Assets attachés
cookies.txt            # Cookies de session
```

### Fichiers Python
```
__pycache__/          # Cache Python
*.pyc                 # Fichiers compilés Python
venv/                 # Environnement virtuel
.venv/
```

**Vérification** : Pour voir quels fichiers sont ignorés
```bash
cat .gitignore
```

## 🔄 Processus Détaillé (Étape par Étape)

### 1. Arrêter l'Application

**Pourquoi ?** Éviter les conflits de fichiers pendant la mise à jour.

#### Linux / macOS
```bash
# Trouver le processus
ps aux | grep -E "gunicorn|python.*main.py"

# Arrêter gunicorn
pkill -f "gunicorn.*main:app"

# OU arrêter Python
pkill -f "python.*main.py"

# Vérifier que tout est arrêté
ps aux | grep -E "gunicorn|python.*main.py"
```

#### Windows
```powershell
# Voir les processus Python
Get-Process python,gunicorn -ErrorAction SilentlyContinue

# Arrêter tous les processus Python/Gunicorn
Get-Process -Name python,gunicorn -ErrorAction SilentlyContinue | Stop-Process -Force

# Vérifier
Get-Process python,gunicorn -ErrorAction SilentlyContinue
```

### 2. Vérifier l'État de Git

```bash
# Voir votre branche actuelle
git branch

# Voir les fichiers modifiés localement (code uniquement)
git status

# Voir les différences
git diff
```

**Note** : Les fichiers dans `.gitignore` (BD, uploads, .env) ne seront pas affichés.

### 3. Force Pull depuis GitHub

Cette commande écrase **uniquement les fichiers de code** trackés par Git.

```bash
# Récupérer les dernières modifications
git fetch origin

# Forcer la mise à jour (écrase vos modifications de code)
git reset --hard origin/main
```

**⚠️ ATTENTION** : `git reset --hard` écrase vos modifications de code local !
- ✅ Safe : Base de données, uploads, .env sont protégés
- ❌ Écrasé : Modifications du code Python, templates, CSS

**Alternative si vous voulez garder certaines modifications** :
```bash
# Sauvegarder vos modifications locales
git stash

# Mettre à jour
git pull origin main

# Restaurer vos modifications (peut causer des conflits)
git stash pop
```

### 4. Mettre à Jour les Dépendances

**Pourquoi ?** Le nouveau code peut nécessiter de nouvelles librairies.

#### Avec pip (Standard)
```bash
pip install -r requirements.txt --upgrade
```

#### Avec uv (Replit)
```bash
uv pip install -r pyproject.toml --upgrade
```

**Vérification** :
```bash
# Voir les packages installés
pip list

# Vérifier une librairie spécifique
pip show flask
```

### 5. Vérifier les Fichiers de Configuration

**Important** : Assurez-vous que vos variables d'environnement sont toujours là.

```bash
# Linux / macOS
cat .env

# Vérifier les clés critiques
echo $GEC_MASTER_KEY
echo $GEC_PASSWORD_SALT
echo $DATABASE_URL

# Windows (PowerShell)
Get-Content .env

# Vérifier les variables
echo $env:GEC_MASTER_KEY
echo $env:GEC_PASSWORD_SALT
```

**Si vos variables ont disparu** (rare), rechargez-les :
```bash
# Linux / macOS
source .env
# OU
export $(cat .env | xargs)

# Windows
Get-Content .env | ForEach-Object {
    $name, $value = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($name, $value, 'Process')
}
```

### 6. Redémarrer l'Application

L'application va automatiquement :
1. ✅ Se connecter à votre base de données existante
2. ✅ Détecter les nouvelles colonnes/tables nécessaires
3. ✅ Appliquer les migrations automatiquement
4. ✅ Logger les changements dans `migration_log`

#### Linux / macOS (Production avec Gunicorn)
```bash
gunicorn --bind 0.0.0.0:5000 --reload main:app
```

#### Linux / macOS (Développement)
```bash
python main.py
```

#### Windows
```bash
python main.py
```

### 7. Vérifier les Migrations Automatiques

**Vérifiez les logs au démarrage** :

```
INFO:root:Vérification des migrations automatiques...
INFO:root:✓ Colonne 'nouveau_champ' ajoutée à la table 'courrier'
INFO:root:✓ Table 'nouvelle_table' créée
INFO:root:🔄 2 migration(s) automatique(s) appliquée(s) avec succès
INFO:root:Default super admin user created (username: sa.gec001)
INFO:root:System parameters and statuses initialized
```

**Si vous voyez des erreurs de migration** :
```
ERROR:root:Erreur lors de la migration: ...
```
→ Consultez la section "Résolution de Problèmes" ci-dessous.

### 8. Tester l'Application

**Via le navigateur** :
1. Ouvrez `http://localhost:5000` (ou votre domaine)
2. Connectez-vous avec vos identifiants existants
3. Vérifiez que :
   - ✅ Connexion fonctionne
   - ✅ Courriers existants sont visibles
   - ✅ Données chiffrées sont déchiffrables
   - ✅ Recherche fonctionne
   - ✅ Nouvelles fonctionnalités sont présentes

**Vérifier les statistiques** :
- Tableau de bord : Nombre de courriers
- Utilisateurs : Liste des utilisateurs
- Départements : Structure organisationnelle

## 🐛 Résolution de Problèmes

### Problème 1 : "Column does not exist" au démarrage

**Symptôme** :
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such column: courrier.nouveau_champ
```

**Cause** : La migration automatique a échoué.

**Solution** :
```bash
# 1. Vérifier les logs de migration
grep "migration" app.log

# 2. Appliquer manuellement si nécessaire
# Se connecter à la BD
sqlite3 gec_mines.db  # SQLite
# OU
psql -U username -d gec_mines  # PostgreSQL

# 3. Ajouter la colonne manuellement (exemple)
ALTER TABLE courrier ADD COLUMN nouveau_champ TEXT DEFAULT '';

# 4. Redémarrer l'application
```

### Problème 2 : "Cannot connect to database"

**Symptôme** :
```
sqlalchemy.exc.OperationalError: unable to open database file
```

**Cause** : Variable `DATABASE_URL` manquante ou incorrecte.

**Solution** :
```bash
# Vérifier DATABASE_URL
echo $DATABASE_URL

# Si vide, la définir
export DATABASE_URL="sqlite:///gec_mines.db"
# OU pour PostgreSQL
export DATABASE_URL="postgresql://user:pass@localhost:5432/gec_mines"

# Redémarrer
```

### Problème 3 : "Encryption key error" / Données illisibles

**Symptôme** :
```
ValueError: Invalid padding bytes
# OU
Les données chiffrées ne peuvent pas être déchiffrées
```

**Cause** : `GEC_MASTER_KEY` a changé ou est manquante.

**Solution** :
```bash
# 1. Vérifier la clé
echo $GEC_MASTER_KEY

# 2. Si elle est différente, restaurer l'ancienne
export GEC_MASTER_KEY="votre_ancienne_cle"

# 3. Si vous l'avez perdue, restaurer depuis backup
source .env.backup

# 4. Redémarrer
```

**⚠️ IMPORTANT** : Si vous avez perdu `GEC_MASTER_KEY`, les données chiffrées sont **irrécupérables**.

### Problème 4 : Conflits Git lors du pull

**Symptôme** :
```
error: Your local changes to the following files would be overwritten by merge:
    views.py
    models.py
```

**Solution 1 - Écraser vos modifications** :
```bash
git reset --hard origin/main
```

**Solution 2 - Garder vos modifications** :
```bash
# Sauvegarder vos modifications
git stash

# Mettre à jour
git pull origin main

# Tenter de restaurer (peut causer des conflits)
git stash pop

# Si conflits, résoudre manuellement
git status
# Éditer les fichiers en conflit
# Puis
git add .
git stash drop
```

### Problème 5 : Dépendances manquantes après update

**Symptôme** :
```
ModuleNotFoundError: No module named 'nouvelle_lib'
```

**Solution** :
```bash
# Réinstaller toutes les dépendances
pip install -r requirements.txt --upgrade

# OU forcer la réinstallation
pip install -r requirements.txt --force-reinstall

# Vérifier
pip list
```

### Problème 6 : Port 5000 déjà utilisé

**Symptôme** :
```
OSError: [Errno 48] Address already in use
```

**Solution** :
```bash
# Linux / macOS - Trouver et tuer le processus
lsof -ti:5000 | xargs kill -9

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Puis redémarrer
```

## 📊 Vérifier l'Historique des Migrations

### Via la Base de Données

```sql
-- Voir toutes les migrations appliquées
SELECT * FROM migration_log ORDER BY applied_at DESC LIMIT 10;

-- Voir les migrations récentes (aujourd'hui)
SELECT * FROM migration_log 
WHERE DATE(applied_at) = DATE('now')
ORDER BY applied_at DESC;

-- Voir les migrations échouées
SELECT * FROM migration_log 
WHERE status = 'error'
ORDER BY applied_at DESC;
```

### Via les Logs de l'Application

```bash
# Linux / macOS
tail -f app.log | grep migration

# Windows
Get-Content app.log -Tail 50 | Select-String "migration"
```

## 🔄 Mise à Jour depuis une Version Spécifique

### Revenir à une Version Précédente (Rollback)

```bash
# Voir l'historique des commits
git log --oneline -10

# Revenir à un commit spécifique
git reset --hard <commit-hash>

# Exemple
git reset --hard a1b2c3d

# Mettre à jour les dépendances
pip install -r requirements.txt

# Redémarrer
```

### Mettre à Jour vers une Branche Spécifique

```bash
# Voir les branches disponibles
git branch -a

# Changer de branche
git checkout develop
# OU
git checkout feature/nouvelle-fonctionnalite

# Mettre à jour
git pull origin develop

# Mettre à jour les dépendances
pip install -r requirements.txt
```

## 📋 Script de Mise à Jour Automatique

### Linux / macOS - `update.sh`

Créez un fichier `update.sh` :

```bash
#!/bin/bash
set -e

echo "🔄 Mise à jour GEC depuis GitHub..."

# 1. Arrêter l'application
echo "⏸️  Arrêt de l'application..."
pkill -f "gunicorn.*main:app" || true
pkill -f "python.*main.py" || true
sleep 2

# 2. Forcer la mise à jour du code
echo "📥 Récupération du code..."
git fetch origin
git reset --hard origin/main

# 3. Mettre à jour les dépendances
echo "📦 Mise à jour des dépendances..."
pip install -r requirements.txt --upgrade

# 4. Redémarrer l'application
echo "🚀 Redémarrage de l'application..."
nohup gunicorn --bind 0.0.0.0:5000 --reload main:app > app.log 2>&1 &

echo "✅ Mise à jour terminée !"
echo "📋 Vérifiez les logs : tail -f app.log"
```

**Utilisation** :
```bash
chmod +x update.sh
./update.sh
```

### Windows - `update.ps1`

Créez un fichier `update.ps1` :

```powershell
Write-Host "🔄 Mise à jour GEC depuis GitHub..." -ForegroundColor Cyan

# 1. Arrêter l'application
Write-Host "⏸️  Arrêt de l'application..." -ForegroundColor Yellow
Get-Process -Name python,gunicorn -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# 2. Forcer la mise à jour du code
Write-Host "📥 Récupération du code..." -ForegroundColor Yellow
git fetch origin
git reset --hard origin/main

# 3. Mettre à jour les dépendances
Write-Host "📦 Mise à jour des dépendances..." -ForegroundColor Yellow
pip install -r requirements.txt --upgrade

# 4. Redémarrer l'application
Write-Host "🚀 Redémarrage de l'application..." -ForegroundColor Yellow
Start-Process python -ArgumentList "main.py" -NoNewWindow

Write-Host "✅ Mise à jour terminée !" -ForegroundColor Green
```

**Utilisation** :
```powershell
.\update.ps1
```

## ✅ Checklist de Mise à Jour

Avant de commencer :
- [ ] Application arrêtée
- [ ] Sauvegarde récente des données (optionnel mais recommandé)
- [ ] Accès au dépôt GitHub

Mise à jour :
- [ ] Code mis à jour (`git reset --hard origin/main`)
- [ ] Dépendances mises à jour (`pip install -r requirements.txt`)
- [ ] Variables d'environnement vérifiées (`.env`)
- [ ] Application redémarrée

Vérification :
- [ ] Logs vérifiés (migrations appliquées)
- [ ] Connexion fonctionne
- [ ] Données existantes visibles
- [ ] Nouvelles fonctionnalités accessibles

## 🔐 Sécurité

### Ce qui NE SERA JAMAIS écrasé par Git

Ces fichiers sont protégés via `.gitignore` :
- `.env` - Variables d'environnement
- `gec_mines.db` - Base de données
- `uploads/` - Fichiers uploadés
- `backups/` - Sauvegardes
- `exports/` - Exports de courriers

### Vérifier le .gitignore

```bash
cat .gitignore
```

Doit contenir au minimum :
```
.env
.env.backup
gec_mines.db
uploads/
exports/
backups/
__pycache__/
*.pyc
venv/
```

## 📞 Support

En cas de problème :
1. ✅ Vérifiez les logs : `tail -f app.log`
2. ✅ Consultez `migration_log` dans la BD
3. ✅ Vérifiez `CHANGELOG.md` pour les changements récents
4. ✅ Restaurez depuis backup si nécessaire

---

**Résumé** : `git reset --hard origin/main` + `pip install -r requirements.txt` + redémarrer = Mise à jour complète sans toucher aux données ! 🚀
