# Serveur Centralisé de Licences GEC Mines

## Description
Système autonome de gestion et validation des licences pour l'application GEC Mines. Ce serveur fonctionne indépendamment et permet la validation centralisée des licences avec synchronisation entre instances.

## Fonctionnalités

### 🔑 Gestion des Licences
- **Génération automatique**: 5000 licences pré-générées (1000 de chaque type)
- **Types disponibles**: 1 jour, 5 jours, 1 mois, 6 mois, 12 mois
- **Validation unique**: Chaque licence ne peut être utilisée qu'une seule fois
- **Activation centralisée**: Marquage automatique lors de l'utilisation

### 🌐 API REST
- `GET /api/validate/<license_key>` - Validation sans activation
- `POST /api/activate` - Activation d'une licence pour un domaine
- `GET /api/stats` - Statistiques complètes du serveur

### 🛡️ Sécurité
- **Base de données chiffrée**: PostgreSQL avec chiffrement
- **Validation d'empreinte**: Détection des changements de domaine
- **Logs d'audit**: Traçabilité complète des activations
- **Protection contre la duplication**: Système anti-contournement

## Installation et Configuration

### 1. Prérequis
```bash
# Python 3.11+
pip install flask flask-sqlalchemy psycopg2-binary sqlalchemy
```

### 2. Variables d'environnement
```bash
export LICENSE_DATABASE_URL="postgresql://user:password@host:port/database"
export LICENSE_SERVER_SECRET="your-secret-key-here"
```

### 3. Initialisation
```bash
cd license_server

# Génération des licences initiales
python generate_initial_licenses.py generate

# Démarrage du serveur
python app.py
```

### 4. Accès
- **Interface web**: http://localhost:5001
- **API**: http://localhost:5001/api/

## Utilisation

### Génération de licences
```bash
# Génère 5000 nouvelles licences
python generate_initial_licenses.py generate

# Affiche les statistiques
python generate_initial_licenses.py stats

# Remet à zéro la base
python generate_initial_licenses.py reset
```

### Interface Web
1. **Page d'accueil**: Vue d'ensemble et statistiques
2. **Génération**: Création de nouveaux lots de licences
3. **Test**: Validation en temps réel des licences

### API REST

#### Validation de licence
```bash
curl http://localhost:5001/api/validate/ABC123XYZ789
```

#### Activation de licence
```bash
curl -X POST http://localhost:5001/api/activate \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "ABC123XYZ789",
    "domain_fingerprint": "domain_hash_here"
  }'
```

## Intégration avec GEC Mines

### Configuration Client
L'application principale GEC Mines se connecte automatiquement au serveur centralisé via:

1. **Validation locale**: Fichiers cryptés locaux
2. **Validation centralisée**: API du serveur de licences
3. **Synchronisation**: Mise à jour automatique des statuts

### Flux d'activation
1. Utilisateur saisit la clé de licence
2. Validation locale et centralisée
3. Marquage de la licence comme utilisée
4. Enregistrement de l'activation avec empreinte du domaine
5. Calcul automatique de la date d'expiration

## Structure de la Base de Données

### Table `licenses`
```sql
CREATE TABLE licenses (
  id INTEGER PRIMARY KEY,
  license_key VARCHAR(12) UNIQUE NOT NULL,
  duration_days INTEGER NOT NULL,
  duration_label VARCHAR(50) NOT NULL,
  status VARCHAR(20) DEFAULT 'ACTIVE',
  is_used BOOLEAN DEFAULT FALSE,
  created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  used_date TIMESTAMP,
  activation_date TIMESTAMP,
  expiration_date TIMESTAMP,
  used_domain VARCHAR(100),
  used_ip VARCHAR(45),
  batch_id VARCHAR(50)
);
```

### Table `license_activations`
```sql
CREATE TABLE license_activations (
  id INTEGER PRIMARY KEY,
  license_key VARCHAR(12) REFERENCES licenses(license_key),
  domain_fingerprint VARCHAR(100) NOT NULL,
  activation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expiration_date TIMESTAMP NOT NULL,
  client_ip VARCHAR(45),
  user_agent TEXT,
  is_active BOOLEAN DEFAULT TRUE
);
```

## Déploiement

### Option 1: Replit Deployment
```bash
# Dans le dossier license_server
replit deploy
```

### Option 2: Serveur dédié
```bash
# Avec gunicorn
pip install gunicorn
gunicorn --bind 0.0.0.0:5001 --workers 4 app:app
```

### Option 3: Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5001
CMD ["python", "app.py"]
```

## Monitoring et Maintenance

### Logs
- Activations de licences
- Tentatives de validation échouées
- Statistiques d'utilisation

### Sauvegarde
```bash
# Sauvegarde de la base de données
pg_dump $LICENSE_DATABASE_URL > licenses_backup.sql

# Restauration
psql $LICENSE_DATABASE_URL < licenses_backup.sql
```

### Surveillance
- Nombre de licences disponibles
- Taux d'activation
- Détection des tentatives de contournement

## Sécurité

### Mesures implémentées
- Chiffrement des communications
- Validation d'intégrité des clés
- Protection contre les attaques par force brute
- Logs de sécurité complets

### Recommandations
- Utiliser HTTPS en production
- Sauvegarder régulièrement la base
- Monitorer les tentatives d'activation suspectes
- Renouveler les clés de chiffrement périodiquement

## Support

Pour toute question ou problème:
1. Vérifier les logs du serveur
2. Consulter les statistiques via `/api/stats`
3. Tester la connectivité avec les endpoints API

---

**GEC Mines License Server v1.0** - Système centralisé de gestion des licences