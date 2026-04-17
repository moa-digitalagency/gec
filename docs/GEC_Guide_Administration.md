# Guide d'Administration - GEC

## Introduction

Ce guide est destiné aux administrateurs système et super administrateurs du GEC. Il couvre la configuration avancée, la maintenance critique et la gestion quotidienne de l'application.

> **Note :** Certaines fonctionnalités décrites ici nécessitent le rôle `super_admin`.

> **Accès :** L'application est strictement interne. L'URL racine (`/`) redirige automatiquement vers la page d'authentification (`/login`). Il n'y a pas de page d'accueil publique.

---

## 1. Gestion des Utilisateurs et Rôles

### Création et Édition
*   **Menu :** Administration → Gestion des utilisateurs.
*   **Champs critiques :**
    *   **Matricule :** Identifiant unique RH (chiffré en base).
    *   **Rôle :** Détermine les permissions (voir ci-dessous).
    *   **Département :** Essentiel pour le cloisonnement des données.
*   **Désactivation :** Préférez décocher "Actif" plutôt que de supprimer un compte, afin de préserver l'historique des logs.

### Rôles et Permissions (RBAC)
Le système utilise un contrôle d'accès basé sur les rôles. Vous pouvez créer des rôles personnalisés via le menu **Administration → Rôles**.

| Rôle | Description | Cas d'usage |
|------|-------------|-------------|
| **Super Admin** | Accès total, non modifiable. | DSI, Responsable Système. |
| **Admin** | Gestion locale (département), utilisateurs simples. | Chef de service, Secrétaire principal. |
| **User** | Enregistrement et traitement des courriers. | Agents administratifs. |

**Permissions configurables :**
*   `read_all_mail` : Voir tous les courriers (outrepasse les départements).
*   `register_mail` : Droit d'enregistrer du courrier.
*   `manage_system_settings` : Accès aux configurations techniques.

---

## 2. Configuration Organisationnelle

### Départements
*   **Menu :** Administration → Départements.
*   **Code :** Utilisez un trigramme unique (ex: `RH`, `FIN`, `IT`).
*   **Chef de Département :** Utilisateur référent (optionnel).

### Types de Courrier Sortant
*   **Menu :** Administration → Types courrier sortant.
*   **Usage :** Définit les options du menu déroulant lors de l'enregistrement d'un courrier sortant (ex: Note, Lettre, Arrêté).
*   **Ordre :** Définissez la priorité d'affichage.

### Statuts de Traitement
*   **Menu :** Administration → Statuts.
*   **Personnalisation :** Vous pouvez modifier les libellés et les couleurs (classes CSS Tailwind) pour adapter le workflow à votre organisation.

---

## 3. Paramètres Système

### Identité Visuelle et Nomenclature
Accessible via **Paramètres → Paramètres généraux**.
*   **Logo :** Upload d'image (PNG/JPG/SVG). Apparaît sur l'interface et les PDF.
*   **Format Accusé de Réception :**
    *   Syntaxe : `GEC-{year}-{counter:05d}`
    *   Variables : `{year}`, `{month}`, `{day}`, `{counter}`, `{random}`.
*   **Pied de page PDF :** Texte légal apparaissant sur tous les exports.

### Configuration Email
Le GEC supporte deux modes d'envoi pour les notifications :

1.  **Resend (Recommandé) :**
    *   Nécessite une clé API.
    *   Plus fiable pour la délivrabilité.
2.  **SMTP Standard :**
    *   Compatible avec Exchange, Gmail, Outlook.
    *   Supporte TLS/SSL.
    *   Le mot de passe est chiffré en base de données.

**Test :** Utilisez toujours le bouton "Tester la configuration" après un changement.

---

## 4. Sécurité Avancée

### Gestion des IPs
*   **Blocage Automatique :** Le système bloque une IP après 8 tentatives de connexion échouées (durée : 15 min).
*   **Liste Blanche (Whitelist) :** Ajoutez les IPs de vos bureaux pour éviter tout blocage accidentel.
*   **Déblocage Manuel :** Via **Paramètres → Sécurité → IP Bloquées**.

### Audit et Logs
*   **Journal d'Activité :** Trace toutes les actions métier (Qui a modifié quoi).
*   **Logs de Sécurité :** Trace les événements techniques (Login échoué, accès refusé).
*   **Export :** Les logs sont exportables en PDF pour audit externe.

---

## 5. Maintenance et Sauvegardes

### Sauvegardes (Backups)
*   **Menu :** Administration → Gestion des sauvegardes.
*   **Contenu du ZIP :**
    *   Dump SQL complet (PostgreSQL).
    *   Fichiers joints (`uploads/`).
    *   Configurations (`json`, `.env`).
*   **Fréquence :** Il est recommandé d'automatiser l'appel à l'API de backup ou de faire un export manuel hebdomadaire.

### Restauration
*   **Attention :** La restauration écrase la base de données actuelle.
*   Le système vérifie l'intégrité du ZIP (checksums) avant de lancer la restauration.

### Nettoyage BDD
Le script `cleanup_database.py` (exécutable en ligne de commande) permet de purger les données de test tout en conservant la configuration (utilisateurs, départements).
*   **Commande :** `python cleanup_database.py`
*   **Sécurité :** Demande une confirmation explicite.

---

## 6. Internationalisation (i18n)

Le système est multilingue par design.
*   **Menu :** Administration → Langues.
*   **Ajout :** Uploadez un fichier JSON respectant la structure des clés.
*   **Modification :** Téléchargez le JSON existant, modifiez les valeurs, et ré-uploadez.
*   **Activation :** Activez/Désactivez les langues disponibles pour les utilisateurs via les interrupteurs.

---

## 7. Dépannage Rapide

| Problème | Cause Probable | Solution |
|----------|----------------|----------|
| **Erreur 500** | Problème serveur ou BDD | Vérifier les logs Gunicorn et la connexion PostgreSQL. |
| **Login impossible** | IP bloquée ou mot de passe | Vérifier "IP Bloquées" ou réinitialiser le mot de passe. |
| **Pas d'email** | Config SMTP invalide | Vérifier les ports (587/465) et les identifiants. |
| **Lenteurs** | Base de données chargée | Vérifier les index ou la taille des logs. |
