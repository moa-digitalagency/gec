[ 🇫🇷 Français ](GEC_features_full_list.md) | [ 🇬🇧 English ](GEC_features_full_list_en.md)

# GEC - Liste Complète des Fonctionnalités (Bible)

> **CONFIDENTIEL ET PROPRIÉTAIRE.**
> Ce document détaille l'intégralité des fonctionnalités du système GEC (Gestion Électronique du Courrier).
> Propriété de MOA Digital Agency. Reproduction interdite.

---

## 1. Sécurité & Authentification (Module `Security`)

### 1.1 Authentification
*   **Login Sécurisé :**
    *   Hachage des mots de passe avec **Bcrypt** (12 rounds) + Sel applicatif (`GEC_PASSWORD_SALT`).
    *   Protection contre les attaques par force brute (Blocage IP temporaire après 5 échecs).
    *   Gestion des tentatives de connexion (`login_attempts`).
*   **Gestion de Session :**
    *   Tokens de session sécurisés (`generate_secure_session_token`).
    *   Validation CSRF stricte sur tous les formulaires (`generate_csrf_token`).
    *   Expiration automatique des sessions (Timeout configurable).

### 1.2 Contrôle d'Accès (RBAC)
*   **Système de Rôles Hiérarchiques :**
    *   **Super Admin :** Accès total, configuration système, maintenance.
    *   **Admin :** Gestion des utilisateurs, configuration limitée, supervision.
    *   **User :** Enregistrement, consultation et traitement selon périmètre.
    *   **Rôles Personnalisés :** Création de rôles avec code couleur, icône et description spécifique.
*   **Permissions Granulaires :**
    *   Système de permissions atomiques (ex: `manage_users`, `register_mail`, `view_trash`).
    *   Vérification dynamique via décorateur `@check_permission`.
*   **Logique de Visibilité (`MailAccessFilter`) :**
    *   `read_all_mail` : Visibilité totale.
    *   `read_department_mail` : Visibilité restreinte au département de l'utilisateur + courriers transmis.
    *   `read_own_mail` : Visibilité restreinte aux courriers assignés/créés + courriers transmis.

### 1.3 Cryptographie & Protection des Données
*   **Chiffrement Base de Données (AES-256) :**
    *   Utilisation de la bibliothèque `cryptography` (Fernet).
    *   **Champs Chiffrés (Utilisateur) :** Email, Nom complet, Matricule, Fonction, Hash MDP.
    *   **Champs Chiffrés (Courrier) :** Objet, Expéditeur, Destinataire, Numéro Référence.
    *   **Champs Chiffrés (Système) :** Mots de passe SMTP, Clés API.
*   **Intégrité des Fichiers :**
    *   Calcul SHA-256 (Checksum) à l'upload pour garantir l'intégrité.
    *   Vérification à la demande via `verify_file_integrity`.

### 1.4 Sécurité Applicative
*   **Rate Limiting :** Protection des endpoints sensibles (Login, Upload) via `@rate_limit`.
*   **Sanitization :** Nettoyage automatique des entrées (`sanitize_input`) pour prévenir XSS et SQL Injection.
*   **Audit Logging :** Traçabilité immuable dans `LogActivite` (Qui, Quoi, Quand, IP).
*   **Headers HTTP Sécurisés :** HSTS, X-Frame-Options, CSP, X-XSS-Protection.

---

## 2. Gestion des Courriers (Module `Core`)

### 2.1 Enregistrement
*   **Typologie :** Distinction stricte `ENTRANT` vs `SORTANT`.
*   **Validation des Données :**
    *   Contrôle de cohérence (Expéditeur/Destinataire requis selon type).
    *   Validation format date et champs obligatoires.
*   **Génération de Numéro d'Accusé :**
    *   Format configurable (ex: `GEC-{year}-{counter:05d}`).
    *   Support de variables dynamiques et séquenceur atomique.
*   **Gestion des Pièces Jointes :**
    *   Upload obligatoire à l'enregistrement.
    *   Validation stricte des types MIME (PDF, Images) et taille (Max 16MB).
    *   Renommage sécurisé des fichiers pour éviter les collisions et exécutions malveillantes.

