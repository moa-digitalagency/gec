# GEC Mines - Système de Gestion du Courrier

## Description
Application web complète de gestion du courrier pour le Secrétariat Général des Mines (GEC). Cette solution digitale permet l'enregistrement, le suivi, la recherche et l'archivage des correspondances avec gestion des pièces jointes.

## Fonctionnalités Principales

### 📮 Gestion du Courrier
- **Enregistrement** : Courriers entrants et sortants avec métadonnées complètes
- **Recherche Avancée** : Recherche textuelle indexant toutes les métadonnées
- **Filtres Multiples** : Par type, statut, dates, SG en copie
- **Pièces Jointes Obligatoires** : Upload sécurisé de documents (PDF, JPG, PNG, TIFF)
- **Export PDF** : Génération de documents officiels avec en-tête personnalisable

### 🔐 Sécurité
- **Chiffrement AES-256** : Protection des données sensibles
- **Authentification Sécurisée** : Hachage bcrypt avec salage personnalisé
- **Protection Anti-Attaques** : SQL injection, XSS, CSRF, brute force
- **Audit Complet** : Journalisation de toutes les actions
- **Gestion des Sessions** : Tokens sécurisés avec expiration

### 👥 Gestion des Utilisateurs
- **Rôles Hiérarchiques** : Super Admin, Admin, Utilisateur
- **Permissions Granulaires** : Accès par département ou individuel
- **Départements** : Organisation structurée des utilisateurs

### ⚙️ Paramètres Système
- **Personnalisation** : Logo, nom du logiciel, format des reçus
- **Mode de Numérotation** : Automatique ou manuel
- **Types de Courrier** : Configuration des catégories
- **Statuts Personnalisables** : Workflow adaptatif

### 📊 Fonctionnalités Avancées
- **Tableau de Bord** : Statistiques en temps réel
- **Historique des Modifications** : Traçabilité complète
- **Corbeille** : Système de récupération des courriers supprimés
- **Performance Optimisée** : Cache et indexation stratégique

## Installation

### Prérequis
- Python 3.8+
- PostgreSQL ou SQLite
- 512MB RAM minimum

### Installation Locale

1. **Cloner le repository**
```bash
git clone [URL_DU_REPO]
cd gec-mines
```

2. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

3. **Configuration de l'environnement**
Créer un fichier `.env` avec :
```env
DATABASE_URL=postgresql://user:password@localhost/gecmines
SESSION_SECRET=votre_cle_secrete_tres_longue
GEC_MASTER_KEY=votre_cle_de_chiffrement
GEC_PASSWORD_SALT=votre_sel_personnalise
```

4. **Initialiser la base de données**
```bash
python -c "from app import db; db.create_all()"
```

5. **Lancer l'application**
```bash
gunicorn --bind 0.0.0.0:5000 main:app
```

## Déploiement Production

### Sur Replit
L'application est optimisée pour Replit avec configuration automatique :
- Base de données PostgreSQL automatique
- Variables d'environnement via Secrets
- Déploiement en un clic

### Sur PythonAnywhere ou Heroku
1. Configurer les variables d'environnement
2. Adapter le chemin des fichiers statiques
3. Configurer le serveur WSGI (gunicorn)
4. Activer HTTPS pour la production

## Structure du Projet

```
gec-mines/
├── app.py              # Configuration Flask et DB
├── main.py             # Point d'entrée
├── models.py           # Modèles de données
├── views.py            # Routes et logique métier
├── utils.py            # Fonctions utilitaires
├── security_utils.py   # Sécurité et chiffrement
├── performance_utils.py # Optimisation
├── templates/          # Templates HTML
│   ├── new_base.html   # Template de base
│   ├── dashboard.html  # Tableau de bord
│   ├── register_mail.html # Enregistrement
│   └── view_mail.html  # Consultation
├── static/             # Assets statiques
├── uploads/            # Fichiers uploadés
└── exports/            # PDF générés
```

## Utilisation

### Premier Démarrage
1. Connexion avec les identifiants par défaut :
   - Email : `admin@gecmines.cd`
   - Mot de passe : `Admin@2025`
2. **Important** : Changer immédiatement le mot de passe
3. Configurer les paramètres système
4. Créer les départements et utilisateurs

### Workflow Courrier

#### Courrier Entrant
1. Cliquer sur "Nouveau Courrier"
2. Sélectionner "Entrant"
3. Remplir :
   - Expéditeur
   - Objet
   - Date de rédaction (optionnel)
   - SG en copie (Oui/Non)
   - Pièce jointe (obligatoire)
4. Soumettre pour génération du numéro d'accusé

#### Courrier Sortant
1. Cliquer sur "Nouveau Courrier"
2. Sélectionner "Sortant"
3. Remplir :
   - Destinataire
   - Objet
   - Date d'émission (obligatoire)
   - Type de courrier sortant
   - Autres informations
   - Pièce jointe (obligatoire)
4. Soumettre pour enregistrement

### Recherche et Filtres
- **Recherche textuelle** : Indexe tous les champs
- **Filtres disponibles** :
  - Type (Entrant/Sortant)
  - Statut
  - Dates (enregistrement et rédaction)
  - SG en copie
  - Type de courrier sortant

## Sécurité

### Mesures Implémentées
- ✅ Chiffrement AES-256-CBC pour données sensibles
- ✅ Hachage bcrypt avec salt personnalisé
- ✅ Protection CSRF sur tous les formulaires
- ✅ Headers de sécurité HTTP
- ✅ Validation et sanitisation des entrées
- ✅ Protection contre les injections SQL
- ✅ Blocage IP après tentatives échouées
- ✅ Audit trail complet

### Recommandations Production
1. Utiliser HTTPS obligatoirement
2. Configurer un firewall applicatif (WAF)
3. Sauvegardes régulières automatisées
4. Monitoring des logs de sécurité
5. Mise à jour régulière des dépendances

## Maintenance

### Sauvegarde
```bash
python -c "from utils import create_backup; create_backup()"
```

### Restauration
```bash
python -c "from utils import restore_backup; restore_backup('path/to/backup.zip')"
```

### Nettoyage
- Les fichiers temporaires sont automatiquement supprimés
- La corbeille peut être vidée depuis l'interface admin

## Support et Contact

Pour toute question ou assistance :
- Documentation complète dans `/docs`
- Logs d'activité dans la base de données
- Monitoring via le tableau de bord admin

## Licence

© 2025 GEC Mines - Secrétariat Général des Mines
Tous droits réservés.

## Changelog

### Version 1.0.0 (Août 2025)
- ✅ Système complet de gestion du courrier
- ✅ Sécurité renforcée avec chiffrement
- ✅ Gestion des pièces jointes obligatoires
- ✅ Recherche textuelle avancée
- ✅ Filtre SG en copie
- ✅ Export PDF optimisé
- ✅ Compatibilité déploiement externe
- ✅ Documentation complète