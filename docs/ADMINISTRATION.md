# Guide d'Administration - GEC

## Introduction

Ce guide est destiné aux administrateurs système et super administrateurs du GEC. Il couvre la configuration, la maintenance et la gestion quotidienne de l'application.

---

## Gestion des Utilisateurs

### Créer un Utilisateur

1. Menu Administration → Gestion des utilisateurs
2. Cliquer sur "Ajouter un utilisateur"
3. Remplir les champs :
   - Nom d'utilisateur (unique, sans espaces)
   - Email (unique)
   - Nom complet
   - Mot de passe (respecter les critères de sécurité)
   - Rôle
   - Département
   - Matricule (optionnel)
   - Fonction (optionnel)
4. Enregistrer

### Modifier un Utilisateur

1. Liste des utilisateurs → Cliquer sur l'utilisateur
2. Modifier les informations nécessaires
3. Pour changer le mot de passe : cocher "Réinitialiser le mot de passe"
4. Enregistrer

### Désactiver un Utilisateur

La désactivation est préférable à la suppression pour conserver l'historique :

1. Modifier l'utilisateur
2. Décocher "Compte actif"
3. Enregistrer

L'utilisateur ne pourra plus se connecter mais ses actions restent traçables.

### Rôles Disponibles

| Rôle | Description |
|------|-------------|
| super_admin | Accès complet, toutes permissions |
| admin | Gestion département, courriers du département |
| user | Consultation et création de courriers personnels |

---

## Gestion des Départements

### Créer un Département

1. Menu Administration → Départements
2. Cliquer sur "Ajouter un département"
3. Remplir :
   - Nom (exemple : "Direction des Ressources Humaines")
   - Code (exemple : "DRH", 2-10 caractères)
   - Description
   - Chef de département (optionnel)
4. Enregistrer

### Personnaliser l'Appellation

Le terme "Départements" peut être personnalisé :

1. Paramètres → Paramètres généraux
2. Modifier "Appellation des entités"
3. Exemples : "Directions", "Services", "Divisions"
4. Enregistrer

---

## Gestion des Rôles et Permissions

### Créer un Rôle Personnalisé

1. Menu Administration → Rôles
2. Cliquer sur "Ajouter un rôle"
3. Définir le nom et la description
4. Sélectionner les permissions :
   - Lecture courriers (tous, département, personnels)
   - Modification courriers
   - Enregistrement courriers
   - Transmission
   - Gestion départements
   - etc.
5. Enregistrer

### Assigner un Rôle

1. Modifier l'utilisateur
2. Sélectionner le rôle dans la liste déroulante
3. Enregistrer

---

## Gestion des Statuts

### Statuts Par Défaut

| Code | Nom | Couleur |
|------|-----|---------|
| RECU | Reçu | Bleu |
| EN_COURS | En cours | Jaune |
| TRAITE | Traité | Vert |
| ARCHIVE | Archivé | Gris |
| URGENT | Urgent | Rouge |

### Ajouter un Statut

1. Menu Administration → Statuts
2. Cliquer sur "Ajouter un statut"
3. Remplir :
   - Code (majuscules, sans espaces)
   - Nom affiché
   - Couleur (classe CSS Tailwind)
   - Ordre d'affichage
4. Enregistrer

---

## Types de Courrier Sortant

### Types Par Défaut

- Note circulaire
- Note télégramme
- Lettre officielle
- Mémorandum
- Convocation
- Rapport
- Note de service
- Autre

### Ajouter un Type

1. Menu Administration → Types courrier sortant
2. Cliquer sur "Ajouter un type"
3. Remplir nom, description, ordre
4. Enregistrer

---

## Paramètres Système

### Paramètres Généraux

Accessibles via : Paramètres → Paramètres généraux

| Paramètre | Description |
|-----------|-------------|
| Nom du logiciel | Affiché dans l'en-tête |
| Logo | Image affichée (SVG recommandé) |
| Format numéro AR | Modèle de numérotation |
| Appellation entités | "Départements", "Services", etc. |
| Titre responsable | "Secrétaire Général", "Directeur", etc. |

### Format de Numérotation

Variables disponibles :
- `{year}` : Année (2025)
- `{month}` : Mois (01-12)
- `{day}` : Jour (01-31)
- `{counter:05d}` : Compteur sur 5 chiffres
- `{random:4}` : 4 chiffres aléatoires

Exemples :
- `GEC-{year}-{counter:05d}` → GEC-2025-00001
- `{year}/{month}/{counter:04d}` → 2025/01/0001

---

## Configuration Email

### Méthode 1 : SendGrid (Recommandé)

1. Créer un compte sur sendgrid.com
2. Générer une clé API (Settings → API Keys)
3. Dans GEC : Paramètres → Configuration Email
4. Sélectionner "SendGrid" comme fournisseur
5. Coller la clé API
6. Tester l'envoi

### Méthode 2 : SMTP Traditionnel

1. Paramètres → Configuration Email
2. Sélectionner "SMTP" comme fournisseur
3. Renseigner :
   - Serveur SMTP
   - Port (587 pour TLS, 465 pour SSL)
   - Email expéditeur
   - Mot de passe
   - Activer TLS (recommandé)
4. Tester l'envoi

### Templates Email

Personnaliser les emails envoyés :

1. Administration → Templates email
2. Types disponibles :
   - Notification nouveau courrier
   - Notification transmission
   - Test SMTP
