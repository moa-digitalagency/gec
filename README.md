# GEC - Système de Gestion Électronique du Courrier

![Status](https://img.shields.io/badge/Status-Production%20Ready-success)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Framework](https://img.shields.io/badge/Framework-Flask%203.1-green)
![License](https://img.shields.io/badge/License-Proprietary-red)

> **Solution digitale complète pour l'administration moderne.**
> Sécurisée, évolutive et auditée pour la gestion des courriers entrants et sortants.

---

## 📑 Table des Matières
1.  [Aperçu](#aperçu)
2.  [Fonctionnalités Clés](#fonctionnalités-clés)
3.  [Stack Technique](#stack-technique)
4.  [Démarrage Rapide](#démarrage-rapide)
5.  [Architecture](#architecture)
6.  [Documentation](#documentation)
7.  [Support & Contact](#support--contact)

---

## 🚀 Aperçu

GEC est une plateforme web conçue spécifiquement pour les administrations gouvernementales et grandes entreprises (focus RDC). Elle dématérialise l'intégralité du flux courrier, garantissant traçabilité, sécurité (chiffrement AES-256) et conformité aux standards administratifs.

---

## ✨ Fonctionnalités Clés

*   **🔐 Sécurité Militaire :** Chiffrement AES-256 des données sensibles, Hachage Argon2/Bcrypt, Protection Brute-force & IP Blocking.
*   **📧 Gestion Complète :** Courriers Entrants/Sortants, Accusés de réception automatiques, Gestion des pièces jointes (PDF/Images).
*   **🔄 Workflow Collaboratif :** Transmission inter-services, Commentaires, Annotations, Notifications temps réel.
*   **🌍 Multi-langues :** Interface disponible en 10+ langues (Français, Anglais, Espagnol, etc.) avec détection auto.
*   **📊 Analytics :** Tableau de bord décisionnel, KPIs temps réel, Exports PDF officiels.
*   **🛠 Administration :** RBAC (Rôles & Permissions), Gestion des Départements, Audit Logs complets.
*   **💾 Sauvegardes :** Système de backup/restore complet (BDD + Fichiers + Config).

---

## 🛠 Stack Technique

*   **Backend :** Python 3.11, Flask, SQLAlchemy, Gunicorn.
*   **Database :** PostgreSQL (Production) / SQLite (Dev).
*   **Frontend :** Jinja2, Tailwind CSS, jQuery, Chart.js.
*   **Sécurité :** Cryptography (AES), BCrypt, Werkzeug.
*   **Services :** SendGrid (Emails), ReportLab (PDF).

---

## ⚡ Démarrage Rapide

### Prérequis
*   Python 3.11+
*   PostgreSQL (recommandé)

### Installation

```bash
# 1. Cloner le projet
git clone https://github.com/moa-digitalagency/gec.git
cd gec

# 2. Créer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .\.venv\Scripts\Activate.ps1  # Windows

# 3. Installer les dépendances
pip install -r project-dependencies.txt

# 4. Configurer l'environnement
cp .env.example .env
# Modifiez .env avec vos clés (Générées via python generate_keys.py)

# 5. Lancer l'application
python main.py
```

L'application sera accessible sur `http://localhost:5000`.
*   **Admin par défaut :** `sa.gec001`
*   **Mot de passe :** `TempPassword123!`

---

## 📚 Documentation

La documentation complète est disponible dans le dossier `docs/` :

| Fichier | Description |
|---------|-------------|
| [📖 Features Bible](docs/GEC_Features_List.md) | Liste exhaustive de toutes les fonctionnalités (Technique & Métier). |
| [🏗 Architecture](docs/GEC_Architecture_Technique.md) | Structure du code, Modèle de données et Stack. |
| [🛡 Sécurité](docs/GEC_Securite.md) | Détails sur le chiffrement, l'audit et les protections. |
| [🔧 Installation](docs/GEC_Installation_Deploiement.md) | Guide pas-à-pas pour l'installation serveur. |
| [👑 Administration](docs/GEC_Guide_Administration.md) | Guide pour les Super Admins (Config, Rôles, Maintenance). |
| [👤 Guide Utilisateur](docs/GEC_Guide_Utilisateur.md) | Manuel d'utilisation pour les agents (Enregistrement, Recherche). |

---

## 📞 Support & Contact

**MOA Digital Agency LLC**
*   **Développeur :** AIsance KALONJI wa KALONJI
*   **Email :** moa@myoneart.com
*   **Web :** [myoneart.com](https://myoneart.com)

---
© 2025 MOA Digital Agency LLC. Tous droits réservés.
