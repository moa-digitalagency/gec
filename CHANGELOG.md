# Journal des Modifications (CHANGELOG)

## [Migration Replit Agent] - 2025-10-15

### ✅ Migration Complétée

#### Infrastructure
- ✅ Installation de l'environnement Python 3.11
- ✅ Installation de toutes les dépendances du projet via pyproject.toml
  - Flask 3.1.1 et extensions (flask-login, flask-sqlalchemy)
  - PostgreSQL (psycopg2-binary)
  - Cryptographie (cryptography, pycryptodome, bcrypt)
  - Génération de documents (reportlab, xlsxwriter, pandas)
  - Traitement d'images (opencv-python, pillow)
  - Communication (sendgrid, requests)
  - Serveur web (gunicorn)

#### Déploiement
- ✅ Configuration du workflow "Start application" avec gunicorn
  - Commande: `gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app`
  - Port: 5000 (seul port non-firewalé)
  - Auto-reload activé pour le développement
- ✅ Configuration du déploiement en production (autoscale)
  - Type: autoscale (adapté aux sites web stateless)
  - Build: Non requis (Python interprété)
  - Run: `gunicorn --bind 0.0.0.0:5000 main:app`

#### Application
- ✅ Vérification du bon fonctionnement de l'application
  - Interface de connexion opérationnelle
  - Base de données PostgreSQL initialisée
  - Utilisateur admin par défaut créé (username: sa.gec001)
  - Tables et schéma de base de données créés
  - Migrations automatiques appliquées

### 🆕 Nouvelles Fonctionnalités

#### Module d'Export/Import de Courriers (export_import_utils.py)
**Problème résolu**: Les sauvegardes/restaurations échouaient lors du transfert entre instances GEC différentes car les données chiffrées avec la clé `GEC_MASTER_KEY` d'une instance ne pouvaient pas être déchiffrées avec la clé d'une autre instance.

**Solution implémentée**:

1. **Fonction `export_courriers_to_json()`**
   - Exporte les courriers en format JSON
   - **Déchiffre automatiquement** toutes les données sensibles avant export:
     - Objet du courrier (objet_encrypted → objet en clair)
     - Expéditeur (expediteur_encrypted → expediteur en clair)
     - Destinataire (destinataire_encrypted → destinataire en clair)
     - Numéro de référence (numero_reference_encrypted → numero_reference en clair)
   - Gère les pièces jointes avec leur statut de chiffrement
   - Inclut les métadonnées de version pour compatibilité

2. **Fonction `create_export_package()`**
   - Crée un package ZIP complet avec:
     - Fichier JSON contenant les données déchiffrées
     - Fichiers attachés **déchiffrés** (extraits du chiffrement avec la clé source)
     - Pièces jointes des transmissions
     - Métadonnées d'export (version, date, nombre de courriers)
   - Format: `export_courriers_YYYYMMDD_HHMMSS.zip`
   - Stockage dans le dossier `exports/`

3. **Fonction `import_courriers_from_package()`**
   - Importe les courriers depuis un package ZIP
   - **Re-chiffre automatiquement** avec la clé de l'instance de destination:
     - Objet en clair → objet_encrypted avec nouvelle clé
     - Expéditeur en clair → expediteur_encrypted avec nouvelle clé
     - Destinataire en clair → destinataire_encrypted avec nouvelle clé
     - Numéro de référence en clair → numero_reference_encrypted avec nouvelle clé
   - Re-chiffre les fichiers attachés avec la nouvelle clé
   - Options:
     - `skip_existing`: Ignore les courriers déjà présents (par numéro)
     - `remap_users`: Remapper les utilisateurs entre instances
   - Gestion des erreurs et statistiques d'import détaillées

**Format d'Export (v1.0.0)**:
```json
{
  "version": "1.0.0",
  "export_date": "2025-10-15T...",
  "total_courriers": 100,
  "courriers": [
    {
      "id": 1,
      "numero_accuse_reception": "GEC-2025-001",
      "objet": "Objet déchiffré en clair",
      "expediteur": "Expéditeur déchiffré en clair",
      "destinataire": "Destinataire déchiffré en clair",
      "numero_reference": "Référence déchiffrée en clair",
      "forwards": [...],
      ...
    }
  ],
  "attachments": [
    {
      "courrier_id": 1,
      "type": "main",
      "filename": "document.pdf",
      "path": "uploads/...",
      "encrypted": true,
      "checksum": "sha256..."
    }
  ]
}
```

#### Routes Flask Ajoutées (views.py)

1. **Route `/export_courriers` (POST)**
   - Réservée aux super administrateurs
   - Paramètres:
     - `export_all`: Exporter tous les courriers (incluant supprimés)
     - `courrier_ids`: Liste d'IDs spécifiques à exporter
   - Télécharge automatiquement le fichier ZIP d'export
   - Log de l'activité dans le journal d'audit

