# GEC Mines - Système de Gestion Électronique du Courrier

## Vue d'ensemble

GEC Mines est un système complet de gestion électronique du courrier développé pour le Secrétariat Général des Mines de la République Démocratique du Congo. Le système permet de gérer efficacement les courriers entrants et sortants avec un suivi complet, des permissions basées sur les rôles, et des capacités d'export avancées.

## Fonctionnalités Principales

### 🏢 Gestion Administrative
- **Système de rôles** : Super Admin, Admin, Utilisateur avec permissions granulaires
- **Gestion des départements** : Organisation hiérarchique avec chefs de département
- **Authentification sécurisée** : Système de connexion avec hachage des mots de passe
- **Profils utilisateurs** : Photos de profil et informations personnalisées

### 📬 Gestion du Courrier
- **Types de courrier** : Distinction claire entre courriers entrants et sortants
- **Enregistrement complet** : 
  - Date de rédaction (optionnelle)
  - Date d'enregistrement automatique
  - Numéros d'accusé de réception automatiques
  - Pièces jointes (PDF, images)
- **Suivi des statuts** : Statuts personnalisables avec codes couleur
- **Recherche avancée** : Filtres multiples et recherche textuelle

### 📊 Rapports et Exports
- **Export PDF individuel** : Accusé de réception formaté
- **Export de listes** : Rapports PDF avec filtres appliqués
- **Impression** : Fonction d'impression directe
- **Sauvegarde/Restauration** : Système complet de backup

### 🌍 Système Multilingue
- **Langues supportées** : Français (par défaut) et Anglais
- **Interface adaptable** : Changement de langue en temps réel
- **Préférences utilisateur** : Langue sauvegardée par utilisateur

### 🔐 Sécurité et Permissions
- **Accès granulaire** :
  - `read_all_mail` : Accès à tous les courriers (Super Admin)
  - `read_department_mail` : Accès aux courriers du département (Admin)
  - `read_own_mail` : Accès aux courriers personnels (Utilisateur)
- **Journalisation** : Logs d'activité complets
- **Chiffrement** : Copyright et données sensibles protégés

## Technologies Utilisées

### Backend
- **Framework** : Flask (Python 3.11+)
- **Base de données** : PostgreSQL (production) / SQLite (développement)
- **ORM** : SQLAlchemy avec Flask-SQLAlchemy
- **Authentification** : Flask-Login
- **PDF** : ReportLab pour la génération de documents

### Frontend
- **CSS Framework** : Tailwind CSS
- **Icons** : Font Awesome 6.0.0
- **Tables** : DataTables 1.13.6
- **JavaScript** : Vanilla JS avec jQuery

### Design
- **Thème** : Couleurs nationales de la RDC
  - Bleu RDC : #003087
  - Jaune : #FFD700
  - Rouge : #CE1126
  - Vert : #009639

## Installation Rapide

### Prérequis
- Python 3.11+
- PostgreSQL 12+ (recommandé pour la production)
- Git

### Étapes d'installation

1. **Cloner le projet**
```bash
git clone <repository-url>
cd gec-mines
```

2. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

3. **Configurer les variables d'environnement**
```bash
export DATABASE_URL="postgresql://user:password@localhost/gec_mines"
export SESSION_SECRET="your-secret-key-here"
```

4. **Initialiser la base de données**
```bash
python init_database.py
```

5. **Lancer l'application**
```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

6. **Accéder à l'application**
- URL : http://localhost:5000
- Connexion par défaut : `admin` / `admin123`

## Guides d'Installation Détaillés

- [Installation sur cPanel](./INSTALL_CPANEL_FR.md) - Guide complet pour hébergement partagé
- [Installation sur VPS](./INSTALL_VPS_FR.md) - Guide pour serveur privé virtuel
- [Configuration de la base de données](./DATABASE_SETUP_FR.md) - Scripts et procédures SQL

## Documentation Technique

- [Documentation complète](./DOCUMENTATION_FR.md) - Spécifications techniques détaillées
- [Guide de développement](./DEVELOPMENT_GUIDE_FR.md) - Pour les développeurs
- [API et intégrations](./API_REFERENCE_FR.md) - Documentation des APIs

## Support et Maintenance

### Sauvegarde Automatique
Le système inclut un système de sauvegarde/restauration complet accessible aux Super Admins :
- Sauvegarde complète : base de données + fichiers + configuration
- Format ZIP avec métadonnées
- Restauration avec sauvegarde de sécurité automatique

### Journalisation
- Logs d'activité utilisateur
- Logs système pour débogage
- Traçabilité complète des actions

### Maintenance
- Nettoyage automatique des fichiers temporaires
- Optimisation de la base de données
- Monitoring des performances

## Configuration Système

### Paramètres Personnalisables
- Nom du logiciel et logo
- Format des numéros d'accusé de réception
- Informations de l'organisme
- Configuration PDF (titre, sous-titre, logo)
- Texte de pied de page

### Départements et Rôles
- Création de départements personnalisés
- Attribution de chefs de département
- Gestion des permissions par rôle
- Workflow d'approbation configurables

## Sécurité

### Bonnes Pratiques Implémentées
- Hachage sécurisé des mots de passe
- Protection CSRF
- Validation des fichiers uploadés
- Contrôle d'accès granulaire
- Logs d'audit complets

### Recommandations de Déploiement
- Utiliser HTTPS en production
- Configurer un proxy inverse (nginx)
- Sauvegardes régulières automatisées
- Monitoring des logs d'erreur

## Contribuer

Ce projet est développé pour le Secrétariat Général des Mines de la RDC. Pour des modifications ou améliorations, contactez l'équipe de développement.

## Licence

© 2025 GEC. Made with 💖 and ☕ By MOA-Digital Agency LLC

---

**Version** : 2.1.0  
**Dernière mise à jour** : Juillet 2025  
**Compatibilité** : Python 3.11+, PostgreSQL 12+, Navigateurs modernes