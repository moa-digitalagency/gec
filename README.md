# 📮 GEC Mines - Système de Gestion Électronique du Courrier

## 🌍 Language / Langue

### 📖 Documentation

#### 🇫🇷 Français
- [📚 Documentation Technique](docs/README_TECHNICAL_FR.md) - Architecture, déploiement, API
- [💼 Documentation Commerciale](docs/README_COMMERCIAL_FR.md) - Fonctionnalités, tarifs, témoignages

#### 🇬🇧 English
- [📚 Technical Documentation](docs/README_TECHNICAL_EN.md) - Architecture, deployment, API
- [💼 Commercial Documentation](docs/README_COMMERCIAL_EN.md) - Features, pricing, testimonials

---

## 🚀 Aperçu Général

**GEC Mines** est un système complet de gestion électronique du courrier développé pour le Secrétariat Général des Mines en République Démocratique du Congo.

### ✨ Fonctionnalités Clés

- 📥 **Gestion Courrier Entrant/Sortant** avec pièces jointes obligatoires
- 🔍 **Recherche Avancée** dans tous les champs de métadonnées
- 🔐 **Sécurité Bancaire** avec chiffrement AES-256
- 👥 **Contrôle d'Accès Multi-niveaux** (Super Admin, Admin, Utilisateur)
- 📊 **Tableau de Bord Analytics** en temps réel
- 📱 **Design 100% Responsive** aux couleurs RDC
- 🌍 **Support Multi-langues** (Français/Anglais)
- 📄 **Génération PDF** pour documents officiels
- 📧 **Templates Email Configurables** avec test SMTP
- 💾 **Sauvegarde/Restauration** automatique

### 🛠️ Stack Technologique

**Backend**: Flask, PostgreSQL, SQLAlchemy, Chiffrement AES-256
**Frontend**: Tailwind CSS, DataTables, Font Awesome, Chart.js
**Sécurité**: bcrypt, cryptography, audit logging complet

---

## ⚡ Installation Rapide

### 1️⃣ Installation
```bash
# Cloner le dépôt
git clone [URL_REPOSITORY]
cd gec-mines

# Installer les dépendances
pip install -r project-dependencies.txt
```

### 2️⃣ Configuration
```bash
# Variables d'environnement
export DATABASE_URL="postgresql://..."
export SESSION_SECRET="votre-clé-secrète"
export GEC_MASTER_KEY="votre-clé-maître"
```

### 3️⃣ Lancement
```bash
# Démarrer l'application
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
# Accès via http://localhost:5000
```

---

## 📋 Dernières Mises à Jour (Août 2025)

✅ **Système de Templates Email**
- Templates multi-langues configurables (Français/Anglais)
- Variables dynamiques ({{numero_courrier}}, {{nom_utilisateur}}, etc.)
- Interface d'administration avec aperçu temps réel
- Test SMTP intégré dans les paramètres

✅ **Sécurité Avancée**
- Chiffrement AES-256-CBC pour toutes les données sensibles
- Hachage bcrypt renforcé avec salts personnalisés
- Protection contre les attaques par force brute
- Journalisation complète des événements de sécurité

✅ **Recherche Améliorée**
- Indexation complète des métadonnées (autres_informations, statut, fichier_nom)
- Filtre "SG en copie" pour courrier entrant uniquement
- Pièces jointes obligatoires pour tous types de courrier

✅ **Prêt pour Production**
- Nettoyage de tous les fichiers temporaires/test
- Optimisé pour déploiement externe
- Documentation complète en français et anglais

---

## 🎯 Design et Copyright

**© 2025 MOA Digital Agency LLC**

### 👨‍💻 Concepteur et Développeur
**AIsance KALONJI wa KALONJI**

### 📞 Contact MOA Digital Agency
- **📧 Email**: moa@myoneart.com
- **📧 Email alternatif**: moa.myoneart@gmail.com  
- **📱 Téléphone**: +212 699 14 000 1
- **📱 Téléphone RDC**: +243 86 049 33 45
- **🌐 Site web**: [myoneart.com](https://myoneart.com)

### 🏢 À Propos de MOA Digital Agency
MOA Digital Agency LLC est une agence de développement spécialisée dans la création de solutions digitales sur mesure pour les entreprises et institutions gouvernementales. Nous excellons dans le développement d'applications web robustes, sécurisées et évolutives.

---

## 📜 Licence

**© 2025 MOA Digital Agency LLC** | Tous droits réservés

Application conçue et développée par **AIsance KALONJI wa KALONJI** pour le Ministère des Mines de la République Démocratique du Congo.

---

<div align="center">

**Choisissez votre langue de documentation ci-dessus pour commencer !**

[🇫🇷 Documentation Française](docs/README_COMMERCIAL_FR.md) | [🇬🇧 English Documentation](docs/README_COMMERCIAL_EN.md)

---

*Développé avec 💖 et ☕ par **MOA Digital Agency LLC***

</div>