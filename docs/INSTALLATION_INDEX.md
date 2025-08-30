# Index des Installations GEC

## Vue d'Ensemble
Ce document centralise toutes les méthodes d'installation pour le système GEC - Gestion du Courrier, développé par MOA Digital Agency LLC.

## 🚀 Installations One-Click (Recommandées)

### Windows 10/11
- **Fichier**: `install-gec-windows.bat`
- **Prérequis**: Windows 10 v1903+ avec droits administrateur
- **Installation**: Clic droit → "Exécuter en tant qu'administrateur"
- **Durée**: ~10-15 minutes

### Windows Server (2008 R2+)
- **Fichier**: `install-gec-windows-server.bat`
- **Prérequis**: Windows Server 2008 R2 SP1+ avec droits administrateur
- **Installation**: Clic droit → "Exécuter en tant qu'administrateur"
- **Fonctionnalités**: Service Windows, pare-feu, sauvegarde automatique
- **Durée**: ~15-20 minutes

### macOS (10.15+)
- **Fichier**: `install-gec-macos.sh`
- **Installation**: 
  ```bash
  chmod +x install-gec-macos.sh
  ./install-gec-macos.sh
  ```
- **Prérequis**: Xcode Command Line Tools
- **Durée**: ~10-15 minutes

### Linux (Ubuntu/Debian/CentOS/RHEL/Fedora)
- **Fichier**: `install-gec-linux.sh`
- **Installation**: 
  ```bash
  curl -fsSL https://raw.githubusercontent.com/moa-digitalagency/gec/main/install-gec-linux.sh | bash
  ```
- **Fonctionnalités**: Service systemd optionnel, nginx, SSL
- **Durée**: ~10-20 minutes

## 📖 Documentation Détaillée

### Instructions Manuelles Complètes
- **Windows**: [INSTALLATION_WINDOWS.md](INSTALLATION_WINDOWS.md)
- **Windows Server**: [INSTALLATION_WINDOWS_SERVER_2008.md](INSTALLATION_WINDOWS_SERVER_2008.md)
- **macOS**: [INSTALLATION_MACOS.md](INSTALLATION_MACOS.md)
- **Linux**: [INSTALLATION_LINUX.md](INSTALLATION_LINUX.md)

## 🎯 Choix de la Méthode d'Installation

### Environnement de Développement/Test
- Utilisez les **installateurs one-click**
- Configuration SQLite (par défaut)
- Démarrage manuel de l'application

### Environnement de Production
- Suivez les **instructions manuelles détaillées**
- Configuration PostgreSQL recommandée
- Installation comme service système
- Configuration HTTPS/SSL
- Sauvegarde automatique

## ⚙️ Configuration Post-Installation

### Accès à l'Application
- **URL locale**: http://localhost:5000
- **Configuration réseau**: Modifiez `main.py` pour bind sur `0.0.0.0:5000`

### Configuration SMTP (Notifications Email)
Ajoutez dans le fichier `.env`:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_EMAIL=votre-email@domaine.com
SMTP_PASSWORD=votre-mot-de-passe-app
```

### Configuration Base de Données Production
```env
DATABASE_URL=postgresql://username:password@localhost/geccourrier
```

## 🔧 Dépannage Courant

### Port 5000 Déjà Utilisé
- **Windows**: `netstat -ano | findstr :5000`
- **macOS/Linux**: `lsof -i :5000`
- **Solution**: Tuer le processus ou changer le port

### Erreurs de Permissions
- **Windows**: Exécuter en tant qu'administrateur
- **macOS/Linux**: Utiliser `sudo` pour l'installation système

### Erreurs SSL/Certificats
- Mettre à jour les certificats système
- Utiliser `--trusted-host` pour pip si nécessaire

## 📊 Comparaison des Installations

| Système | One-Click | Service Auto | Production Ready | Complexité |
|---------|-----------|--------------|------------------|------------|
| Windows 10/11 | ✅ | ❌ | ⚠️ | Faible |
| Windows Server | ✅ | ✅ | ✅ | Moyenne |
| macOS | ✅ | ⚠️ | ⚠️ | Faible |
| Linux | ✅ | ✅ | ✅ | Moyenne |

**Légende**: ✅ Complet, ⚠️ Partiel, ❌ Non disponible

## 📞 Support Technique

### Contacts
- **Entreprise**: MOA Digital Agency LLC
- **Développeur**: AIsance KALONJI wa KALONJI
- **Email**: moa@myoneart.com
- **Téléphone**: +212 699 14 000 1 / +243 86 049 33 45
- **Site Web**: myoneart.com

### Ressources
- **Documentation**: Dossier `docs/`
- **Code Source**: GitHub (lien dans les installateurs)
- **Dépendances**: `project-dependencies.txt`

## 🔄 Mises à Jour

### Système de Mise à Jour Intégré
- **En ligne**: Via Git (interface admin)
- **Hors ligne**: Upload de fichier ZIP
- **Préservation**: Base de données et configuration automatiquement sauvegardées

### Mise à Jour Manuelle
```bash
cd gec
git pull origin main
source .venv/bin/activate  # Linux/macOS
# ou
.venv\Scripts\activate.bat  # Windows
pip install -r project-dependencies.txt
```

## 📝 Notes de Version

### Version Actuelle: 1.0.1
- ✅ Templates d'email multi-langues
- ✅ Système de mise à jour intelligent
- ✅ Sécurité renforcée (AES-256, bcrypt)
- ✅ Interface d'administration complète
- ✅ Support notifications email (SMTP/SendGrid)
- ✅ Installateurs automatiques tous OS

---

*Ce document est maintenu à jour avec chaque nouvelle version de GEC Courrier.*