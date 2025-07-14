# Guide de Démarrage Rapide - GEC Mines

## Installation Express (5 minutes)

### Option 1 : Installation automatique avec PostgreSQL
```bash
# 1. Cloner le projet
git clone <repository-url>
cd gec-mines

# 2. Variables d'environnement
export DATABASE_URL="postgresql://user:password@localhost:5432/gec_mines"
export SESSION_SECRET="votre_cle_secrete_complexe"

# 3. Installation Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Initialisation automatique
python init_database.py

# 5. Lancement
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

### Option 2 : Installation manuelle
```bash
# 1. Créer la base de données PostgreSQL
createdb gec_mines

# 2. Importer les tables
psql gec_mines < docs/init_database.sql
psql gec_mines < docs/init_data.sql

# 3. Lancer l'application
python main.py
```

## Accès immédiat

- **URL** : http://localhost:5000
- **Connexion** : admin / admin123

## Fonctionnalités essentielles

1. **Enregistrer un courrier** : Menu → Enregistrer courrier
2. **Consulter les courriers** : Menu → Voir courriers  
3. **Rechercher** : Utiliser les filtres avancés
4. **Exporter en PDF** : Bouton d'export sur chaque courrier
5. **Gérer les utilisateurs** : Paramètres → Gestion utilisateurs (Super Admin)

## Structure Documentation

Le dossier `docs/` contient toute la documentation :

### Guides français
- `README_FR.md` - Vue d'ensemble complète
- `DATABASE_SETUP_FR.md` - Configuration base de données
- `INSTALL_CPANEL_FR.md` - Installation sur hébergement partagé
- `INSTALL_VPS_FR.md` - Installation sur serveur privé

### Guides anglais  
- `README_EN.md` - Complete overview
- `DATABASE_SETUP_EN.md` - Database configuration
- `INSTALL_CPANEL_EN.md` - Shared hosting installation
- `INSTALL_VPS_EN.md` - Private server installation

### Scripts SQL
- `init_database.sql` - Création des tables
- `init_data.sql` - Données d'initialisation

### Scripts d'initialisation
- `../init_database.py` - Script automatique d'initialisation

## Configuration requise

### Minimum
- Python 3.11+
- PostgreSQL 12+
- 512 MB RAM
- 1 GB espace disque

### Recommandé
- Python 3.11+
- PostgreSQL 14+
- 2 GB RAM
- 5 GB espace disque
- Nginx (pour production)

## Dépendances principales

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.7.0
psycopg2-binary==2.9.9
reportlab==4.0.7
gunicorn==21.2.0
```

## Sécurité post-installation

1. **Changer le mot de passe admin** immédiatement
2. **Configurer HTTPS** pour la production  
3. **Sauvegarder** régulièrement via l'interface
4. **Mettre à jour** les dépendances régulièrement

## Support rapide

- **Documentation complète** : Dossier `docs/`
- **Logs d'erreur** : Consultez les logs Flask
- **Base de données** : Vérifiez la connexion PostgreSQL
- **Permissions** : Vérifiez les droits sur les dossiers uploads/

---

Pour une installation de production sécurisée, consultez les guides détaillés dans `docs/`.