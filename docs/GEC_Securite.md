# Sécurité - GEC

## Introduction

Ce document décrit les mesures de sécurité implémentées dans le système GEC. La sécurité est une priorité absolue compte tenu de la nature sensible des courriers administratifs gérés par l'application.

---

## Chiffrement des Données

### Chiffrement au Repos

#### Données Sensibles

Les données suivantes sont chiffrées en base de données avec AES-256-CBC :

**Utilisateurs** :
- Adresse email
- Nom complet
- Matricule
- Fonction
- Hash du mot de passe

**Courriers** :
- Objet
- Expéditeur
- Destinataire
- Numéro de référence

**Système** :
- Clé API SendGrid
- Mot de passe SMTP

#### Fichiers Attachés

Les pièces jointes peuvent être chiffrées avec AES-256-CBC :
- Chiffrement automatique à l'upload
- Déchiffrement à la volée pour le téléchargement
- Checksum SHA-256 pour l'intégrité

### Clés de Chiffrement

#### GEC_MASTER_KEY

Clé maître de 256 bits utilisée pour tout le chiffrement applicatif.

**Génération** :
```bash
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

**Stockage** :
- Variable d'environnement (recommandé)
- Jamais en clair dans le code
- Jamais dans le dépôt Git

**Rotation** :
1. Exporter toutes les données (elles seront déchiffrées)
2. Modifier GEC_MASTER_KEY
3. Réimporter les données (elles seront rechiffrées)

#### GEC_PASSWORD_SALT

Sel additionnel pour le hachage des mots de passe.

**Fonction** : Ajout d'entropie aux mots de passe avant hachage bcrypt
**Génération** : Identique à GEC_MASTER_KEY

---

## Authentification

### Hachage des Mots de Passe

Algorithme : bcrypt avec 12 rounds + sel applicatif

```
password → (password + GEC_PASSWORD_SALT) → bcrypt(12 rounds) → hash
```

### Exigences Mot de Passe

- Minimum 8 caractères
- Au moins une majuscule
- Au moins une minuscule
- Au moins un chiffre
- Au moins un caractère spécial (!@#$%^&*...)
- Pas de patterns prévisibles (123, abc, etc.)
- Pas de mots de passe courants (password, admin, etc.)

### Protection Contre Brute Force

| Paramètre | Valeur |
|-----------|--------|
| Tentatives max avant blocage | 8 |
| Durée du blocage | 15 minutes |
| Seuil activités suspectes | 15 |
| Blocage automatique IP | 30 minutes |

### Rate Limiting

Limites par défaut par route :

| Route | Limite |
|-------|--------|
| Login | 30 requêtes / 15 min |
| Enregistrement courrier | 50 requêtes / 15 min |
| API générale | 10 requêtes / 15 min |

---

## Protection Contre les Attaques

### Injection SQL

**Mesures** :
- Utilisation exclusive de l'ORM SQLAlchemy
- Paramètres bindés pour requêtes brutes
- Détection de patterns malveillants
- Sanitization automatique des entrées

**Patterns détectés** :
```
UNION SELECT, DROP TABLE, TRUNCATE
exec(), execute(), sp_executesql
0x (encodage hexadécimal)
OR 1=1, AND 1=0
```

### Cross-Site Scripting (XSS)

**Mesures** :
- Échappement automatique Jinja2
- Fonction sanitize_input() sur toutes les entrées
- Headers Content-Security-Policy restrictifs

**Patterns détectés** :
```
<script>...</script>
javascript:
onerror=, onclick=
<iframe>, <object>, <embed>
```

### Cross-Site Request Forgery (CSRF)

**Mesures** :
- Tokens de session UUID4
- Validation sur toutes les requêtes POST
- Cookies sécurisés (HttpOnly, Secure, SameSite)

### Path Traversal

**Mesures** :
- Suppression de `..` dans les chemins de fichiers
- Limitation de la longueur des noms de fichiers (255 car.)
- Validation des extensions autorisées

### Open Redirect

**Mesures** :
- Validation des URLs de redirection
- Interdiction des schémas dangereux (javascript:, data:)
- Liste blanche des hôtes autorisés

---

## Validation des Fichiers

### Extensions Autorisées

```
pdf, png, jpg, jpeg, tiff, tif, svg
```

### Validation du Contenu

Vérification des headers de fichiers (magic bytes) :

| Extension | Header attendu |
|-----------|----------------|
| PDF | %PDF |
| PNG | \x89PNG\r\n\x1a\n |
| JPEG | \xff\xd8\xff |
| TIFF | II*\x00 |

### Limites

- Taille maximale : 16 MB par fichier
- Taille totale upload : 100 MB

---

## Headers de Sécurité HTTP

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Cache-Control: no-cache, no-store, must-revalidate
```