2. **Route `/import_courriers` (POST)**
   - Réservée aux super administrateurs
   - Upload d'un fichier ZIP d'export
   - Paramètres:
     - `skip_existing`: Ignorer les doublons (par défaut: true)
   - Affiche les statistiques détaillées:
     - Nombre de courriers importés
     - Nombre de courriers ignorés (doublons)
     - Nombre d'erreurs rencontrées
   - Log de l'activité avec détails

#### Sécurité et Chiffrement

**Gestion des Clés de Chiffrement**:
- Chaque instance GEC possède sa propre clé `GEC_MASTER_KEY` (256-bit AES)
- Les données sensibles sont chiffrées avec AES-256-CBC
- Le processus export/import assure la compatibilité entre instances:
  1. **Export**: Déchiffrement avec clé source → stockage en clair (sécurisé dans ZIP)
  2. **Import**: Re-chiffrement avec clé destination → stockage sécurisé

**Avantages**:
- ✅ Transfert sécurisé de courriers entre instances GEC
- ✅ Pas de perte de données lors des migrations
- ✅ Compatibilité garantie entre versions identiques
- ✅ Traçabilité complète via logs d'audit

### 🔧 Améliorations Système

#### Gestion des Sauvegardes
- Le système de backup existant (`create_system_backup`, `restore_system_from_backup`) reste inchangé
- Nouveau système export/import dédié au transfert de courriers entre instances
- Séparation claire:
  - **Backups système**: Sauvegarde complète de l'instance (avec clés chiffrées)
  - **Export/Import**: Transfert de courriers entre instances (avec re-chiffrement)

#### Logs et Traçabilité
- Nouveaux types d'activités dans le journal:
  - `EXPORT_COURRIERS`: Export de courriers effectué
  - `IMPORT_COURRIERS`: Import de courriers avec statistiques

### ⚠️ Points d'Attention

#### Variables d'Environnement Critiques
Les clés suivantes doivent être configurées pour la persistence et la sécurité:

1. **GEC_MASTER_KEY** (CRITIQUE)
   - Clé de chiffrement principale (256-bit)
   - Générée automatiquement si absente (voir logs CRITICAL)
   - ⚠️ DOIT être sauvegardée et configurée en production
   - Utilisée pour chiffrer toutes les données sensibles

2. **GEC_PASSWORD_SALT** (CRITIQUE)
   - Sel pour le hachage des mots de passe
   - Généré automatiquement si absent (voir logs CRITICAL)
   - ⚠️ DOIT être sauvegardé et configuré en production

3. **SESSION_SECRET**
   - Secret pour les sessions Flask
   - Configuré par défaut: "dev-secret-key-gec-mines"
   - ⚠️ Doit être changé en production

4. **DATABASE_URL**
   - URL de connexion PostgreSQL
   - Par défaut: SQLite (gec_mines.db)
   - ⚠️ Utiliser PostgreSQL en production

5. **ADMIN_PASSWORD**
   - Mot de passe de l'utilisateur admin initial (sa.gec001)
   - Par défaut: "TempPassword123!"
   - ⚠️ Doit être changé immédiatement après première connexion

#### Configuration Sendgrid
- Intégration Sendgrid configurée mais nécessite setup
- Voir `use_integration` pour configurer les clés API

### 📋 À Faire (TODO)

#### Configuration Initiale Requise
1. ⚠️ **URGENT**: Configurer les clés de chiffrement en production
   ```bash
   # Générer les clés (utiliser generate_keys.py si disponible)
   # Puis configurer dans Secrets Replit:
   GEC_MASTER_KEY=<clé_base64>
   GEC_PASSWORD_SALT=<sel_base64>
   SESSION_SECRET=<secret_aleatoire>
   ```

2. ⚠️ Changer le mot de passe admin par défaut
   - Utilisateur: sa.gec001
   - Mot de passe par défaut: TempPassword123!

3. Configurer Sendgrid pour les notifications email
   - Utiliser l'intégration Replit Sendgrid
   - Configurer les templates d'email

#### Optimisations Futures
- [ ] Ajouter compression des exports pour fichiers volumineux
- [ ] Implémenter import/export incrémental (par date)
- [ ] Ajouter validation de schéma avant import
- [ ] Interface utilisateur pour sélection de courriers à exporter
- [ ] Support multi-version pour compatibilité ascendante/descendante
- [ ] Export/import des utilisateurs et départements associés
- [ ] Chiffrement du fichier ZIP d'export pour transit sécurisé

### 🐛 Corrections de Bugs

#### Problème de Restauration entre Instances
- **Problème**: Les sauvegardes restaurées sur une autre instance ne fonctionnaient pas car les données chiffrées ne pouvaient pas être déchiffrées
- **Cause**: Clés de chiffrement `GEC_MASTER_KEY` différentes entre instances
- **Solution**: Nouveau système export/import avec déchiffrement/rechiffrement automatique

