# GEC — Sécurité & Contrôle d'Accès

*Mise à jour : Avril 2026 — post-audit complet*

---

## 1. Règles inviolables (hardcodées)

### Super Admin — AUCUN accès aux courriers
Le rôle `super_admin` est un **administrateur système** : gestion des utilisateurs, configuration, sécurité, sauvegardes.
Il **ne peut pas** :
- Consulter/lire un courrier
- Créer un courrier
- Modifier un courrier
- Effectuer des actions bulk sur les courriers
- Voir la liste des courriers

Cette règle est codée directement dans `models/user.py` via la constante `_SUPER_ADMIN_MAIL_BLOCKED_PERMISSIONS` et **ne peut pas être contournée** via l'interface ou les rôles RBAC.

```python
# models/user.py — INVIOLABLE
_SUPER_ADMIN_MAIL_BLOCKED_PERMISSIONS = frozenset({
    'read_all_mail', 'read_department_mail', 'read_own_mail',
    'edit_all_mail', 'edit_department_mail', 'edit_own_mail',
    'create_mail', 'delete_mail', 'restore_mail', 'manage_mail',
    'view_all_mail', 'bulk_mail',
})
```

Points de contrôle (5 niveaux) :
1. `has_permission()` → retourne False pour les permissions mail si super_admin
2. `can_view_courrier()` → return False immédiat
3. `can_edit_courrier()` → return False immédiat
4. `can_access_courrier()` → return False immédiat
5. `apply_mail_access_filter()` → `query.filter(False)` (0 résultats)
6. Route `register_mail` → redirect dashboard + log ACCES_REFUSE

---

## 2. Expiration de session automatique (1 heure)

