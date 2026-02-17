![Python Version](https://img.shields.io/badge/Python-3.11-blue) ![Framework](https://img.shields.io/badge/Framework-Flask%203.1-green) ![Database](https://img.shields.io/badge/Database-PostgreSQL-336791) ![Status: Private/Internal](https://img.shields.io/badge/Status-Private%2FInternal-red) ![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red) ![Owner: MOA Digital Agency](https://img.shields.io/badge/Owner-MOA%20Digital%20Agency-orange)

[ 🇫🇷 Français ](README.md) | [ 🇬🇧 English ](README_en.md)

# GEC - Gestion Électronique du Courrier

> **LOGICIEL PROPRIÉTAIRE - USAGE INTERNE STRICT.**
> Toute copie, distribution ou modification non autorisée est interdite.
> Copyright © 2024 MOA Digital Agency.

## 📌 Présentation
GEC est une solution de classe "Enterprise" pour la dématérialisation et la gestion sécurisée des flux de courriers (Entrants/Sortants). Conçue pour répondre aux exigences de haute sécurité (Chiffrement AES-256) et de traçabilité (Audit Logs) des administrations.

## 🏗 Architecture Globale

```mermaid
graph TD
    User[Utilisateur] -->|HTTPS| Proxy[Nginx]
    Proxy -->|WSGI| App[GEC Core (Flask)]
    App -->|SQL| DB[(PostgreSQL)]
    App -->|FS| Storage[Secure Storage]
```

## 📑 Documentation

Toute la documentation technique et fonctionnelle se trouve dans le dossier `docs/`.

| Document | Description |
|----------|-------------|
| [**📖 La Bible des Fonctionnalités**](docs/GEC_features_full_list.md) | Liste exhaustive de toutes les fonctionnalités. |
| [**🏗 Architecture Technique**](docs/GEC_technical_architecture.md) | Stack, flux de données et sécurité. |
| [**⚖️ Licence**](LICENSE) | Termes d'utilisation et propriété. |

## 🚀 Installation Rapide

```bash
# 1. Cloner (Accès restreint)
git clone https://github.com/moa-digitalagency/gec.git

# 2. Environnement
# Créer un environnement virtuel (venv)
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configuration
cp .env.example .env
# Configurer GEC_MASTER_KEY et DB_URL

# 4. Lancer
python main.py
```

## 📞 Contact
Pour toute question technique ou juridique : **MOA Digital Agency** (myoneart.com).
