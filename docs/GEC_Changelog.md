# Journal des Modifications (CHANGELOG)

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