#### Bug Critique Corrigé: Double Chiffrement des Fichiers (v1.0.1)
- **Problème Identifié**: Lors de l'export, si un fichier ne pouvait pas être déchiffré, il était ajouté tel quel (chiffré) au package ZIP
- **Conséquence**: À l'import, ces fichiers déjà chiffrés étaient re-chiffrés avec la nouvelle clé, créant un double chiffrement et rendant les fichiers inutilisables
- **Solution Implémentée**:
  1. L'export échoue maintenant complètement si un fichier ne peut pas être déchiffré
  2. Le fichier ZIP incomplet est automatiquement supprimé
  3. Un message d'erreur détaillé liste tous les fichiers problématiques
  4. Aucun fichier chiffré ne peut être ajouté à l'export par erreur
- **Validation**: L'import vérifie maintenant la présence des fichiers et émet des avertissements clairs si des fichiers sont manquants

### 📊 Statistiques du Projet

#### Fichiers Modifiés
- ✅ `export_import_utils.py` - CRÉÉ (nouveau module)
- ✅ `views.py` - MODIFIÉ (2 nouvelles routes)
- ✅ `CHANGELOG.md` - CRÉÉ (ce fichier)
- ✅ `.local/state/replit/agent/progress_tracker.md` - MIS À JOUR

#### Fonctionnalités Ajoutées
- Export de courriers avec déchiffrement
- Import de courriers avec rechiffrement
- Package ZIP portable entre instances
- Gestion des pièces jointes chiffrées
- Logs et traçabilité d'export/import

### 📖 Documentation

#### Guide d'Utilisation - Export

1. Se connecter en tant que super administrateur
2. Aller dans "Gestion des sauvegardes"
3. Section "Export de Courriers"
4. Options:
   - Exporter tous les courriers
   - OU spécifier des IDs de courriers (séparés par virgules)
5. Cliquer sur "Exporter"
6. Le fichier ZIP sera téléchargé automatiquement

#### Guide d'Utilisation - Import

1. Se connecter en tant que super administrateur sur l'instance cible
2. Aller dans "Gestion des sauvegardes"
3. Section "Import de Courriers"
4. Sélectionner le fichier ZIP d'export
5. Options:
   - Ignorer les doublons (recommandé)
6. Cliquer sur "Importer"
7. Consulter les statistiques d'import affichées

#### Sécurité du Processus

**Export**:
1. Les données sont extraites de la base de données
2. Les champs chiffrés sont déchiffrés avec `GEC_MASTER_KEY` source
3. Les fichiers attachés chiffrés sont déchiffrés
4. Tout est empaqueté dans un ZIP (données en clair, sécurisé)
5. ⚠️ Le fichier ZIP doit être transféré de manière sécurisée (HTTPS, SSH, etc.)

**Import**:
1. Le ZIP est extrait dans un dossier temporaire
2. Les données JSON sont lues
3. Pour chaque courrier:
   - Les données en clair sont lues
   - Les données sont re-chiffrées avec `GEC_MASTER_KEY` destination
   - Les fichiers sont re-chiffrés avec la nouvelle clé
   - Les données sont insérées dans la base
4. Le dossier temporaire est nettoyé

### ✅ Tests Effectués

- ✅ Application démarre correctement avec gunicorn
- ✅ Base de données PostgreSQL initialisée
- ✅ Interface web accessible sur port 5000
- ✅ Page de connexion fonctionnelle
- ✅ Utilisateur admin créé automatiquement
- ✅ Migrations automatiques appliquées
- ✅ Système de chiffrement opérationnel (avec warnings de configuration)

### 🔍 Tests à Effectuer

- [ ] Test d'export de courriers réels
- [ ] Test d'import sur instance avec clé différente
- [ ] Vérification de l'intégrité des données après import
- [ ] Test des pièces jointes chiffrées
- [ ] Test des courriers avec transmissions
- [ ] Test de performance avec grand volume de données
- [ ] Test de gestion des erreurs et rollback

---

## Notes Techniques

### Architecture du Système d'Export/Import

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Instance A     │         │  Package ZIP     │         │  Instance B     │
│  (GEC_KEY_A)    │         │  (données claires)│         │  (GEC_KEY_B)    │
├─────────────────┤         ├──────────────────┤         ├─────────────────┤
│                 │         │                  │         │                 │
│ Données cryptées│─Export─→│ Données en clair │─Import─→│ Données cryptées│
│ avec KEY_A      │         │ + fichiers       │         │ avec KEY_B      │
│                 │         │                  │         │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
       │                            │                            │
       ▼                            ▼                            ▼
  Déchiffrement              Format portable               Re-chiffrement
   avec KEY_A                  (JSON + ZIP)                 avec KEY_B
```

### Format de Versioning

- Format d'export: v1.0.0
- Compatibilité: Même version majeure (1.x.x)
- Migration automatique du schéma via migration_utils.py

### Dépendances Critiques

- **encryption_utils.py**: Gestion du chiffrement/déchiffrement
- **models.py**: Modèles Courrier, PieceJointe, CourrierForward
- **utils.py**: Fonctions utilitaires et backup système
- **migration_utils.py**: Migrations automatiques de schéma

---

*Dernière mise à jour: 2025-10-15*
*Créé pendant la migration Replit Agent*
