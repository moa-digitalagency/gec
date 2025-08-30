# GEC - Système de Gestion Électronique du Courrier

**[English Version](README_EN.md)**

## Aperçu

GEC (Gestion Électronique du Courrier) est une application web Flask complète pour la gestion numérique de la correspondance. Développée spécialement pour les administrations et entreprises, elle offre une solution sécurisée et auditable pour l'enregistrement, le suivi et la gestion des courriers avec fichiers joints.

## Fonctionnalités Principales

### 🔐 Authentification et Sécurité
- **Authentification utilisateur sécurisée** avec Flask-Login
- **Chiffrement AES-256** pour toutes les données sensibles
- **Hachage bcrypt** avec sels personnalisés pour les mots de passe
- **Protection contre les attaques** : brute force, injection SQL, XSS
- **Blocage IP automatique** après tentatives de connexion échouées
- **Vérification d'intégrité des fichiers** avec checksums
- **Suppression sécurisée** des fichiers
- **Journalisation complète** de sécurité et d'audit

### 👥 Gestion des Utilisateurs et Rôles
- **Système de rôles à trois niveaux** : Super Admin, Admin, Utilisateur
- **Permissions granulaires** configurables
- **Contrôle d'accès basé sur les rôles** (RBAC)
- **Gestion des départements** et affectations
- **Profils utilisateur** avec informations de contact

### 📧 Gestion du Courrier
- **Enregistrement de courriers** entrants et sortants
- **Fichiers joints obligatoires** pour tous les types de courrier
- **Numérotation automatique** avec accusés de réception
- **Statuts configurables** : En attente, En cours, Traité, Archivé
- **Recherche avancée** avec filtres multiples
- **Types de courriers sortants** personnalisables
- **Gestion des expéditeurs/destinataires**

### 💬 Système de Commentaires et Annotations
- **Commentaires, annotations et instructions** sur les courriers
- **Notifications in-app** et par email
- **Ciblage intelligent** : créateur + dernière personne ayant reçu le courrier
- **Historique complet** des interactions

### 🔄 Transmission et Suivi
- **Transmission de courriers** entre utilisateurs
- **Notifications automatiques** de transmission
- **Historique des transmissions** avec dates et messages
- **Marquage de lecture** automatique
- **Suivi en temps réel** du statut

### 🔔 Notifications
- **Notifications in-app** en temps réel
- **Notifications email** configurables
- **Templates d'email** personnalisables
- **Intégration SendGrid** et SMTP
- **Notifications ciblées** selon les permissions

### 📊 Tableaux de Bord et Rapports
- **Tableau de bord analytique** avec statistiques temps réel
- **Graphiques interactifs** (Chart.js)
- **Export PDF et Excel** des rapports
- **Métriques de performance** et KPI
- **Statistiques par département** et utilisateur

### 📄 Génération de Documents
- **Export PDF** avec mise en page professionnelle
- **Bordereaux d'enregistrement** automatiques
- **Listes de courriers** formatées
- **En-têtes et pieds de page** personnalisables
- **Logos et signatures** dynamiques

### ⚙️ Configuration Système
- **Paramètres système** entièrement configurables
- **Logos personnalisables** (en-tête et signature)
- **Nomenclature organisationnelle** dynamique
- **Formats de numérotation** personnalisables
- **Configuration email** (SMTP/SendGrid)
- **Gestion des statuts** et types de courriers

### 🌍 Multi-langue
- **Support français et anglais**
- **Fichiers de traduction JSON**
- **Commutation de langue** en temps réel
- **Interface entièrement localisée**

### 🔒 Sauvegarde et Migration
- **Système de sauvegarde automatique**
- **Migration automatique** de base de données
- **Détection et ajout automatique** de nouvelles colonnes
- **Préservation des données** existantes
- **Système de rollback** avec checkpoints

## Technologies Utilisées

### Backend
- **Flask** (Framework web Python)
- **SQLAlchemy** avec Flask-SQLAlchemy (ORM)
- **PostgreSQL** (Base de données principale)
- **ReportLab** (Génération PDF)
- **bcrypt + cryptography** (Sécurité)
- **SendGrid** (Service email)

### Frontend
- **Jinja2** (Moteur de templates)
- **Tailwind CSS** (Framework CSS)
- **Font Awesome** (Icônes)
- **DataTables** (Tableaux interactifs)
- **Chart.js** (Graphiques)
- **jQuery** (Interactions JavaScript)

### Sécurité
- **AES-256-CBC** pour le chiffrement des données
- **bcrypt** pour le hachage des mots de passe
- **Protection CSRF** et en-têtes de sécurité
- **Validation et sanitisation** des entrées
- **Audit logging** complet

## Design et UX

- **Couleurs RDC** : Bleu (#003087), Jaune (#FFD700), Rouge (#CE1126), Vert (#009639)
- **Design responsive** adaptatif
- **Interface intuitive** et ergonomique
- **Menu hamburger universel**
- **Préservation du ratio d'aspect** pour les logos
- **Thème corporatif** cohérent

## Installation et Déploiement

### Prérequis
- Python 3.8+
- PostgreSQL
- Serveur web (recommandé : Gunicorn)

### Variables d'Environnement
```
DATABASE_URL=postgresql://user:password@host:port/database
SESSION_SECRET=your_secret_key
SENDGRID_API_KEY=your_sendgrid_key (optionnel)
GEC_MASTER_KEY=your_encryption_key
GEC_PASSWORD_SALT=your_password_salt
```

### Démarrage Rapide
```bash
# Installation des dépendances
pip install -r project-dependencies.txt

# Configuration de la base de données
# (Les tables sont créées automatiquement)

# Démarrage de l'application
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

## Nouvelles Fonctionnalités (Août 2025)

### Nomenclature Dynamique
- **Titres de responsables configurables** (ex: Secrétaire Général, Directeur)
- **Adaptation automatique** dans tous les templates et exports
- **Interface de configuration** dans les paramètres système

### Notifications Avancées
- **Ciblage intelligent** pour commentaires/annotations/instructions
- **Notifications à plusieurs destinataires** : créateur + dernier destinataire
- **Templates email** spécialisés par type d'action
- **Système de permissions** pour notifications

### Améliorations PDF
- **Texte "En Copie"** au lieu de "SG Copie" pour plus de flexibilité
- **Adaptation automatique** à la nomenclature configurée
- **Mise en page optimisée** pour tous types d'organisation

### Système de Migration
- **Migration automatique** des colonnes de base de données
- **Détection intelligente** des changements de schéma
- **Préservation des données** existantes
- **Messages d'information** détaillés

## Support et Contribution

Ce système est développé pour répondre aux besoins spécifiques des administrations et peut être adapté selon les exigences organisationnelles.

Pour plus d'informations techniques, consultez le code source ou contactez l'équipe de développement.

---

**GEC - Système de Gestion du Courrier**  
*Solution digitale pour l'administration moderne*