### 2.2 Cycle de Vie & Statuts
*   **Workflow de Statuts :**
    *   États standard : `RECU`, `EN_COURS`, `TRAITE`, `ARCHIVE`, `URGENT`.
    *   Transition de statut logguée et notifiée.
*   **Gestion de la Corbeille (Soft Delete) :**
    *   Suppression logique avec possibilité de restauration.
    *   Purge définitive réservée aux administrateurs.

### 2.3 Recherche Avancée
*   **Moteur de Recherche :**
    *   Indexation sur : N° Accusé, Référence, Objet, Tiers.
    *   Recherche insensible à la casse et aux accents.
*   **Filtrage Multicritères :**
    *   Par Période (Enregistrement / Rédaction).
    *   Par Statut / Type / Priorité.
    *   Par Département / Utilisateur.
    *   Par présence de Copie SG.

---

## 3. Collaboration & Workflow

### 3.1 Transmission (Forwarding)
*   **Mécanisme de Transmission :**
    *   Transfert de responsabilité ou demande d'avis entre utilisateurs.
    *   Ajout de message contextuel et pièces jointes additionnelles.
*   **Héritage de Droits :** Le destinataire hérite automatiquement des droits de lecture sur le courrier transmis.
*   **Historique :** Chaîne de transmission visible (Timeline).

### 3.2 Annotations & Commentaires
*   **Système d'Annotation :**
    *   Ajout de notes (Instructions, Remarques) sur le dossier.
    *   Horodatage et identification de l'auteur.
*   **Notifications :** Alertes automatiques aux parties concernées lors d'un ajout.

### 3.3 Notifications Multicanales
*   **In-App :** Centre de notification temps réel (Badge, Liste déroulante).
*   **Email :** Notifications asynchrones via SMTP ou SendGrid (Template HTML responsive).

---

## 4. Administration Système

### 4.1 Configuration Globale
*   **Identité Visuelle :** Personnalisation des logos, noms, slogans.
*   **Paramètres PDF :** En-têtes et pieds de page des exports officiels.
*   **Configuration Email :** Gestionnaire de provider (SMTP/API) avec test de connexion.

### 4.2 Gestion Organisationnelle
*   **Gestion Utilisateurs :** CRUD complet, Réinitialisation MDP, Avatar.
*   **Gestion Départements :** Structure hiérarchique de l'organisation.
*   **Types de Courriers :** Configuration des types de documents (Lettre, Note, Arrêté...).

### 4.3 Internationalisation (i18n)
*   **Moteur de Langue :**
    *   Support JSON multi-fichiers (`fr.json`, `en.json`).
    *   Détection de langue intelligente (Session > Navigateur).
*   **Éditeur de Traduction :** Interface graphique pour modifier les libellés sans toucher au code.

---

## 5. Reporting & Décisionnel

### 5.1 Tableau de Bord (Dashboard)
*   **KPIs Stratégiques :** Volumétrie, Taux de traitement, Charge par département.
*   **Visualisation de Données :** Graphiques interactifs (Bar, Pie, Line) via Chart.js.
*   **Système de Cache :** Mise en cache des statistiques lourdes pour performance optimale.

### 5.2 Exports & Rapports
*   **Moteur PDF (ReportLab) :**
    *   **Fiche Courrier :** Document officiel de synthèse d'un courrier.
    *   **Rapports de Liste :** Export tabulaire filtré.
    *   **Logs d'Audit :** Rapport de sécurité pour conformité.

---

## 6. Maintenance & Fiabilité

### 6.1 Sauvegarde & Restauration
*   **Backup Full-Stack :**
    *   Dump SQL + Fichiers Uploads + Configuration + Env.
    *   Compression ZIP avec Manifeste JSON.
*   **Restauration Granulaire :** Capacité de restaurer tout ou partie du système.

### 6.2 Maintenance Automatisée
*   **Nettoyage Base de Données :** Scripts de purge des logs anciens et données temporaires.
*   **Migration de Schéma :** Gestion automatique des évolutions de base de données au démarrage.
