# GEC Mines - Système de Gestion Électronique du Courrier

## Vue d'ensemble

GEC Mines est un système complet de gestion électronique du courrier développé pour le Secrétariat Général des Mines de la République Démocratique du Congo. Le système permet de gérer efficacement les courriers entrants et sortants avec un suivi complet et des capacités d'export avancées.

## Fonctionnalités Principales

- **Gestion complète du courrier** : Enregistrement, suivi et archivage des courriers entrants/sortants
- **Date de rédaction** : Suivi de la date de rédaction de la lettre en plus de la date d'enregistrement
- **Authentification sécurisée** : Système de rôles (Super Admin, Admin, Utilisateur)
- **Gestion des départements** : Organisation hiérarchique avec permissions granulaires
- **Recherche avancée** : Filtres multiples incluant les dates de rédaction
- **Export PDF** : Accusés de réception et listes formatées
- **Sauvegarde/Restauration** : Système complet de backup
- **Multilingue** : Interface en français et anglais
- **Responsive** : Compatible mobile et desktop

## Installation Rapide

```bash
# 1. Configurer la base de données
export DATABASE_URL="postgresql://user:password@localhost/gec_mines"
export SESSION_SECRET="your-secret-key"

# 2. Initialiser automatiquement
python init_database.py

# 3. Lancer l'application
gunicorn --bind 0.0.0.0:5000 main:app
```

## Connexion par Défaut

- **Nom d'utilisateur** : `admin`
- **Mot de passe** : `admin123`

⚠️ **Important** : Changez le mot de passe administrateur après la première connexion.

## Documentation Complète

📚 **Toute la documentation détaillée se trouve dans le dossier [`docs/`](docs/)**

### Guides Principaux
- **[Vue d'ensemble complète](docs/README_FR.md)** - Fonctionnalités détaillées
- **[Guide de démarrage rapide](docs/QUICKSTART.md)** - Installation en 5 minutes
- **[Index de documentation](docs/INDEX_DOCUMENTATION.md)** - Accès à tous les guides

### Installation
- **[Installation cPanel](docs/INSTALL_CPANEL_FR.md)** - Hébergement partagé
- **[Installation VPS](docs/INSTALL_VPS_FR.md)** - Serveur privé
- **[Configuration base de données](docs/DATABASE_SETUP_FR.md)** - Scripts SQL

### Documentation Anglaise
- **[Complete overview](docs/README_EN.md)** - Detailed features
- **[cPanel installation](docs/INSTALL_CPANEL_EN.md)** - Shared hosting
- **[VPS installation](docs/INSTALL_VPS_EN.md)** - Private server
- **[Database setup](docs/DATABASE_SETUP_EN.md)** - SQL scripts

## Technologies

- **Backend** : Flask, SQLAlchemy, PostgreSQL
- **Frontend** : Tailwind CSS, Font Awesome
- **Sécurité** : Flask-Login, hash des mots de passe
- **Export** : ReportLab pour PDF
- **Déploiement** : Gunicorn, Nginx

## Structure du Projet

```
gec-mines/
├── docs/                    # 📚 Documentation complète
├── init_database.py        # 🔧 Script initialisation automatique
├── main.py                 # 🚀 Point d'entrée application
├── app.py                  # ⚙️ Configuration Flask
├── models.py               # 🗄️ Modèles de données
├── views.py                # 🌐 Routes et vues
├── utils.py                # 🛠️ Fonctions utilitaires
├── templates/              # 📄 Templates HTML
├── static/                 # 🎨 Ressources statiques
├── uploads/                # 📎 Fichiers téléchargés
├── exports/                # 📊 Exports PDF
├── backups/                # 💾 Sauvegardes système
└── lang/                   # 🌍 Fichiers de traduction
```

## Support

Pour une assistance technique :
1. **Consultez la documentation** dans `docs/`
2. **Vérifiez les logs** d'application
3. **Contactez l'équipe** de développement

## Licence

© 2025 GEC. Made with 💖 and ☕ By MOA-Digital Agency LLC

---

**Version** : 2.1.0  
**Dernière mise à jour** : Juillet 2025