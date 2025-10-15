# Guide de Mise à Jour via GitHub

Ce guide explique comment mettre à jour votre instance GEC locale depuis GitHub sans perdre vos données actuelles, sur différents systèmes d'exploitation.

## 📋 Prérequis

- Git installé sur votre système
- Accès au dépôt GitHub du projet GEC
- Sauvegarde récente de vos données (recommandé)

## 🔄 Processus de Mise à Jour

### Étape 1 : Sauvegarde des Données

**IMPORTANT** : Créez toujours une sauvegarde avant toute mise à jour !

#### Via l'Interface Web
1. Connectez-vous en tant que super administrateur
2. Allez dans **Gestion des Sauvegardes**
3. Cliquez sur **"Créer une Sauvegarde"**
4. Téléchargez le fichier ZIP de sauvegarde

#### Via la Base de Données
```bash
# PostgreSQL
pg_dump -U username -d gec_mines > backup_$(date +%Y%m%d_%H%M%S).sql

# SQLite
cp gec_mines.db backup_gec_mines_$(date +%Y%m%d_%H%M%S).db
```

### Étape 2 : Sauvegarder les Fichiers Uploadés

```bash
# Linux / macOS
cp -r uploads uploads_backup_$(date +%Y%m%d_%H%M%S)

# Windows (PowerShell)
Copy-Item -Path uploads -Destination "uploads_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')" -Recurse
```

### Étape 3 : Sauvegarder les Variables d'Environnement

**CRITIQUE** : Sauvegardez vos clés de chiffrement !

```bash
# Linux / macOS
echo "GEC_MASTER_KEY=$GEC_MASTER_KEY" > .env.backup
echo "GEC_PASSWORD_SALT=$GEC_PASSWORD_SALT" >> .env.backup
echo "SESSION_SECRET=$SESSION_SECRET" >> .env.backup
echo "DATABASE_URL=$DATABASE_URL" >> .env.backup

# Windows (PowerShell)
"GEC_MASTER_KEY=$env:GEC_MASTER_KEY" | Out-File -FilePath .env.backup
"GEC_PASSWORD_SALT=$env:GEC_PASSWORD_SALT" | Out-File -Append -FilePath .env.backup
"SESSION_SECRET=$env:SESSION_SECRET" | Out-File -Append -FilePath .env.backup
"DATABASE_URL=$env:DATABASE_URL" | Out-File -Append -FilePath .env.backup
```

### Étape 4 : Mise à Jour du Code

#### Linux / macOS

```bash
# 1. Sauvegarder les modifications locales non commitées
git stash

# 2. Récupérer les dernières modifications
git fetch origin

# 3. Mettre à jour la branche principale
git pull origin main

# 4. Restaurer vos modifications locales (si nécessaire)
git stash pop
```

#### Windows (PowerShell)

```powershell
# 1. Sauvegarder les modifications locales non commitées
git stash

# 2. Récupérer les dernières modifications
git fetch origin

# 3. Mettre à jour la branche principale
git pull origin main

# 4. Restaurer vos modifications locales (si nécessaire)
git stash pop
```

### Étape 5 : Mise à Jour des Dépendances

#### Linux / macOS

```bash
# Activer l'environnement virtuel (si utilisé)
source venv/bin/activate

# Mettre à jour les dépendances
pip install -r requirements.txt --upgrade
# OU si vous utilisez uv
uv pip install -r pyproject.toml --upgrade
```

#### Windows

```powershell
# Activer l'environnement virtuel (si utilisé)
.\venv\Scripts\Activate.ps1

# Mettre à jour les dépendances
pip install -r requirements.txt --upgrade
```

### Étape 6 : Migration de la Base de Données

L'application GEC gère automatiquement les migrations au démarrage. Le système applique :

1. **Migrations automatiques** (via `migration_utils.py`)
   - Détecte les nouvelles colonnes manquantes
   - Ajoute automatiquement les colonnes avec valeurs par défaut
   - Log toutes les modifications dans la table `migration_log`

2. **Corrections spécifiques à PostgreSQL** (si applicable)
   - Ajustements de types de données
   - Optimisations d'index

#### Vérification des Migrations

```bash
# Démarrer l'application
python main.py

# Vérifier les logs pour voir les migrations appliquées
# Vous devriez voir des messages comme :
# INFO:root:✓ Colonne 'nouveau_champ' ajoutée à la table 'courrier'
# INFO:root:🔄 2 migration(s) automatique(s) appliquée(s) avec succès
```

### Étape 7 : Restaurer les Variables d'Environnement

Si vos variables d'environnement ont été réinitialisées :

#### Linux / macOS

```bash
# Charger depuis le backup
source .env.backup

# OU éditer manuellement .env
nano .env
```

#### Windows

```powershell
# Charger depuis le backup
Get-Content .env.backup | ForEach-Object {
    $name, $value = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($name, $value, 'Process')
}

# OU éditer manuellement
notepad .env
```

### Étape 8 : Redémarrer l'Application

#### Linux / macOS

```bash
# Arrêter l'application existante
pkill -f "gunicorn.*main:app"

# Redémarrer
gunicorn --bind 0.0.0.0:5000 --reload main:app
```

#### Windows

```powershell
# Arrêter l'application existante (trouver le PID)
Get-Process -Name python | Stop-Process -Force

# Redémarrer
python main.py
```

## 🔧 Résolution des Problèmes de Migration

### Problème : Erreur "Column does not exist"

**Cause** : Migration automatique non appliquée

**Solution** :
1. Vérifiez les logs de l'application au démarrage
2. Si la migration a échoué, appliquez-la manuellement :

