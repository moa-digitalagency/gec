# GEC - Bible des Fonctionnalités

Ce document recense de manière exhaustive toutes les fonctionnalités techniques et métier implémentées dans le système GEC (Gestion Électronique du Courrier). Il sert de référence absolue pour le développement, la maintenance et l'audit.

---

## 1. Authentification & Sécurité (Module `Auth`)

### 1.1 Authentification Utilisateur
*   **Système de Login :**
    *   Authentification par `username` et `password`.
    *   Vérification des identifiants via `Flask-Login`.
    *   Hachage des mots de passe avec `bcrypt` (via `werkzeug.security`) et sels personnalisés (`GEC_PASSWORD_SALT`).
    *   **Protection Brute-Force :**
        *   Blocage IP automatique après 8 tentatives échouées (`MAX_LOGIN_ATTEMPTS`).
        *   Durée de blocage : 15 minutes (`LOGIN_LOCKOUT_DURATION`).
        *   Stockage des tentatives échouées en mémoire (`_failed_login_attempts`).
    *   **Gestion de Session :**
        *   Tokens de session sécurisés (`generate_secure_session_token`).
        *   Validation CSRF sur les formulaires (`generate_csrf_token`).
        *   Expiration automatique des sessions.

### 1.2 Contrôle d'Accès (RBAC)
*   **Système de Rôles :**
    *   Modèle de base de données `Role` et `RolePermission`.
    *   **Rôles par défaut :**
        *   `super_admin` : Accès total, non modifiable.
        *   `admin` : Gestion utilisateurs, config limitée.
        *   `user` : Enregistrement et consultation simple.
    *   **Rôles Personnalisés :** Création de rôles avec couleur, icône et description.
*   **Permissions Granulaires :**
    *   Liste définie de permissions (ex: `manage_users`, `register_mail`, `read_department_mail`, `view_trash`, etc.).
    *   Vérification via décorateur `@check_permission` ou méthode `user.has_permission()`.
    *   **Logique d'accès Courrier (`apply_mail_access_filter`) :**
        *   `read_all_mail` : Voit tout.
        *   `read_department_mail` : Voit courriers de son département + ceux transmis à lui.
        *   `read_own_mail` : Voit ses propres courriers + ceux transmis à lui.
        *   **Transmission :** Un courrier transmis (`CourrierForward`) devient visible par le destinataire quelle que soit sa permission de base.

