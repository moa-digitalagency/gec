[ 🇫🇷 Français ](GEC_technical_architecture.md) | [ 🇬🇧 English ](GEC_technical_architecture_en.md)

# GEC - Architecture Technique

> **DOCUMENT TECHNIQUE INTERNE.**
> Ce document décrit l'architecture logicielle, la stack technique et les flux de données.
> Propriété de MOA Digital Agency.

## 1. Vue d'Ensemble

L'architecture repose sur un modèle monolithique modulaire utilisant **Flask (Python)** comme backend et **Jinja2 + Tailwind** pour le frontend. La persistance est assurée par **PostgreSQL**.

### Diagramme d'Architecture

```mermaid
graph TD
    User[Utilisateur (Navigateur)] -->|HTTPS / JSON| LB[Reverse Proxy (Nginx/Apache)]
    LB -->|WSGI| Gunicorn[Serveur Gunicorn]

    subgraph "Application Flask (GEC)"
        Auth[Security Layer<br/>(CSRF, Auth, RateLimit)]

        subgraph "Modules"
            Core[Core Module<br/>(Courriers, Workflow)]
            Admin[Admin Module<br/>(Users, Depts)]
            Stats[Reporting Module<br/>(Charts, Exports)]
        end

        ORM[SQLAlchemy ORM]
    end

    subgraph "Stockage"
        DB[(PostgreSQL<br/>Données Chiffrées)]
        FS[File System<br/>(Uploads Sécurisés)]
    end

    Gunicorn --> Auth
    Auth --> Core & Admin & Stats
    Core & Admin & Stats --> ORM
    ORM --> DB
    Core --> FS
```

## 2. Stack Technique

### Backend
*   **Langage :** Python 3.11+
*   **Framework :** Flask 3.x
*   **ORM :** SQLAlchemy 2.x
*   **Sécurité :** Cryptography (Fernet), Bcrypt, Werkzeug
*   **Dépendances Clés :**
    *   `flask-login` : Gestion de session.
    *   `flask-migrate` : Migrations de base de données.
    *   `reportlab` : Génération PDF.
    *   `sendgrid-python` : Envoi d'emails transactionnels.

### Frontend
*   **Templating :** Jinja2 (Rendu côté serveur).
*   **CSS :** Tailwind CSS (Utility-first).
*   **JS :** Vanilla JS + jQuery (Manipulation DOM) + Chart.js (Analytics).
*   **Assets :** FontAwesome (Icônes), Google Fonts (Inter).

### Base de Données
*   **SGBD :** PostgreSQL 14+ (Production) / SQLite (Dev).
*   **Chiffrement :** Données sensibles chiffrées au repos (AES-256).
*   **Connexion :** Pool via SQLAlchemy Engine.

## 3. Sécurité & Flux de Données

### 3.1 Cycle de Vie d'une Requête
1.  **Entrée :** La requête arrive via Gunicorn.
2.  **Middleware :**
    *   Vérification des Headers de sécurité.
    *   Validation CSRF (si POST).
    *   Rate Limiting (si endpoint sensible).
3.  **Routing :** Dispatch vers la vue appropriée (`views.py`).
4.  **Contrôle d'Accès :** Décorateur `@login_required` et `@check_permission`.
5.  **Traitement :** Logique métier, appel BDD via ORM.
6.  **Rendu :** Injection des données dans le template Jinja2 ou retour JSON.

### 3.2 Gestion des Fichiers
*   Les fichiers uploadés ne sont JAMAIS servis directement par le serveur web sans validation.
*   Chemin : `uploads/{year}/{month}/`.
*   Nommage : `secure_filename` + Timestamp unique.

## 4. Déploiement Type
*   **OS :** Linux (Ubuntu/Debian) recommandé.
*   **Serveur App :** Gunicorn (Workers synchrones ou gevent).
*   **Process Manager :** Systemd.
*   **Reverse Proxy :** Nginx (Gestion SSL, Compression Gzip, Static Files).
