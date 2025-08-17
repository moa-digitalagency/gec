# 📚 GEC Mines Documentation Index

## 🌍 Available Languages

### 🇫🇷 Documentation Française

#### 📖 Documentation Technique
- [Architecture et Déploiement](README_TECHNICAL_FR.md)
  - Architecture système
  - Installation locale
  - Déploiement production
  - Configuration et monitoring
  - API et endpoints
  - Troubleshooting

#### 💼 Documentation Commerciale
- [Présentation et Fonctionnalités](README_COMMERCIAL_FR.md)
  - Fonctionnalités clés
  - Avantages et ROI
  - Tarification
  - Témoignages clients
  - Support et formation

#### 🚀 Guides de Déploiement
- [Checklist de Déploiement](deployment_checklist.md)
- [Notes de Déploiement](deployment_notes.md)

---

### 🇬🇧 English Documentation

#### 📖 Technical Documentation
- [Architecture and Deployment](README_TECHNICAL_EN.md)
  - System architecture
  - Local installation
  - Production deployment
  - Configuration and monitoring
  - API and endpoints
  - Troubleshooting

#### 💼 Commercial Documentation
- [Presentation and Features](README_COMMERCIAL_EN.md)
  - Key features
  - Benefits and ROI
  - Pricing
  - Customer testimonials
  - Support and training

#### 🚀 Deployment Guides
- [Deployment Checklist](deployment_checklist.md)
- [Deployment Notes](deployment_notes.md)

---

## 📋 Quick Reference

### System Requirements
- Python 3.8+
- PostgreSQL 12+ or SQLite
- 2GB RAM minimum
- 10GB disk space

### Default Credentials
- **Email**: admin@gecmines.cd
- **Password**: Admin@2025
- ⚠️ **Important**: Change immediately after first login

### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@host/db
SESSION_SECRET=your-secret-key
GEC_MASTER_KEY=your-encryption-key
GEC_PASSWORD_SALT=your-salt
```

### Quick Commands
```bash
# Start application
python main.py

# Run with Gunicorn
gunicorn --bind 0.0.0.0:5000 main:app

# Initialize database
python -c "from app import db; db.create_all()"
```

---

## 🔗 External Resources

- [Project Repository](https://github.com/gecmines)
- [Support Email](mailto:support@gecmines.cd)
- [Official Website](https://www.gecmines.cd)

---

© 2025 GEC Mines - Secrétariat Général des Mines