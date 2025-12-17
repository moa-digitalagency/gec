# Fonctionnalités et Routes - GEC

## Vue d'Ensemble des Fonctionnalités

Le GEC offre un ensemble complet de fonctionnalités pour la gestion du courrier administratif.

---

## Modules Fonctionnels

### 1. Authentification et Utilisateurs

| Fonctionnalité | Route | Méthode | Accès |
|----------------|-------|---------|-------|
| Connexion | /login | GET, POST | Public |
| Déconnexion | /logout | GET | Authentifié |
| Profil utilisateur | /profile | GET | Authentifié |
| Modifier profil | /edit_profile | GET, POST | Authentifié |
| Gestion utilisateurs | /manage_users | GET | Super Admin |
| Ajouter utilisateur | /add_user | GET, POST | Super Admin |
| Modifier utilisateur | /edit_user/<id> | GET, POST | Super Admin |

### 2. Tableau de Bord

| Fonctionnalité | Route | Description |
|----------------|-------|-------------|
| Dashboard | /dashboard | Statistiques, courriers récents, activités |

### 3. Gestion des Courriers

| Fonctionnalité | Route | Méthode | Accès |
|----------------|-------|---------|-------|
| Enregistrer courrier | /register_mail | GET, POST | Authentifié |
| Voir courrier | /view_mail/<id> | GET | Selon permissions |
| Modifier courrier | /edit_courrier/<id> | GET, POST | Selon permissions |
| Supprimer courrier | /delete_courrier/<id> | POST | Selon permissions |
| Télécharger pièce jointe | /download_attachment/<id> | GET | Selon permissions |
| Historique modifications | /courrier_modifications/<id> | GET | Selon permissions |

### 4. Recherche

| Fonctionnalité | Route | Description |
|----------------|-------|-------------|
| Recherche | /search | Recherche avancée avec filtres |
| Suggestions | /search_suggestions | Auto-complétion AJAX |

### 5. Transmission

| Fonctionnalité | Route | Description |
|----------------|-------|-------------|
| Transmettre courrier | /forward_mail/<id> | POST |
| Marquer comme lu | /mark_forward_read/<id> | POST |

### 6. Notifications

| Fonctionnalité | Route | Description |
|----------------|-------|-------------|
| Liste notifications | /notifications | GET |
| Marquer lue | /mark_notification_read/<id> | POST |
| Marquer toutes lues | /mark_all_notifications_read | POST |

### 7. Corbeille

| Fonctionnalité | Route | Description |
|----------------|-------|-------------|
| Voir corbeille | /trash | GET |
| Restaurer | /restore_courrier/<id> | POST |
| Supprimer définitivement | /permanent_delete/<id> | POST (Super Admin) |

### 8. Administration

#### Départements

| Route | Description |
|-------|-------------|
| /manage_departments | Liste des départements |
| /add_department | Ajouter un département |
| /edit_department/<id> | Modifier un département |
| /delete_department/<id> | Supprimer un département |

#### Rôles et Permissions

| Route | Description |
|-------|-------------|
| /manage_roles | Liste des rôles |
| /add_role | Ajouter un rôle |
| /edit_role/<id> | Modifier un rôle |
| /delete_role/<id> | Supprimer un rôle |

#### Statuts

| Route | Description |
|-------|-------------|
| /manage_statuses | Liste des statuts |
| /add_status | Ajouter un statut |
| /edit_status/<id> | Modifier un statut |
| /delete_status/<id> | Supprimer un statut |

#### Types de Courrier Sortant

| Route | Description |
|-------|-------------|
| /manage_outgoing_types | Liste des types |
| /add_outgoing_type | Ajouter un type |
| /edit_outgoing_type/<id> | Modifier un type |
| /delete_outgoing_type/<id> | Supprimer un type |

#### Templates Email

| Route | Description |
|-------|-------------|
| /manage_email_templates | Liste des templates |
| /add_email_template | Ajouter un template |
| /edit_email_template/<id> | Modifier un template |
| /delete_email_template/<id> | Supprimer un template |

### 9. Paramètres Système

| Route | Description |
|-------|-------------|
| /settings | Paramètres généraux |
| /security_settings | Paramètres de sécurité |
| /test_smtp_config | Test configuration email |

### 10. Sauvegardes