### 1.3 Cryptographie & Données Sensibles
*   **Chiffrement en Base de Données (AES-256) :**
    *   Utilisation de `encryption_utils` et `cryptography`.
    *   **Champs chiffrés (Modèle `User`) :** `email`, `nom_complet`, `matricule`, `fonction`, `password_hash` (double couche).
    *   **Champs chiffrés (Modèle `Courrier`) :** `objet`, `expediteur`, `destinataire`, `numero_reference`.
    *   **Champs chiffrés (Modèle `ParametresSysteme`) :** `smtp_password`, `copyright_crypte`.
    *   **Clé Maître :** Utilisation de `GEC_MASTER_KEY` (variable d'env) pour dériver les clés de chiffrement.
*   **Intégrité des Fichiers :**
    *   Calcul et stockage du checksum SHA-256 pour chaque fichier joint (`fichier_checksum`).
    *   Vérification d'intégrité à la demande (`verify_file_integrity`).

### 1.4 Sécurité Applicative
*   **Rate Limiting :** Décorateur `@rate_limit` sur les routes sensibles (Login, Upload).
*   **Sanitization :**
    *   Nettoyage des entrées (`sanitize_input`) contre XSS et SQL Injection.
    *   Détection de patterns d'attaque (SQLi, XSS) avec logging de sécurité.
*   **Audit Logging :**
    *   Traçabilité complète dans la table `LogActivite` (Qui, Quoi, Quand, IP).
    *   Logs spécifiques de sécurité (`security_logs`) pour les événements critiques (Login failed, IP Block, etc.).
*   **Headers de Sécurité :** Injection automatique (HSTS, X-Frame-Options, CSP, X-XSS-Protection).

---

## 2. Gestion des Courriers (Module `Core`)

### 2.1 Enregistrement
*   **Types de Courriers :** `ENTRANT` ou `SORTANT`.
*   **Validation des Champs :**
    *   `ENTRANT` : Expéditeur obligatoire, Objet obligatoire, Copie SG (Oui/Non).
    *   `SORTANT` : Destinataire obligatoire, Objet obligatoire, Type de sortie obligatoire (Note, Lettre, etc.), Date de rédaction obligatoire.
*   **Numéro d'Accusé de Réception :**
    *   **Génération Automatique :** Format configurable (ex: `GEC-{year}-{counter:05d}`).
    *   **Variables dynamiques :** `{year}`, `{month}`, `{day}`, `{counter}`, `{random}`.
    *   **Mode Manuel :** Possibilité de saisir un numéro existant (avec vérification d'unicité).
*   **Gestion des Pièces Jointes :**
    *   Upload obligatoire à l'enregistrement.
    *   Validation extension (`pdf`, `png`, `jpg`, `jpeg`, `tiff`).
    *   Validation taille (Max 16MB).
    *   Renommage sécurisé (`secure_filename`) avec timestamp pour éviter les collisions.
    *   Stockage dans `uploads/` (ou sous-dossiers).

### 2.2 Cycle de Vie & Statuts
*   **Statuts Configurables :** `RECU`, `EN_COURS`, `TRAITE`, `ARCHIVE`, `URGENT`.
*   **Gestion des Statuts :**
    *   CRUD complet des statuts (Nom, Couleur, Ordre, Description).
    *   Changement de statut via interface dédiée avec log automatique.
*   **Soft Delete (Corbeille) :**
    *   Suppression logique (`is_deleted=True`).
    *   Restauration possible depuis la corbeille.
    *   Suppression définitive (Purge) réservée aux Super Admins.

### 2.3 Recherche & Filtres
*   **Moteur de Recherche :**
    *   Recherche textuelle sur : N° Accusé, Référence, Objet, Expéditeur, Destinataire.
    *   Optimisation des requêtes (`optimize_search_query`).
*   **Filtres Avancés :**
    *   Par Date d'enregistrement (Début/Fin).
    *   Par Date de rédaction (Début/Fin).
    *   Par Statut.
    *   Par Type (Entrant/Sortant).
    *   Par Type Sortant Spécifique (Note, Lettre...).
    *   Par présence SG en copie.
*   **Autocomplétion :** Endpoint API `/api/search_suggestions`.

---

## 3. Workflow & Collaboration

### 3.1 Transmission (Forwarding)
*   **Mécanisme :**
    *   Transmission d'un courrier d'un utilisateur A vers un utilisateur B.
    *   Modèle `CourrierForward`.
    *   Ajout optionnel d'un message et d'une pièce jointe spécifique à la transmission (stockée dans `uploads/forwards/`).
*   **Visibilité :** Donne automatiquement accès au courrier à l'utilisateur B (contournement des restrictions de département).
*   **Traçabilité :** Historique complet des transmissions affiché dans les détails du courrier et sur le PDF.

### 3.2 Commentaires & Annotations
*   **Types :** Commentaire, Annotation, Instruction.
*   **Fonctionnement :**
    *   Ajout sur un courrier spécifique.
    *   Modèle `CourrierComment`.
    *   Affichage chronologique.
*   **Notifications :** Notifie le créateur du courrier et le dernier destinataire lors d'un ajout.

### 3.3 Notifications
*   **Canaux :**
    *   **In-App :** Table `Notification`, indicateur visuel (badge), page dédiée.
    *   **Email :** Envoi via SMTP ou Resend.
*   **Événements déclencheurs :**
    *   Nouveau courrier enregistré (pour Admins/Super Admins).
    *   Courrier transmis (pour le destinataire).
    *   Nouveau commentaire/annotation.
*   **Gestion :** Marquage "Lu/Non lu", lien direct vers le courrier concerné.

---

## 4. Administration Système

### 4.1 Configuration Générale
*   **Paramètres (`ParametresSysteme`) :**
    *   Identité : Nom logiciel, Logos (App & PDF), Slogan/Footer.
    *   Organisation : Adresse, Téléphone, Email contact.
    *   PDF : Titre, Sous-titre, Pays, Copyright.
    *   Email : Choix Provider (SMTP/Resend), Clés API, Identifiants SMTP (mot de passe chiffré).
    *   Nomenclature : Format Accusé de réception, Appellation "Département", Titre Responsable.

### 4.2 Gestion Organisationnelle
*   **Utilisateurs :** Création, Édition, Désactivation, Reset Password, Photo de profil.
*   **Départements :** Création, Code, Chef de département.
*   **Types de Courrier Sortant :** Liste configurable (Note circulaire, Mémorandum...) avec ordre d'affichage.

### 4.3 Internationalisation (i18n)
*   **Support Multi-langues :**
    *   Fichiers JSON dans `lang/` (ex: `fr.json`, `en.json`).
    *   Détection automatique : Session > Cookie > Préférence User > Navigateur > Défaut (FR).
    *   **Interface de Gestion :**
        *   Activation/Désactivation des langues.
        *   Upload de nouveaux fichiers JSON.
        *   Téléchargement pour édition.
        *   Protection du Français (langue de référence).

---

## 5. Rapports & Analytics

### 5.1 Tableau de Bord (Dashboard)
*   **KPIs Temps Réel :** Total courriers, Aujourd'hui, Semaine, Utilisateurs.
*   **Activité Récente :** Liste des derniers courriers (filtrée par permissions).
*   **Cache :** Utilisation de `performance_utils` pour mettre en cache les stats lourdes.

### 5.2 Page Analytics (`/analytics`)
*   **Graphiques (Chart.js) :**
    *   Volume quotidien (Bar chart).
    *   Répartition par statut (Pie chart).
    *   Évolution mensuelle.
    *   Top départements / Utilisateurs.
    *   Analyse par jour de semaine / Heure.
*   **Stats Détaillées :** Top Expéditeurs, Top Destinataires, Temps moyen de traitement.

### 5.3 Exports PDF
*   **Moteur :** `ReportLab` via `utils.py`.
*   **Types d'exports :**
    *   **Fiche Courrier Individuelle :** Détails complets, métadonnées, historique transmissions, commentaires. Mise en page soignée avec logo et en-tête officiel.
    *   **Liste Filtrée :** Tableau récapitulatif des résultats de recherche/filtre.
    *   **Logs d'Activité :** Export audit complet.
    *   **Rapport Analytics :** Export des graphiques et tableaux statistiques.

---

## 6. Maintenance & Sauvegardes

### 6.1 Système de Sauvegarde (`utils.py`)
*   **Sauvegarde Complète (Full System) :**
    *   Archive ZIP contenant :
        *   Dump SQL complet (`pg_dump` pour PostgreSQL ou copie SQLite).
        *   Dossier `uploads/` (pièces jointes).
        *   Dossier `forward_attachments/`.
        *   Dossiers configuration (`lang/`, `templates/`, `static/`).
        *   Fichiers critiques (`.env` documenté, `requirements.txt`).
        *   Manifeste JSON (`backup_manifest.json`) avec métadonnées.
*   **Sauvegarde Pré-Mise à jour :** Création automatique d'un point de restauration avant update.

### 6.2 Restauration
*   **Restauration Intelligente :**
    *   Vérification d'intégrité du ZIP avant restauration.
    *   Restauration base de données (`psql` ou fichier).
    *   Restauration sélective des fichiers.
    *   Préservation des configurations critiques si nécessaire.

### 6.3 Mises à Jour
*   **Update Online :** `git pull` automatique via interface + redémarrage.
*   **Update Offline :** Upload d'un ZIP de mise à jour, extraction intelligente (hash comparison) et remplacement des fichiers modifiés.

### 6.4 Nettoyage
*   **Script `cleanup_database.py` :**
    *   Purge des données transactionnelles (Courriers, Logs, Notifs).
    *   Conservation des configurations (Users Admin, Départements, Paramètres).
    *   Transaction atomique (Rollback en cas d'erreur).
