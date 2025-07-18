# Changelog - GEC Mines

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Versioning Sémantique](https://semver.org/lang/fr/).

## [2.1.0] - 2025-07-17

### 🆕 Ajouté
- **Logos PDF optimisés** : Système de préservation automatique des proportions d'image
- **Route Flask `/uploads/<filename>`** : Service sécurisé des fichiers uploadés avec gestion des permissions
- **Guide PythonAnywhere** : Documentation complète pour déploiement cloud (FR/EN)
- **Sécurité renforcée** : Suppression des identifiants par défaut de la page de connexion
- **Prévisualisation logos** : Affichage immédiat après upload dans les paramètres système

### 🔧 Modifié
- **Calcul dimensions PDF** : Utilisation de PIL pour préserver le ratio d'aspect des logos
- **Gestion des chemins** : Conversion automatique URL relative → chemin absolu pour ReportLab
- **Template login** : Interface épurée sans hints d'identifiants pour la production
- **Documentation** : Mise à jour complète de tous les guides avec nouvelles fonctionnalités

### 🐛 Corrigé
- **Déformation logos PDF** : Les logos conservent maintenant leurs proportions originales
- **Service fichiers uploads** : Route manquante ajoutée pour l'accès aux fichiers uploadés
- **Prévisualisation logos** : Affichage correct dans l'interface d'administration
- **Synchronisation templates** : Cohérence entre pages web et exports PDF

### 🔒 Sécurité
- Suppression de l'affichage des identifiants par défaut en production
- Validation renforcée des fichiers uploadés
- Protection des chemins de fichiers sensibles

## [2.0.0] - 2025-07-14

### 🆕 Ajouté
- **Date de rédaction** : Champ optionnel pour la date de rédaction des lettres
- **Filtres avancés** : Recherche par période de rédaction (du/au)
- **Documentation complète** : Guides FR/EN pour cPanel, VPS, base de données
- **Scripts d'initialisation** : Automatisation complète de l'installation
- **Système de sauvegarde/restauration** : Archives ZIP complètes avec métadonnées
- **Configuration PDF** : Paramètres personnalisables (titre, sous-titre, logo PDF)
- **Footer configurable** : Texte de pied de page personnalisable

### 🔧 Modifié
- **Export PDF** : Inclusion des dates de rédaction dans tous les exports
- **Interface liste courriers** : Colonnes séparées pour dates rédaction/enregistrement
- **Page détail courrier** : Affichage proéminent de la date de rédaction
- **Paramètres système** : Interface complète pour configuration PDF

### 🐛 Corrigé
- **Hardcoded application names** : Utilisation dynamique des paramètres système
- **Synchronisation PDF/pages** : Données identiques affichées partout
- **Templates login/navigation** : Cohérence des paramètres système

## [1.9.0] - 2025-07-13

### 🆕 Ajouté
- **Système multilingue** : Support français/anglais avec fichiers JSON
- **Gestion des rôles** : Système granulaire Super Admin/Admin/Utilisateur
- **Permissions courrier** : Contrôle d'accès par niveau (all/department/own)
- **Navigation mobile** : Menu hamburger universel responsive
- **Journalisation** : Page logs d'activité pour super administrateurs

### 🔧 Modifié
- **Architecture permissions** : Système hiérarchique avec fallback
- **Interface utilisateur** : Design Tailwind CSS aux couleurs RDC
- **Menu navigation** : JavaScript simplifié et fiable
- **Gestion utilisateurs** : CRUD complet avec validation

## [1.8.0] - 2025-07-12

### 🆕 Ajouté
- **Gestion départements** : Organisation hiérarchique avec chefs
- **Photos de profil** : Upload et affichage des photos utilisateurs
- **Statuts courrier** : Système personnalisable avec codes couleur
- **Actions rapides** : Interface optimisée pour actions fréquentes

### 🔧 Modifié
- **Base de données** : Migration vers structure département/rôle
- **Interface** : Amélioration responsive et accessibilité
- **Performance** : Optimisation requêtes et chargement

## [1.0.0] - 2025-07-10

### 🆕 Ajouté
- **Gestion courrier** : Enregistrement entrant/sortant avec métadonnées
- **Authentification** : Système login/logout sécurisé
- **Export PDF** : Génération accusés de réception formatés
- **Recherche** : Filtres multiples et recherche textuelle
- **Upload fichiers** : Support PDF/images avec validation
- **Interface Tailwind** : Design moderne aux couleurs nationales RDC

### 🔧 Fonctionnalités de base
- Framework Flask avec SQLAlchemy ORM
- Base de données PostgreSQL/SQLite
- Templates Jinja2 avec composants réutilisables
- Système de sessions Flask-Login
- Génération PDF avec ReportLab

---

## Légende des Types de Changements

- 🆕 **Ajouté** : Nouvelles fonctionnalités
- 🔧 **Modifié** : Changements dans les fonctionnalités existantes
- 🐛 **Corrigé** : Corrections de bugs
- 🗑️ **Supprimé** : Fonctionnalités supprimées
- 🔒 **Sécurité** : Améliorations de sécurité
- ⚡ **Performance** : Améliorations de performance
- 📖 **Documentation** : Changements de documentation uniquement

## Compatibilité

### Version 2.1.0
- **Python** : 3.11+
- **PostgreSQL** : 12+
- **Navigateurs** : Chrome 90+, Firefox 88+, Safari 14+

### Mise à jour depuis 2.0.0
```bash
# Aucune migration base de données requise
# Mise à jour simple du code
git pull origin main
pip install --upgrade pillow  # Nouvelle dépendance pour logos
```

### Mise à jour depuis 1.x.x
```bash
# Migration base de données requise
python init_database.py --migrate
```

## Notes de Support

- **LTS (Long Term Support)** : Version 2.0.0 (jusqu'en juillet 2026)
- **Support actuel** : Version 2.1.0
- **Obsolescence** : Versions 1.x.x (fin de support juillet 2025)

---

**Maintenu par** : Équipe GEC Mines  
**Contact** : Support technique via documentation  
**Dernière mise à jour** : 17 juillet 2025