| Route | Description |
|-------|-------------|
| /manage_backups | Gestion des sauvegardes |
| /create_backup | Créer une sauvegarde |
| /restore_backup | Restaurer une sauvegarde |
| /download_backup/<filename> | Télécharger une sauvegarde |
| /delete_backup/<filename> | Supprimer une sauvegarde |

### 11. Export/Import

| Route | Description |
|-------|-------------|
| /export_courriers | Exporter des courriers (ZIP) |
| /import_courriers | Importer des courriers (ZIP) |

### 12. Journaux

| Route | Description |
|-------|-------------|
| /logs | Journal d'activité |
| /security_logs | Journal de sécurité |

### 13. Analytiques

| Route | Description |
|-------|-------------|
| /analytics | Tableau de bord analytique |

### 14. Langues

| Route | Description |
|-------|-------------|
| /manage_languages | Gestion des langues |
| /set_language/<code> | Changer de langue |
| /download_language/<code> | Télécharger fichier langue |
| /upload_language | Uploader fichier langue |

### 15. Liste des Expéditeurs

| Route | Description |
|-------|-------------|
| /senders_list | Liste des expéditeurs avec statistiques |

---

## Système de Permissions

### Permissions Disponibles

```
# Gestion système
manage_users              # Gérer les utilisateurs
manage_roles              # Gérer les rôles
manage_departments        # Gérer les départements
manage_statuses           # Gérer les statuts
manage_system_settings    # Paramètres système
manage_backups            # Gérer les sauvegardes
manage_email_templates    # Gérer templates email

# Courriers - Lecture
read_all_mail             # Lire tous les courriers
read_department_mail      # Lire courriers du département
read_own_mail             # Lire ses propres courriers

# Courriers - Modification
edit_all_mail             # Modifier tous les courriers
edit_department_mail      # Modifier courriers département
edit_own_mail             # Modifier ses propres courriers
register_mail             # Enregistrer de nouveaux courriers

# Courriers - Suppression
view_trash                # Voir la corbeille
restore_trash             # Restaurer de la corbeille
permanent_delete          # Suppression définitive

# Transmission
forward_mail              # Transmettre des courriers
receive_new_mail_notifications  # Recevoir notifications

# Export
export_courriers          # Exporter des courriers
import_courriers          # Importer des courriers
```

### Matrice des Rôles

| Permission | Super Admin | Admin | Utilisateur |
|------------|-------------|-------|-------------|
| manage_users | X | | |
| manage_roles | X | | |
| manage_departments | X | X | |
| manage_statuses | X | X | |
| read_all_mail | X | | |
| read_department_mail | X | X | |
| read_own_mail | X | X | X |
| edit_all_mail | X | | |
| edit_department_mail | X | X | |
| edit_own_mail | X | X | X |
| register_mail | X | X | X |
| view_trash | X | X | |
| restore_trash | X | | |
| permanent_delete | X | | |
| forward_mail | X | X | X |
| export_courriers | X | | |
| import_courriers | X | | |

---

## Modèles de Données Détaillés

### User

```python
class User:
    id: int                    # Identifiant unique
    username: str              # Nom d'utilisateur (unique)
    email: str                 # Email (unique)
    nom_complet: str           # Nom affiché
    password_hash: str         # Hash du mot de passe
    role: str                  # super_admin, admin, user
    departement_id: int        # FK vers Departement
    langue: str                # fr, en
    photo_profile: str         # Chemin vers la photo
    actif: bool                # Compte actif
    matricule: str             # Numéro d'employé
    fonction: str              # Poste occupé
    date_creation: datetime    # Date de création
```

### Courrier

```python
class Courrier:
    id: int                           # Identifiant unique
    numero_accuse_reception: str      # Numéro AR (unique)
    numero_reference: str             # Référence externe
    objet: str                        # Objet du courrier
    type_courrier: str                # ENTRANT, SORTANT
    type_courrier_sortant_id: int     # FK TypeCourrierSortant
    expediteur: str                   # Pour entrant
    destinataire: str                 # Pour sortant
    date_redaction: date              # Date sur le document
    date_enregistrement: datetime     # Date d'enregistrement
    statut: str                       # Statut actuel
    fichier_nom: str                  # Nom du fichier
    fichier_chemin: str               # Chemin du fichier
    fichier_type: str                 # Type MIME
    fichier_encrypted: bool           # Fichier chiffré
    fichier_checksum: str             # SHA-256
    secretaire_general_copie: bool    # SG en copie (entrant)
    autres_informations: str          # Notes
    is_deleted: bool                  # Soft delete
    deleted_at: datetime              # Date suppression
    utilisateur_id: int               # FK User (créateur)
```

