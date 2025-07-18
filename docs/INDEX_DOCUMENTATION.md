# Index de la Documentation - GEC Mines

## Vue d'ensemble

Cette documentation complète couvre tous les aspects de l'installation, la configuration et l'utilisation du système GEC Mines. Tous les documents sont disponibles en français et en anglais.

## 📚 Documentation Utilisateur

### Guides Principaux (Français)
- **[README_FR.md](./README_FR.md)** - Vue d'ensemble complète du système avec toutes les fonctionnalités
- **[QUICKSTART.md](./QUICKSTART.md)** - Guide de démarrage rapide (5 minutes)

### Guides Principaux (English)
- **[README_EN.md](./README_EN.md)** - Complete system overview with all features

## 🛠 Installation et Configuration

### Installation sur Hébergement Partagé
- **[INSTALL_CPANEL_FR.md](./INSTALL_CPANEL_FR.md)** - Guide complet cPanel (français)
- **[INSTALL_CPANEL_EN.md](./INSTALL_CPANEL_EN.md)** - Complete cPanel guide (English)

### Installation sur Serveur Privé (VPS)
- **[INSTALL_VPS_FR.md](./INSTALL_VPS_FR.md)** - Guide complet VPS/serveur dédié (français)
- **[INSTALL_VPS_EN.md](./INSTALL_VPS_EN.md)** - Complete VPS/dedicated server guide (English)

### Installation sur PythonAnywhere ⭐ **NOUVEAU**
- **[INSTALL_PYTHONANYWHERE_FR.md](./INSTALL_PYTHONANYWHERE_FR.md)** - Guide complet PythonAnywhere (français)
- **[INSTALL_PYTHONANYWHERE_EN.md](./INSTALL_PYTHONANYWHERE_EN.md)** - Complete PythonAnywhere guide (English)

### Configuration Base de Données
- **[DATABASE_SETUP_FR.md](./DATABASE_SETUP_FR.md)** - Scripts SQL et procédures (français)
- **[DATABASE_SETUP_EN.md](./DATABASE_SETUP_EN.md)** - SQL scripts and procedures (English)

## 🗄 Scripts et Utilitaires

### Scripts SQL
- **[init_database.sql](./init_database.sql)** - Script de création des tables PostgreSQL
- **[init_data.sql](./init_data.sql)** - Script d'insertion des données initiales

### Scripts Python
- **[../init_database.py](../init_database.py)** - Script d'initialisation automatique Python

## 📋 Fonctionnalités par Version

### Version 2.1.0 (Juillet 2025)
- ✅ **Date de rédaction** : Suivi des dates de rédaction des lettres
- ✅ **Filtres avancés** : Recherche par période de rédaction
- ✅ **Documentation complète** : Guides multilingues complets
- ✅ **Scripts d'initialisation** : Automatisation de l'installation
- ✅ **Export PDF amélioré** : Inclusion des dates de rédaction
- ✅ **Logos PDF optimisés** : Préservation automatique des proportions d'image ⭐ **NOUVEAU**
- ✅ **Route Flask uploads** : Service sécurisé des fichiers uploadés ⭐ **NOUVEAU**
- ✅ **Sécurité renforcée** : Suppression des identifiants par défaut ⭐ **NOUVEAU**
- ✅ **Guide PythonAnywhere** : Documentation déploiement cloud ⭐ **NOUVEAU**

### Version 2.0.0 (Juillet 2025)
- ✅ **Système de sauvegarde/restauration** complet
- ✅ **Gestion des rôles et permissions** granulaire
- ✅ **Interface multilingue** (français/anglais)
- ✅ **Système de départements** avec hiérarchie
- ✅ **Navigation mobile** responsive

### Version 1.0.0 (Juillet 2025)
- ✅ **Gestion de courrier** entrant/sortant
- ✅ **Authentification** et sessions
- ✅ **Export PDF** avec accusés de réception
- ✅ **Interface Tailwind CSS** aux couleurs RDC

## 🔧 Configuration Technique

### Variables d'Environnement Requises
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/gec_mines
SESSION_SECRET=votre_cle_secrete_complexe
FLASK_ENV=production
```

### Dépendances Principales
- Flask 3.0.0
- PostgreSQL 12+
- Python 3.11+
- Gunicorn (production)

### Structure de Base de Données
```
Tables principales :
├── user (utilisateurs)
├── courrier (documents)
├── departement (organisation)
├── role (rôles système)
├── role_permission (permissions)
├── statut_courrier (états)
├── log_activite (audit)
└── parametres_systeme (configuration)
```

## 🚀 Déploiement

### Environnements Supportés
- **Développement** : SQLite + Flask dev server
- **Production cPanel** : PostgreSQL/MySQL + Apache/LiteSpeed
- **Production VPS** : PostgreSQL + Nginx + Gunicorn
- **Production PythonAnywhere** : PostgreSQL/MySQL + WSGI ⭐ **NOUVEAU**

### Checklist de Déploiement
- [ ] Base de données configurée
- [ ] Variables d'environnement définies
- [ ] Dépendances Python installées
- [ ] Tables initialisées
- [ ] Permissions dossiers configurées
- [ ] SSL/HTTPS activé (production)
- [ ] Mot de passe admin changé

## 🔒 Sécurité

### Mesures Implémentées
- Hachage sécurisé des mots de passe
- Protection CSRF
- Validation des uploads
- Logs d'audit complets
- Sessions sécurisées

### Recommandations Production
- Utiliser HTTPS uniquement
- Changer tous les mots de passe par défaut
- Configurer un pare-feu
- Sauvegardes automatisées
- Monitoring des logs

## 📞 Support

### Ordre de Résolution des Problèmes
1. **Consultez cette documentation** dans l'ordre approprié
2. **Vérifiez les logs** application et serveur web
3. **Testez la connectivité** base de données
4. **Contactez l'équipe** de développement

### Logs Importants
- `logs/error.log` - Erreurs application
- `logs/access.log` - Accès HTTP
- `/var/log/nginx/` - Logs Nginx (VPS)
- Logs PostgreSQL système

## 🔄 Maintenance

### Tâches Régulières
- **Quotidien** : Vérification des logs d'erreur
- **Hebdomadaire** : Sauvegarde complète
- **Mensuel** : Mise à jour des dépendances
- **Trimestriel** : Audit de sécurité

### Commandes Utiles
```bash
# Sauvegarde manuelle
python -c "from views import create_system_backup; create_system_backup()"

# Vérification base de données
python init_database.py --verify

# Logs en temps réel
tail -f logs/error.log
```

---

**Note** : Cette documentation est maintenue à jour avec chaque version. Consultez toujours la version la plus récente avant une installation ou mise à jour.

**Version Documentation** : 2.1.0  
**Dernière Mise à Jour** : Juillet 2025