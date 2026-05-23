# GEC — Contexte Domaine Approfondi

> Ce fichier contient tout ce qui ne se dérive pas du code :
> le métier, les règles implicites, le contexte client.

---

## Qu'est-ce que GEC ?

**GEC** (Gestion Électronique du Courrier) est un logiciel propriétaire MOA Digital Agency.
Il sert à dématérialiser et tracer tous les flux de courrier (entrant et sortant) d'une administration ou entreprise.

**Cible principale** : administrations publiques africaines (RDC en priorité).
**Contexte réglementaire** : besoin de traçabilité stricte, d'audit, et de sécurité des données sensibles.

---

## Flux Métier Courrier

### Courrier Entrant (ENTRANT)
1. Agent reçoit un courrier physique ou numérique
2. L'enregistre dans GEC : expéditeur, objet, date, fichier joint optionnel
3. Numéro d'accusé de réception généré automatiquement (ex. `GEC-2025-00042`)
4. Statut initial : **RECU**
5. Peut être transmis à un autre agent (`CourrierForward`)
6. Passage de statut : RECU → EN_COURS → TRAITE → ARCHIVE
7. Statut spécial **URGENT** possible à tout moment

### Courrier Sortant (SORTANT)
1. Agent rédige/enregistre un courrier à envoyer
2. Champs : destinataire, type (Note circulaire, Lettre, Mémorandum...), objet, date d'émission
3. Même cycle de statuts qu'entrant

### Transmission (Forward)
- N'importe quel utilisateur autorisé peut transmettre un courrier à un collègue
- Crée un `CourrierForward` + une `Notification` pour le destinataire
- Le destinataire d'une transmission peut accéder au courrier même si son rôle ne le permettrait pas normalement (exception dans `can_view_courrier()`)
- Email de notification envoyé si configuré

---

## Règles d'Accès — Logique Critique

La visibilité des courriers suit cette hiérarchie (cf. `User.can_view_courrier()`) :

```
super_admin  → AUCUN accès aux courriers (INVIOLABLE — _SUPER_ADMIN_MAIL_BLOCKED_PERMISSIONS)
admin        → voit les courriers de SON département
user         → voit SEULEMENT ses propres courriers
```

**Exception** : si un courrier a été transmis à un utilisateur, cet utilisateur peut le voir quelle que soit sa permission de base. Logique dans `apply_mail_access_filter()`.

---

## Signature Électronique Non-Répudiation (ajoutée mai 2026)

### Principe

Chaque action sur un courrier génère une entrée `CourrierActionSignature` avec :
- **Hash SHA-256** : `SHA256(timestamp|user_id|action_type|courrier_id|details|previous_hash)`
- **previous_hash** : hash de l'entrée précédente → chaîne infalsifiable
- **Snapshots immuables** : `user_nom` + `user_role` au moment de l'action (même si l'utilisateur est modifié/supprimé après)
- **IP address** : adresse IP réelle (via ProxyFix + get_client_ip())

### Pourquoi c'est non-falsifiable

Modifier rétroactivement une entrée invalide son hash. Modifier le hash invalide le `previous_hash` de l'entrée suivante, et ainsi de suite. La chaîne entière s'effondre. Vérifiable via `GET /api/courrier/<id>/verify_signatures`.

### Actions couvertes

CREATION · MODIF_STATUT · MODIF_CHAMP · TRANSMISSION · COMMENTAIRE · ANNOTATION · INSTRUCTION · TELECHARGEMENT · VISUALISATION · SIGNATURE · REJET · SUPPRESSION · RESTAURATION · CIRCUIT_INIT

### Affichage

Section "Historique Signé" dans `mail_detail_new.html` — timeline verticale avec badge couleur, hash tronqué (8 chars) + tooltip, bouton AJAX de vérification d'intégrité.

---

## Sécurité — Chiffrement

### AES-256-GCM v2 (depuis mai 2026)

**Fichiers joints chiffrés** (format binaire) :
```
Magic 4 bytes : b'GEC2'
Nonce 12 bytes (GCM)
Tag 16 bytes (authenticité + intégrité)
Ciphertext (variable)
```
Détection : `file.read(4) == b'GEC2'` → v2 GCM. Sinon → v1 CBC (backward-compat).

**Champs DB chiffrés** (`objet_encrypted`, `expediteur_encrypted`, etc.) :
Format v2 : `v2:base64(nonce+tag+ciphertext)`. Format v1 : raw base64 sans préfixe.

**Avantage GCM vs CBC** : GCM authentifie le chiffré (tag de 16 bytes). Une modification du chiffré est détectable immédiatement au déchiffrement. CBC ne protège pas l'intégrité.

**Fail-fast** : si `GEC_MASTER_KEY` absente au démarrage → log CRITICAL + exception. Jamais de clé volatile en RAM (les données chiffrées deviendraient illisibles au redémarrage).

### Audit Log

Toutes les actions importantes génèrent un `LogActivite`.
Les events de sécurité (tentatives échouées, IP bloquées) sont dans `security.auth.audit_log()`.

### Blocage IP

Après X tentatives de connexion échouées → IP bloquée automatiquement (durée configurable).
Table `IPBlock` — whitelist dans `IPWhitelist`.

### Headers de sécurité

Injectés via `add_security_headers()` dans `after_request` (CSP, X-Frame-Options, etc.).

---

## Paramétrage Organisationnel

GEC est pensé pour être déployé pour différents types d'organisations :
- Le terme "Département" est configurable (peut devenir "Direction", "Service", "Division")
- Le titre du responsable est configurable : "Secrétaire Général", "Directeur", etc.
- Le format du numéro d'accusé est configurable : `GEC-{year}-{counter:05d}`
- Le logo, l'entête PDF, le pays sont tous paramétrables via `ParametresSysteme`

---

## Notifications Email

Deux événements déclenchent un email :
1. Nouveau courrier enregistré → notifie les admins/super_admin configurés
2. Courrier transmis → notifie le destinataire
3. Commentaire ajouté → notifie les participants (`send_comment_notification`)

Templates configurables en base (`EmailTemplate`). Providers : **Resend** (`re_xxx`) ou **SMTP**.

---

## PWA (ajoutée mai 2026)

GEC est installable comme application native sur mobile/desktop :
- `static/manifest.json` : métadonnées, icônes, start_url `/dashboard`
- `static/js/sw.js` : cache offline pour les assets statiques, network-first pour les pages HTML
- Icônes SVG 192px + 512px (bleu-indigo gradient, enveloppe)

Cas d'usage : agents terrain sans connexion stable → accès aux dernières pages visitées en mode offline.

---

## Déploiement en Production

- VPS 2 : `168.231.86.201` — `/var/websites/gec` — port `5004`
- Process manager : PM2 (nom PM2 : `gec`)
- Reverse proxy : Nginx (HTTPS)
- SSH : `ssh -i ~/.ssh/vps1_access root@168.231.86.201`
- Workflow : **jamais éditer sur le VPS** — toujours local → GitHub → `git pull` VPS

**Migration DB en attente** (mai 2026) :
```bash
flask db migrate -m "add courrier_action_signature and fichier_encrypted"
flask db upgrade
```

---

## Historique Produit

- **Avril 2026** : Redesign UX complet (design system gec-*, sidebar accordéon, skeleton, dark theme)
- **Mai 2026** : AES-256-GCM v2, signature électronique non-répudiation, PWA, skeleton loading, bugs B1-B7 fixés
- **Sept 2025** : Multilingue FR/EN, backup/restore PostgreSQL, templates email dynamiques, Resend API, 2FA TOTP
