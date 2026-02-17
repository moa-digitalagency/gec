![Python Version](https://img.shields.io/badge/Python-3.11-blue) ![Framework](https://img.shields.io/badge/Framework-Flask%203.1-green) ![Database](https://img.shields.io/badge/Database-PostgreSQL-336791) ![Status: Private/Internal](https://img.shields.io/badge/Status-Private%2FInternal-red) ![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red) ![Owner: MOA Digital Agency](https://img.shields.io/badge/Owner-MOA%20Digital%20Agency-orange)

[ 🇫🇷 Français ](README.md) | [ 🇬🇧 English ](README_en.md)

# GEC - Electronic Mail Management

> **PROPRIETARY SOFTWARE - STRICTLY INTERNAL USE.**
> Any unauthorized copying, distribution, or modification is prohibited.
> Copyright © 2024 MOA Digital Agency.

## 📌 Overview
GEC is an "Enterprise" class solution for the dematerialization and secure management of mail flows (Incoming/Outgoing). Designed to meet high security requirements (AES-256 Encryption) and traceability (Audit Logs) for administrations.

## 🏗 Global Architecture

```mermaid
graph TD
    User["User"] -->|HTTPS| Proxy["Nginx"]
    Proxy -->|WSGI| App["GEC Core (Flask)"]
    App -->|SQL| DB[("PostgreSQL")]
    App -->|FS| Storage["Secure Storage"]
```

## 📑 Documentation

All technical and functional documentation can be found in the `docs/` folder.

| Document | Description |
|----------|-------------|
| [**📖 The Features Bible**](docs/GEC_features_full_list_en.md) | Exhaustive list of all features. |
| [**🏗 Technical Architecture**](docs/GEC_technical_architecture_en.md) | Stack, data flows, and security. |
| [**⚖️ License**](LICENSE_en) | Terms of use and ownership. |

## 🚀 Quick Install

```bash
# 1. Clone (Restricted Access)
git clone https://github.com/moa-digitalagency/gec.git

# 2. Environment
# Create a virtual environment (venv)
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configuration
cp .env.example .env
# Configure GEC_MASTER_KEY and DB_URL

# 4. Run
python main.py
```

## 📞 Contact
For any technical or legal questions: **MOA Digital Agency** (myoneart.com).
