# GEC Mines - Système de Gestion Électronique du Courrier

## Vue d'ensemble

GEC (Gestion Électronique du Courrier) est un système complet de gestion documentaire développé spécifiquement pour le **Secrétariat Général des Mines de la République Démocratique du Congo**. Cette application web moderne permet la digitalisation complète du processus de traitement du courrier administratif avec des fonctionnalités avancées de suivi, archivage et reporting.

## 🚀 Fonctionnalités principales

### 📨 Gestion du Courrier
- **Enregistrement bidirectionnel** : Courriers entrants et sortants
- **Génération automatique** d'accusés de réception avec format personnalisable
- **Upload de fichiers** multiples (PDF, images, documents)
- **Métadonnées complètes** : expéditeur/destinataire, référence, objet, date
- **Statuts dynamiques** : Reçu, En cours, Traité, Archivé, Urgent

### 🔍 Recherche et filtrage
- **Recherche textuelle** globale dans tous les champs
- **Filtres avancés** par date, statut, type, expéditeur/destinataire
- **Tri dynamique** par date, numéro, contact, objet
- **Pagination intelligente** avec navigation rapide

### 👥 Système de rôles et permissions
- **3 niveaux hiérarchiques** : Super Admin, Admin, Utilisateur
- **Permissions granulaires** : 
  - `read_all_mail` : Accès complet (Super Admin)
  - `read_department_mail` : Accès départemental (Admin)
  - `read_own_mail` : Accès personnel (Utilisateur)
- **Gestion des utilisateurs** : Création, édition, suppression
- **Départements** : Organisation par structure administrative

### 🌍 Multilingue
- **Support natif** français/anglais
- **Interface adaptative** selon la langue utilisateur
- **Traductions complètes** de tous les éléments UI

### 📊 Tableaux de bord et reporting
- **Dashboard exécutif** avec métriques en temps réel
- **Statistiques visuelles** : aujourd'hui, semaine, mois
- **Logs d'activité** détaillés pour audit
- **Export PDF** personnalisé avec en-têtes officiels

### ⚙️ Configuration système
- **Paramètres globaux** : nom logiciel, logos, coordonnées
- **Format d'accusé** personnalisable avec variables dynamiques
- **Branding** : logos PDF distincts, titres, sous-titres
- **Footer** configurable avec copyright crypté

## 🛠 Architecture technique

### Backend
- **Framework** : Flask (Python)
- **ORM** : SQLAlchemy avec PostgreSQL
- **Authentification** : Flask-Login avec sessions sécurisées
- **Sécurité** : Hachage Werkzeug, validation CSRF
- **Génération PDF** : ReportLab avec templates personnalisés

### Frontend
- **Framework CSS** : Tailwind CSS avec thème RDC
- **JavaScript** : Vanilla JS + jQuery pour DataTables
- **Templates** : Jinja2 avec héritage modulaire
- **Design System** : Couleurs nationales RDC (bleu #003087, jaune #FFD700, rouge #CE1126, vert #009639)
- **Responsive** : Support mobile/tablette complet

### Base de données
- **Modèles principaux** :
  - `User` : Utilisateurs et permissions
  - `Courrier` : Documents avec métadonnées
  - `Departement` : Structure organisationnelle
  - `LogActivite` : Audit trail complet
  - `ParametresSysteme` : Configuration globale
  - `StatutCourrier` : États personnalisables
  - `Role` : Système de rôles avancé

## 🚀 Installation et déploiement

### Prérequis
- Python 3.8+
- PostgreSQL
- Node.js (pour outils de build optionnels)

### Configuration rapide
```bash
# Variables d'environnement
DATABASE_URL=postgresql://user:pass@host:port/db
SESSION_SECRET=your_secret_key

# Installation des dépendances
pip install -r requirements.txt

# Lancement
python main.py
```

### Utilisateur par défaut
- **Login** : `admin`
- **Mot de passe** : `admin123`
- **Rôle** : Super Administrateur

## 🎨 Interface utilisateur

### Thème visuel
L'interface utilise les **couleurs nationales de la RDC** pour une identité visuelle patriotique :
- **Bleu RDC** (#003087) : Navigation, boutons primaires
- **Jaune** (#FFD700) : Actions de recherche
- **Rouge** (#CE1126) : Actions d'export, alertes
- **Vert** (#009639) : Actions de validation, succès

### Expérience utilisateur
- **Navigation hamburger universelle** sur tous les écrans
- **Actions rapides** contextuelles sur chaque page
- **Feedback visuel** immédiat pour toutes les actions
- **Messages flash** pour confirmations/erreurs
- **Tooltips** informatifs sur les fonctions avancées

## 📈 Flux de travail type

1. **Connexion** utilisateur avec gestion de session
2. **Dashboard** : Vue d'ensemble des activités récentes
3. **Enregistrement** : Upload de courrier avec métadonnées
4. **Traitement** : Changement de statut et suivi
5. **Recherche** : Filtrage et consultation historique
6. **Export** : Génération de rapports PDF officiels
7. **Administration** : Gestion des utilisateurs et paramètres

## 🔒 Sécurité

- **Authentification** obligatoire sur toutes les routes
- **Validation** côté serveur pour tous les inputs
- **Permissions** vérifiées à chaque accès document
- **Logs** complets pour traçabilité administrative
- **Upload** sécurisé avec validation de type fichier
- **Session** expirable avec protection CSRF

## 🌟 Points forts

- **100% responsive** : Fonctionne parfaitement sur mobile
- **Performance optimisée** : Pagination, cache, index DB
- **Scalabilité** : Architecture modulaire extensible
- **Maintenance** : Code documenté et structuré
- **Conformité** : Respecte les standards administratifs RDC

## 📞 Support

Pour questions techniques ou demandes d'évolution, contactez l'équipe de développement via les canaux officiels du Secrétariat Général des Mines.

---

**© 2025 GEC. Made with 💖 and ☕ By MOA-Digital Agency LLC**