3. Modifier le sujet et le contenu HTML
4. Variables disponibles : `{{nom_courrier}}`, `{{expediteur}}`, etc.

---

## Sauvegardes

### Créer une Sauvegarde

1. Administration → Gestion des sauvegardes
2. Cliquer sur "Créer une sauvegarde"
3. Options :
   - Sauvegarde complète (base de données + fichiers)
   - Sauvegarde de sécurité (avant mise à jour)
4. Télécharger le fichier ZIP

### Contenu d'une Sauvegarde

```
backup_YYYYMMDD_HHMMSS.zip
├── database_backup.sql       # Dump PostgreSQL
├── backup_manifest.json      # Métadonnées
├── environment_variables_documentation.json
├── uploads/                  # Fichiers uploadés
├── forward_attachments/      # Pièces jointes transmissions
├── lang/                     # Fichiers de langue
├── templates/                # Templates HTML
└── static/                   # Fichiers statiques
```

### Restaurer une Sauvegarde

1. Administration → Gestion des sauvegardes
2. Sélectionner la sauvegarde
3. Cliquer sur "Restaurer"
4. Confirmer l'opération

Attention : la restauration remplace les données actuelles.

### Planification

Les sauvegardes automatiques ne sont pas incluses par défaut. Pour les mettre en place :

1. Utiliser un cron job (Linux) ou Task Scheduler (Windows)
2. Appeler l'endpoint `/create_backup` via script

---

## Export/Import de Courriers

### Export

1. Administration → Gestion des sauvegardes
2. Section "Export de courriers"
3. Options :
   - Exporter tous les courriers
   - Sélectionner des IDs spécifiques
4. Le package ZIP contient les données déchiffrées

### Import

1. Télécharger le fichier ZIP d'export
2. Administration → Gestion des sauvegardes
3. Section "Import de courriers"
4. Sélectionner le fichier
5. Cocher "Ignorer les doublons" (recommandé)
6. Importer

Les données sont re-chiffrées avec la clé de l'instance.

---

## Sécurité

### Paramètres de Sécurité

Accessibles via : Paramètres → Sécurité

| Paramètre | Description |
|-----------|-------------|
| Tentatives max | Nombre de tentatives avant blocage |
| Durée blocage | Durée en minutes du blocage IP |
| Seuil activités suspectes | Nombre d'activités avant alerte |

### Liste Blanche IP

Ajouter des adresses IP qui ne seront jamais bloquées :

1. Paramètres → Sécurité
2. Ajouter une IP à la liste blanche
3. Utile pour les accès administratifs

### Blocage d'IP

Voir les IP bloquées et les débloquer manuellement :

1. Paramètres → Sécurité
2. Section "IP bloquées"
3. Débloquer si nécessaire

### Journaux de Sécurité

Consulter les événements de sécurité :

1. Administration → Journaux de sécurité
2. Filtrer par :
   - Type d'événement
   - Date
   - Utilisateur
   - Niveau de sévérité

---

## Langues

### Langues Disponibles

Par défaut : Français, Anglais

### Ajouter une Langue

1. Administration → Langues
2. Télécharger un fichier de langue existant (modèle)
3. Traduire les clés
4. Uploader le nouveau fichier (ex: `es.json` pour espagnol)

### Structure du Fichier de Langue

```json
{
  "common": {
    "save": "Enregistrer",
    "cancel": "Annuler",
    "delete": "Supprimer"
  },
  "dashboard": {
    "welcome": "Bienvenue",
    "total_courriers": "Total des courriers"
  }
}
```

---

## Maintenance

### Nettoyage de la Base de Données

Script disponible : `cleanup_database.py`

Opérations :
- Suppression des logs anciens
- Nettoyage des sessions expirées
- Optimisation des index

### Vérification de l'Intégrité

Au démarrage, l'application vérifie :
- Présence des tables
- Colonnes requises
- Contraintes de clés étrangères

### Mise à Jour

1. Créer une sauvegarde de sécurité
2. Arrêter l'application
3. Mettre à jour les fichiers
4. Redémarrer l'application
5. Les migrations s'appliquent automatiquement

---

## Dépannage Administratif

### Un utilisateur ne peut pas se connecter

Vérifier :
1. Compte actif (coché)
2. Mot de passe correct
3. IP non bloquée

Solution : réinitialiser le mot de passe ou débloquer l'IP.

### Les notifications email ne fonctionnent pas

Vérifier :
1. Configuration email complète
2. Clé API SendGrid valide
3. Email expéditeur vérifié (SendGrid)
4. Connexion internet

Tester avec le bouton "Tester la configuration".

### Courrier disparu

Vérifier :
1. Corbeille (si supprimé)
2. Permissions de l'utilisateur
3. Filtres de recherche actifs

### Performance dégradée

Actions :
1. Vider le cache de l'application
2. Vérifier la taille de la base de données
3. Optimiser les index PostgreSQL
4. Archiver les anciens courriers

---

## Bonnes Pratiques

### Sécurité

1. Changer les clés de chiffrement à l'installation
2. Utiliser des mots de passe forts pour les admins
3. Activer les notifications de sécurité
4. Surveiller les journaux régulièrement

### Maintenance

1. Sauvegardes quotidiennes
2. Test de restauration mensuel
3. Mise à jour des dépendances
4. Nettoyage des données obsolètes

### Organisation

1. Définir une nomenclature des départements
2. Former les utilisateurs au système
3. Documenter les processus internes
4. Désigner un administrateur principal et un suppléant