- **Durée maximale** : 1 heure après connexion (absolue, indépendante de l'inactivité)
- **Mécanisme** : `session['login_at']` (timestamp UNIX) stocké à la connexion
- **Vérification** : `@app.before_request` dans `routes/auth.py` — toute requête authentifiée vérifie l'expiration
- **Action** : `logout_user()` + `session.clear()` + log `AUTO_DECONNEXION` + redirect login
- **Durée cookie** : 7 jours max, mais invalidée par before_request après 1h

---

## 3. Cookies de session

| Paramètre | Valeur | Protection |
|---|---|---|
| `SESSION_COOKIE_HTTPONLY` | `True` | Cookie inaccessible au JavaScript (XSS) |
| `SESSION_COOKIE_SECURE` | `True` en production | Cookie transmis HTTPS uniquement |
| `SESSION_COOKIE_SAMESITE` | `'Lax'` | Protection CSRF cross-site |
| Durée maximale | 7 jours | Réduction de 30 → 7 jours |

---

## 4. IP réelle dans les logs

Nginx → Flask via `X-Forwarded-For` validé par proxy de confiance.

**Config `app.py`** :
```python
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
```

`log_activity()` et `log_courrier_modification()` utilisent `get_client_ip()` de `security/auth.py` qui :
1. Vérifie que `REMOTE_ADDR` est un proxy de confiance (liste `TRUSTED_PROXIES`)
2. Extrait le premier IP non-privé/non-loopback de la chaîne `X-Forwarded-For`
3. Rejette les IPs spoofées si le peer n'est pas de confiance

Variable d'environnement : `TRUSTED_PROXIES=127.0.0.1,::1` (défaut)

---

## 5. Matrice des permissions par rôle

| Action | super_admin | admin | user |
|---|---|---|---|
| Gérer les utilisateurs | ✅ | ❌ | ❌ |
| Configurer le système | ✅ | ❌ | ❌ |
| Gérer les sauvegardes | ✅ | ❌ | ❌ |
| Consulter les logs | ✅ | ❌ | ❌ |
| Gérer la sécurité | ✅ | ❌ | ❌ |
| **Créer un courrier** | **❌ BLOQUÉ** | ✅ | ✅ (si permission) |
| **Lire un courrier** | **❌ BLOQUÉ** | ✅ | ✅ (si permission) |
| **Modifier un courrier** | **❌ BLOQUÉ** | ✅ | ✅ (propre, 24h) |
| **Supprimer un courrier** | **❌ BLOQUÉ** | ✅ (si permission) | ❌ |
| Gérer les statuts | ❌ | ✅ | ❌ |
| Gérer les rôles/permissions | ✅ | ❌ | ❌ |
| Gérer les départements | ✅ | ❌ | ❌ |

---

## 6. Audit trail — Actions loggées

Toutes les actions dans `LogActivite` avec : `utilisateur_id`, `action`, `description`, `ip_address`, `date_action`, `courrier_id`.

### Authentification
`CONNEXION` · `CONNEXION_2FA` · `DECONNEXION` · `AUTO_DECONNEXION` · `2FA_ENABLED` · `2FA_DISABLED` · `ACCES_REFUSE`

### Navigation
`NAVIGATION_DASHBOARD` · `NAVIGATION_LISTE_COURRIERS` (filtres loggés) · `NAVIGATION_KANBAN` · `NAVIGATION_RECHERCHE` · `RECHERCHE_COURRIER` (termes loggés) · `NAVIGATION_ANALYTIQUE`

### Courriers
`ENREGISTREMENT_COURRIER` · `CONSULTATION_COURRIER` · `MODIFICATION_COURRIER` · `CHANGEMENT_STATUT` · `SUPPRESSION_COURRIER` · `RESTAURATION_COURRIER` · `CONSULTATION_CORBEILLE` · `VIDAGE_CORBEILLE` · `BULK_STATUT` · `BULK_DELETE` · `SET_DUE_DATE`

### Fichiers
`TELECHARGEMENT_FICHIER` · `TELECHARGEMENT_PIECE_JOINTE` · `VISUALISATION_FICHIER` · `UPLOAD_PIECES_JOINTES` · `UPLOAD_TRANSMISSION_FILE`

### Transmissions & Signatures
`TRANSMISSION_COURRIER` · `DOWNLOAD_TRANSMISSION_FILE` · `CIRCUIT_SIGNATURE_INIT` · `SIGNATURE_APPROVED` · `SIGNATURE_REJECTED`

### Sécurité système
`LOGIN_BLOCKED` · `LOGIN_FAILED` · `SECURITY_SETTINGS` · `SECURITY_UNBLOCK` · `SECURITY_WHITELIST` · `SECURITY_CONFIG`

---

## 7. Chiffrement des données

### Champs DB (AES-256-CBC, PBKDF2-HMAC-SHA256, 100k itérations)

Chiffré dans `User` : `email_encrypted`, `nom_complet_encrypted`, `matricule_encrypted`, `fonction_encrypted`

Chiffré dans `Courrier` : `objet_encrypted`, `expediteur_encrypted`, `destinataire_encrypted`, `numero_reference_encrypted`

Clé maître : variable d'environnement `GEC_MASTER_KEY` (obligatoire en production).

### Fichiers uploadés
Stockés dans `uploads/`. La fonction `encrypt_uploaded_file()` existe dans `security/encryption.py` — activation prévue.

---

## 8. Protections anti-attaque

| Menace | Protection |
|---|---|
| Brute force login | Rate limit 8 tentatives → blocage IP 15 min |
| CSRF | Flask-WTF sur tous les POST |
| SQL Injection | ORM SQLAlchemy (requêtes paramétrées) + détection patterns |
| XSS | Jinja2 auto-escape + patterns de détection |
| Path traversal | `os.path.realpath()` sur tous les téléchargements |
| Session hijacking | HTTPONLY + SECURE + SAMESITE + expiration 1h |
| 2FA bypass | TOTP (pyotp) disponible pour super_admin |
| IP spoofing | get_client_ip() valide le proxy avant de lire X-Forwarded-For |
