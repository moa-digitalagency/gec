# Journal des Modifications (CHANGELOG)

---

## [v2.2.0] - Juillet 2026 — Évolutions DPEM (Réf. MOA/CD/KIN/06003/2026)

Intégration des 6 évolutions demandées par la Direction de Protection de l'Environnement Minier (DPEM) dans sa lettre du 18/06/2026, sans régression sur l'existant (chiffrement AES-256-GCM, RBAC, signature de non-répudiation).

### Fonctionnalités
- **Statut figé à l'enregistrement** : un seul statut initial (`RECU`) est désormais imposé côté serveur à la création d'un courrier ; les statuts suivants restent gérés lors du traitement (`edit_courrier`, `change_status`). Le sélecteur de statut a été retiré du formulaire d'enregistrement au profit d'un affichage lecture seule.
- **Annotation du Directeur** : nouveau type de commentaire `annotation_directeur`, réservé aux porteurs de la permission dédiée `add_director_annotation` (non attribuée par défaut, à assigner via l'éditeur de rôles). Une seule annotation active par courrier — un second dépôt met à jour la précédente au lieu d'en créer une nouvelle. Affichée dans un bloc distinct sur la fiche courrier.
- **Pièces jointes sur commentaires et annotations** : ajout d'un fichier (PDF ou image) optionnel sur tout commentaire/annotation, chiffré (AES-256-GCM) comme les autres pièces jointes du système, avec route de téléchargement dédiée protégée par le même contrôle d'accès anti-IDOR que le courrier parent (`can_view_courrier`).
- **Courrier sortant adossé au courrier entrant** : depuis la fiche d'un courrier entrant, un bouton « Générer un courrier sortant lié » ouvre le formulaire d'enregistrement pré-rempli (destinataire = expéditeur du parent) ; le lien (`courrier_parent_id`) est conservé à la création et affiché en cross-lien sur les deux fiches, avec vérification d'accès sur le parent (anti-fuite).
- **Date d'enregistrement modifiable (RBAC)** : nouvelle permission `edit_registration_date` (attribuée par défaut au rôle `admin`, révocable) permettant de corriger manuellement la date d'enregistrement d'un courrier depuis `edit_courrier` ; modification journalisée et signée électroniquement.
- **Numéro de suivi + étiquette QR** : chaque courrier reçoit à la création un numéro de suivi court et unique (format `SUIVI-{année}-{compteur:05d}`) ; une étiquette imprimable dédiée (numéro de suivi + QR code encodant ce numéro) est accessible depuis la fiche courrier, et la recherche retrouve désormais un dossier par ce numéro (y compris par scan).

### Technique
- Nouvelles colonnes (migration automatique idempotente, dev SQLite + prod PostgreSQL) : `courrier.courrier_parent_id`, `courrier.numero_suivi`, et 5 colonnes de pièce jointe sur `courrier_comment` (`fichier_nom`, `fichier_chemin`, `fichier_type`, `fichier_taille`, `fichier_encrypted`).
- 3 nouveaux types d'action signée (non-répudiation) : `ANNOTATION_DIRECTEUR`, `MODIF_DATE_ENREG`, `GEN_SORTANT`.
- 2 nouvelles permissions au catalogue RBAC (`add_director_annotation`, `edit_registration_date`), ajoutées à `_SUPER_ADMIN_MAIL_BLOCKED_PERMISSIONS` (le super_admin reste inviolablement exclu du courrier).
- Internationalisation complète des nouveaux libellés (`lang/fr.json` / `lang/en.json`) dans `register_mail.html`, `mail_detail_new.html`, `edit_courrier.html` et `etiquette_courrier.html`.

---

## [v2.1.0] - Avril 2026 — Sécurité + UX Redesign

### Sécurité critique
- **Super admin bloqué des courriers (INVIOLABLE)** : `_SUPER_ADMIN_MAIL_BLOCKED_PERMISSIONS` hardcodé dans `models/user.py` — 5 niveaux de contrôle (has_permission, can_view, can_edit, can_access, apply_mail_access_filter). Route `register_mail` bloque et logue la tentative.
- **IP réelle dans les logs** : `log_activity()` utilise désormais `get_client_ip()` de `security/auth.py` (validation proxy de confiance, anti-spoofing). `ProxyFix(x_for=1)` ajouté dans `app.py`.
- **Auto-logout 1h** : `@app.before_request` vérifie `session['login_at']` — déconnexion automatique après 3600s avec log `AUTO_DECONNEXION`.
- **Cookies session** : `HTTPONLY=True`, `SECURE=True` (prod), `SAMESITE=Lax`, durée réduite 30j → 7j.

### Logs étendus
- Navigation loggée : `NAVIGATION_DASHBOARD`, `NAVIGATION_LISTE_COURRIERS` (filtres inclus), `NAVIGATION_KANBAN`, `NAVIGATION_RECHERCHE` / `RECHERCHE_COURRIER` (termes inclus), `NAVIGATION_ANALYTIQUE`.
- `UPLOAD_PIECES_JOINTES` : log des noms de fichiers supplémentaires à l'enregistrement.

### UX / Interface
- **Sidebar** : groupes accordéon collapsibles (Structure, Paramètres courriers, Email, Sécurité & Logs, Infrastructure) avec auto-ouverture sur la page courante.
- **Paramètres** : navigation par onglets (Identité / Terminologie / Numérotation / PDF / Email) avec persistence localStorage.
- **Upload files** : zone "Pièces jointes supplémentaires" refaite avec `gec-upload-zone` (drag & drop, DataTransfer API, liste dynamique).
- **Statuts DB** : `EN_COURS`, `RECU`, etc. traduits en français partout via `.replace('_',' ')|title` (dashboard, view_mail, edit_courrier, search).
- **Breadcrumbs** : ajoutés à `notifications.html` et `logs.html`.
- **Sidebar** : ajout "Contacts" (`senders_list`) et accordéon "Exports" (PDF + Excel).
- Fix `url_for('kanban')` → `url_for('kanban_view')` (BuildError corrigé).

---

## [v2.0.0] - Avril 2026 — Refonte UI complète

- Nouveau design system `static/css/design-system.css` avec classes `gec-*`
- `mail_detail_new.html` : réécriture complète, tout le JS préservé (tags, circuit de signature, timeline, user search dropdown)
- Nouveau `new_base.html` : sidebar dark theme, topbar, dark mode toggle

---

## [Correction Import de Courriers - Affichage des Erreurs] - 2025-10-15

### Correction Critique - Import/Export

**Problème** : L'import de courriers affichait "0 courriers importés" et "2 erreurs rencontrées" mais sans détails sur les erreurs.

**Causes identifiées** :
- Mauvaise gestion des exceptions dans le parseur CSV/Excel
- Les erreurs de validation étaient silencieusement avalées

**Correction** : Propagation correcte des messages d'erreur vers le template + affichage détaillé par ligne.