### Departement

```python
class Departement:
    id: int                    # Identifiant unique
    nom: str                   # Nom (unique)
    code: str                  # Code court (unique)
    description: str           # Description
    chef_departement_id: int   # FK User (responsable)
    actif: bool                # Département actif
    date_creation: datetime    # Date de création
```

### CourrierForward

```python
class CourrierForward:
    id: int                          # Identifiant unique
    courrier_id: int                 # FK Courrier
    from_department_id: int          # FK Departement (source)
    to_department_id: int            # FK Departement (destination)
    forwarded_by_id: int             # FK User (expéditeur)
    forwarded_to_id: int             # FK User (destinataire)
    forward_date: datetime           # Date transmission
    comments: str                    # Commentaires
    attached_file: str               # Fichier joint
    attached_file_original_name: str # Nom original
    attached_file_size: int          # Taille fichier
    is_read: bool                    # Lu par destinataire
    read_date: datetime              # Date de lecture
```

### ParametresSysteme

```python
class ParametresSysteme:
    id: int                            # Identifiant unique
    nom_logiciel: str                  # Nom affiché
    logo_path: str                     # Chemin logo
    format_numero_accuse: str          # Format numérotation
    appellation_departement: str       # Label départements
    titre_responsable_structure: str   # Titre du responsable
    email_provider: str                # sendgrid, smtp
    smtp_server: str                   # Serveur SMTP
    smtp_port: int                     # Port SMTP
    smtp_username: str                 # Email expéditeur
    smtp_password: str                 # Mot de passe (chiffré)
    smtp_use_tls: bool                 # Utiliser TLS
    sendgrid_api_key: str              # Clé API (chiffrée)
    notify_superadmin_new_mail: bool   # Notifier super admin
```

---

## Format des Numéros d'Accusé

### Variables Disponibles

| Variable | Description | Exemple |
|----------|-------------|---------|
| {year} | Année (4 chiffres) | 2025 |
| {month} | Mois (2 chiffres) | 01 |
| {day} | Jour (2 chiffres) | 15 |
| {counter} | Compteur simple | 1, 2, 3... |
| {counter:05d} | Compteur formaté | 00001, 00002... |
| {random:4} | Nombre aléatoire | 1234 |

### Exemples de Format

| Format | Résultat |
|--------|----------|
| GEC-{year}-{counter:05d} | GEC-2025-00001 |
| {year}/{month}/{counter:04d} | 2025/01/0001 |
| CR-{year}-{random:6} | CR-2025-123456 |

---

## Codes de Statut HTTP

| Code | Signification |
|------|---------------|
| 200 | Succès |
| 302 | Redirection |
| 400 | Requête invalide |
| 403 | Accès interdit |
| 404 | Non trouvé |
| 429 | Trop de requêtes (rate limit) |
| 500 | Erreur serveur |

---

## Fichiers Statiques

### Structure

```
static/
├── css/
│   └── style.css           # Styles personnalisés
├── js/
│   └── app.js              # JavaScript applicatif
├── images/
│   └── default-profile.svg # Avatar par défaut
├── vendor/
│   ├── bootstrap/          # Bootstrap 5
│   ├── chartjs/            # Chart.js
│   ├── cropperjs/          # Cropper.js
│   ├── datatables/         # DataTables
│   ├── fontawesome/        # Font Awesome
│   ├── jquery/             # jQuery
│   └── tailwind/           # Tailwind CSS
└── favicon.svg             # Icône du site
```

### Accès

Les fichiers statiques sont servis depuis `/static/...`

Exemple : `/static/css/style.css`

---

## Templates

### Template de Base

`new_base.html` contient :
- Structure HTML5
- Inclusion CSS/JS
- Navigation
- Messages flash
- Pied de page

### Héritage

```jinja2
{% extends 'new_base.html' %}

{% block title %}Titre de la page{% endblock %}

{% block content %}
<!-- Contenu spécifique -->
{% endblock %}
```

### Fonctions Disponibles

| Fonction | Description |
|----------|-------------|
| t('clé') | Traduction |
| url_for('route') | Génération URL |
| format_date(date) | Formatage date |
| get_current_language() | Langue actuelle |
| get_appellation_entites() | Label départements |
| get_titre_responsable() | Titre responsable |