```sql
-- PostgreSQL
ALTER TABLE nom_table ADD COLUMN nom_colonne TYPE_DONNEE DEFAULT valeur_defaut;

-- SQLite
ALTER TABLE nom_table ADD COLUMN nom_colonne TYPE_DONNEE DEFAULT valeur_defaut;
```

### Problème : Erreur "Encryption key mismatch"

**Cause** : Les clés de chiffrement ont changé

**Solution** :
1. Restaurez `GEC_MASTER_KEY` et `GEC_PASSWORD_SALT` depuis `.env.backup`
2. Redémarrez l'application

```bash
export GEC_MASTER_KEY="votre_cle_sauvegardee"
export GEC_PASSWORD_SALT="votre_sel_sauvegarde"
```

### Problème : Erreur "IntegrityError" ou "Foreign Key Constraint"

**Cause** : Incohérence dans les données après migration

**Solution** :
1. Vérifiez les logs pour identifier la contrainte violée
2. Nettoyez les données orphelines :

```sql
-- Exemple : Supprimer les références à des utilisateurs supprimés
DELETE FROM courrier WHERE utilisateur_id NOT IN (SELECT id FROM user WHERE actif = TRUE);
```

### Problème : Données chiffrées illisibles

**Cause** : Perte ou modification de la clé `GEC_MASTER_KEY`

**Solution** :
1. **Si vous avez la clé de sauvegarde** :
   ```bash
   export GEC_MASTER_KEY="cle_de_sauvegarde"
   ```

2. **Si la clé est perdue** :
   - Les données chiffrées sont **irrécupérables**
   - Restaurez depuis une sauvegarde complète
   - Ou utilisez l'export/import pour migrer les données déchiffrées

## 📦 Cas Particulier : Migration avec Changement de Clé

Si vous devez changer de clé de chiffrement :

### 1. Exporter les Données (avec l'ancienne clé)

```bash
# Assurez-vous que GEC_MASTER_KEY contient l'ancienne clé
export GEC_MASTER_KEY="ancienne_cle"
python main.py
```

Via l'interface :
1. **Gestion des Sauvegardes** > **Export de Courriers**
2. Exportez tous les courriers
3. Téléchargez le fichier ZIP

### 2. Générer et Configurer la Nouvelle Clé

```bash
# Générer une nouvelle clé
python generate_keys.py

# Ou manuellement
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```bash
# Configurer la nouvelle clé
export GEC_MASTER_KEY="nouvelle_cle"
export GEC_PASSWORD_SALT="nouveau_sel"
```

### 3. Réinitialiser la Base de Données

```bash
# PostgreSQL
psql -U username -d gec_mines -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# SQLite
rm gec_mines.db
```

### 4. Redémarrer et Importer

```bash
python main.py
```

Via l'interface :
1. **Gestion des Sauvegardes** > **Import de Courriers**
2. Uploadez le fichier ZIP d'export
3. Les données seront re-chiffrées avec la nouvelle clé

## ✅ Vérification Post-Mise à Jour

### 1. Vérifier les Logs

```bash
# Les logs doivent afficher :
# ✓ Migrations automatiques appliquées
# ✓ Admin user created/updated
# ✓ System parameters initialized
```

### 2. Tester les Fonctionnalités Clés

- [ ] Connexion avec utilisateur existant
- [ ] Création d'un nouveau courrier
- [ ] Recherche et filtrage
- [ ] Visualisation des pièces jointes
- [ ] Export/Import de courriers

### 3. Vérifier l'Intégrité des Données

Via l'interface :
1. **Tableau de Bord** : Vérifiez les statistiques
2. **Liste des Courriers** : Vérifiez que tous les courriers sont présents
3. **Recherche** : Testez la recherche sur des données chiffrées

## 🆘 En Cas de Problème Majeur

### Rollback Complet

Si la mise à jour a causé des problèmes critiques :

```bash
# 1. Revenir à la version précédente du code
git reset --hard HEAD~1

# 2. Restaurer la base de données
# PostgreSQL
psql -U username -d gec_mines < backup_YYYYMMDD_HHMMSS.sql

# SQLite
cp backup_gec_mines_YYYYMMDD_HHMMSS.db gec_mines.db

# 3. Restaurer les fichiers uploadés
rm -rf uploads
mv uploads_backup_YYYYMMDD_HHMMSS uploads

# 4. Redémarrer
python main.py
```

## 📝 Checklist de Mise à Jour

- [ ] Sauvegarde de la base de données créée
- [ ] Sauvegarde des fichiers `uploads/` créée
- [ ] Variables d'environnement sauvegardées (`.env.backup`)
- [ ] Code mis à jour depuis GitHub (`git pull`)
- [ ] Dépendances mises à jour (`pip install -r requirements.txt`)
- [ ] Application redémarrée
- [ ] Logs vérifiés (migrations appliquées)
- [ ] Tests fonctionnels effectués
- [ ] Données vérifiées (statistiques, courriers, recherche)

## 🔐 Sécurité

**IMPORTANT** : Ne jamais partager ou commiter :
- `.env` ou `.env.backup`
- `GEC_MASTER_KEY`
- `GEC_PASSWORD_SALT`
- `SESSION_SECRET`

Ces informations permettent de déchiffrer toutes vos données sensibles !

## 📞 Support

En cas de problème pendant la mise à jour :
1. Consultez les logs de l'application
2. Vérifiez la table `migration_log` dans la base de données
3. Référez-vous au `CHANGELOG.md` pour les changements récents
4. Contactez l'équipe de support avec les logs d'erreur
