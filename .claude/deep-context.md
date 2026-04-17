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
4. Pas d'expéditeur (c'est l'organisme lui-même)

### Transmission (Forward)
- N'importe quel utilisateur autorisé peut transmettre un courrier à un collègue
- Crée un `CourrierForward` + une `Notification` pour le destinataire
- Le destinataire d'une transmission peut accéder au courrier même si son rôle ne le permettrait pas normalement (exception dans `can_view_courrier()`)
- Email de notification envoyé si configuré

---

## Règles d'Accès — Logique Critique

La visibilité des courriers suit cette hiérarchie (cf. `User.can_view_courrier()`) :

```
super_admin  → voit TOUT
admin        → voit les courriers de SON département
user         → voit SEULEMENT ses propres courriers
```

**Exception critique** : si un courrier a été transmis (`CourrierForward`) à un utilisateur,  
cet utilisateur peut le voir QUELLE QUE SOIT sa permission de base.  
Cette logique est dans `apply_mail_access_filter()` dans `views.py`.

---

## Paramétrage Organisationnel

GEC est pensé pour être déployé pour différents types d'organisations :
- Le terme "Département" est configurable (peut devenir "Direction", "Service", "Division")
- Le titre du responsable est configurable : "Secrétaire Général", "Directeur", etc.
- Le format du numéro d'accusé est configurable : `GEC-{year}-{counter:05d}`
- Le logo, l'entête PDF, le pays sont tous paramétrables via `ParametresSysteme`

---

## Sécurité — Points Importants

### Chiffrement des données sensibles
Certains champs sont stockés **en double** : en clair (compatibilité) + chiffré AES-256.  
Colonnes chiffrées : `email_encrypted`, `nom_complet_encrypted`, `objet_encrypted`, `expediteur_encrypted`, etc.  
Clé de chiffrement : variable `GEC_MASTER_KEY` (jamais en dur).

### Audit Log
Toutes les actions importantes génèrent un `LogActivite`.  
Les events de sécurité (tentatives échouées, IP bloquées) sont dans `security_utils.audit_log()`.

### Blocage IP
Après X tentatives de connexion échouées → IP bloquée automatiquement (durée configurable).  
Table `IPBlock` — whitelist dans `IPWhitelist`.

### Headers de sécurité
Injectés via `add_security_headers()` dans `after_request` (CSP, X-Frame-Options, etc.).

---

## Numérotation des Courriers

Deux modes :
- **Automatique** : compteur auto par année, format configurable
- **Manuel** : l'agent saisit lui-même le numéro

La logique est dans `utils.generate_accuse_reception()`.

---

## Notifications Email

Deux événements déclenchent un email :
1. Nouveau courrier enregistré → notifie les admins/super_admin configurés
2. Courrier transmis → notifie le destinataire de la transmission

Templates configurables en base (`EmailTemplate`) avec variables dynamiques `{{nom_variable}}`.  
Deux providers : **Resend** (API key `re_xxx`) ou **SMTP** classique — choix dans `ParametresSysteme`.

---

## Déploiement en Production

- VPS 2 : `168.231.86.201` — `/var/websites/gec` — port `5004`
- Process manager : PM2
- Reverse proxy : Nginx (HTTPS)
- SSH : `ssh -i ~/.ssh/vps1_access root@168.231.86.201`
- Workflow : **jamais éditer sur le VPS** — toujours local → GitHub → `git pull` VPS

---

## Historique Produit (depuis requirements.txt)

Fonctionnalités ajoutées en septembre 2025 :
- Multilingue FR/EN complet
- Backup/restore PostgreSQL
- Mise à jour système en ligne (Git) et hors ligne (ZIP)
- Templates email dynamiques multi-langues
- Autocomplete de recherche
- Support Resend API