### Content-Security-Policy

```
default-src 'self';
script-src 'self' 'unsafe-inline';
style-src 'self' 'unsafe-inline';
font-src 'self' data:;
img-src 'self' data:;
connect-src 'self';
frame-ancestors 'none';
```

---

## Gestion des Sessions

### Configuration

- Durée de vie : 30 jours
- Stockage : Cookie signé côté client
- Régénération : À chaque connexion

### Token de Session

- Génération : secrets.token_urlsafe(32)
- Validation : Vérification IP, expiration 24h
- Invalidation : À la déconnexion

---

## Journalisation de Sécurité

### Événements Journalisés

| Type | Description |
|------|-------------|
| LOGIN_SUCCESS | Connexion réussie |
| LOGIN_FAILED | Tentative de connexion échouée |
| LOGIN_BLOCKED | Connexion bloquée (rate limit) |
| LOGOUT | Déconnexion |
| ACCESS_DENIED | Accès refusé (403) |
| RATE_LIMIT_EXCEEDED | Dépassement limite requêtes |
| SQL_INJECTION_ATTEMPT | Tentative injection SQL |
| XSS_ATTEMPT | Tentative XSS |
| BRUTE_FORCE_LOGIN | Attaque brute force détectée |
| IP_BLOCKED | IP automatiquement bloquée |

### Format des Logs

```json
{
  "timestamp": "2025-01-15T10:30:00",
  "action": "LOGIN_FAILED",
  "details": "Failed login attempt for user: admin",
  "user_id": null,
  "username": "admin",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "severity": "WARNING"
}
```

### Consultation

Les logs de sécurité sont accessibles :
- Via l'interface web (super admin uniquement)
- Dans les fichiers de log du serveur
- Dans la base de données (LogActivite)

---

## Gestion des IP

### Liste Blanche

Les adresses IP en liste blanche ne peuvent jamais être bloquées.

Configuration via l'interface d'administration :
1. Paramètres → Sécurité
2. Ajouter une IP à la liste blanche

### Blocage d'IP

Blocage automatique après :
- 8 tentatives de connexion échouées
- 15 activités suspectes en 24h

Blocage manuel possible par les administrateurs.

---

## Sauvegarde et Restauration

### Sécurité des Sauvegardes

- Les sauvegardes contiennent les données chiffrées
- Les clés de chiffrement ne sont PAS incluses
- Documentation des variables d'environnement nécessaires

### Export/Import Sécurisé

L'export de courriers :
1. Déchiffre les données avec la clé source
2. Stocke les données en clair dans un ZIP
3. Le ZIP doit être protégé pendant le transport

L'import de courriers :
1. Lit les données en clair du ZIP
2. Re-chiffre avec la clé de destination
3. Stocke de manière sécurisée

---

## Suppression Sécurisée

### Soft Delete

Les courriers supprimés :
- Passent en statut is_deleted=True
- Restent accessibles dans la corbeille
- Conservent leurs données chiffrées

### Suppression Définitive

Réservée aux super administrateurs :
- Suppression des données en base
- Suppression sécurisée des fichiers (3 passes d'écrasement)
- Journalisation de l'opération

---

## Recommandations de Déploiement

### Production

1. **HTTPS obligatoire** : Configurer un certificat SSL/TLS valide
2. **Variables d'environnement** : Ne jamais hardcoder les secrets
3. **Clés uniques** : Générer GEC_MASTER_KEY et GEC_PASSWORD_SALT uniques
4. **Mot de passe admin** : Changer immédiatement après installation
5. **Sauvegardes** : Planifier des sauvegardes régulières
6. **Mises à jour** : Appliquer les correctifs de sécurité

### Réseau

1. Firewall : Autoriser uniquement le port 5000 (ou 443 si reverse proxy)
2. Reverse proxy : Utiliser Nginx/Apache pour HTTPS
3. Base de données : Restreindre l'accès au serveur applicatif uniquement

### Monitoring

1. Surveiller les logs de sécurité
2. Alerter sur les tentatives d'intrusion
3. Auditer les accès régulièrement

---

## Conformité

### RGPD

- Chiffrement des données personnelles
- Droit à l'effacement (suppression définitive)
- Journalisation des accès
- Export des données utilisateur

### Bonnes Pratiques

Le système suit les recommandations :
- OWASP Top 10
- CWE/SANS Top 25
- NIST Cybersecurity Framework

---

## Contact Sécurité

Pour signaler une vulnérabilité :
- Contacter l'administrateur système
- Ne pas divulguer publiquement avant correction
- Fournir les détails techniques pour reproduction
