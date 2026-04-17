# 2FA TOTP — Guide d'implémentation Flask

> Implémentation complète de la double authentification TOTP (Time-based One-Time Password)
> pour une application Flask. Basé sur le projet GEC-Courrier (Avril 2026).

---

## Sommaire

1. [Dépendances](#1-dépendances)
2. [Migration base de données](#2-migration-base-de-données)
3. [Modèle User — colonnes et méthodes](#3-modèle-user--colonnes-et-méthodes)
4. [Intégration dans la route login](#4-intégration-dans-la-route-login)
5. [Route — Vérification TOTP (`/verify_2fa`)](#5-route--vérification-totp-verify_2fa)
6. [Route — Activation 2FA (`/profile/2fa/setup`)](#6-route--activation-2fa-profile2fasetup)
7. [Route — Désactivation 2FA (`/profile/2fa/disable`)](#7-route--désactivation-2fa-profile2fadisable)
8. [Template — Page de vérification (`verify_2fa.html`)](#8-template--page-de-vérification-verify_2fahtml)
9. [Template — Page d'activation (`setup_2fa.html`)](#9-template--page-dactivation-setup_2fahtml)
10. [Profil utilisateur — Boutons d'activation/désactivation](#10-profil-utilisateur--boutons-dactivationdésactivation)
11. [Sécurité — Points critiques](#11-sécurité--points-critiques)

---

## 1. Dépendances

```
pyotp==2.9.0
qrcode[pil]==8.0
```

```bash
pip install pyotp "qrcode[pil]"
```

- **pyotp** — génère les secrets TOTP, vérifie les codes
- **qrcode[pil]** — crée les QR codes en image PNG (nécessite Pillow)

---

## 2. Migration base de données

Ajouter 3 colonnes à la table `users` :

```python
# Dans utils/migrations.py ou un fichier de migration Alembic

def add_2fa_columns():
    """Ajoute les colonnes 2FA TOTP à la table users"""
    import psycopg2  # ou sqlite3 selon votre DB
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    migrations = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(64)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_pending_secret VARCHAR(64)",
    ]

    for sql in migrations:
        try:
            cur.execute(sql)
            conn.commit()
            print(f"OK: {sql}")
        except Exception as e:
            conn.rollback()
            print(f"SKIP (already exists?): {e}")

    cur.close()
    conn.close()
```

**Explication des 3 colonnes** :

| Colonne | Type | Rôle |
|---|---|---|
| `totp_secret` | VARCHAR(64) | Secret TOTP actif (confirmé, utilisé pour vérifier les codes) |
| `totp_enabled` | BOOLEAN | `True` si la 2FA est activée sur ce compte |
| `totp_pending_secret` | VARCHAR(64) | Secret temporaire généré mais pas encore confirmé |

> **Pourquoi `totp_pending_secret` ?**
> Le secret est généré sur la page de setup et stocké dans `totp_pending_secret`.
> Il ne devient `totp_secret` (actif) qu'une fois que l'utilisateur a confirmé qu'il peut
> générer un code valide. Cela évite d'activer la 2FA avec un QR code que l'utilisateur
> n'a pas réellement scanné.

---

## 3. Modèle User — colonnes et méthodes

```python
from extensions import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    # ... autres colonnes existantes ...

    # 2FA TOTP
    totp_secret = db.Column(db.String(64), nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False, nullable=False)
    totp_pending_secret = db.Column(db.String(64), nullable=True)

    def get_totp_uri(self, issuer='MonApp'):
        """Génère l'URI otpauth:// pour le QR code"""
        import pyotp
        secret = self.totp_pending_secret or self.totp_secret
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=self.email,
            issuer_name=issuer
        )

    def verify_totp(self, token):
        """Vérifie un code TOTP saisi par l'utilisateur"""
        import pyotp
        if not self.totp_enabled or not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(token, valid_window=1)
        # valid_window=1 : accepte le code précédent et le suivant
        # (compense les décalages d'horloge de ±30s)
```

---

## 4. Intégration dans la route login

Après vérification du mot de passe, intercepter si la 2FA est activée :

```python
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.actif:

            # ── 2FA check ──────────────────────────────────────────
            if user.totp_enabled and user.totp_secret:
                session['2fa_pending_user_id'] = user.id
                session['2fa_next'] = request.args.get('next', '')
                return redirect(url_for('verify_2fa'))
            # ────────────────────────────────────────────────────────

            # Connexion normale (sans 2FA)
            login_user(user)
            import time
            session['last_activity'] = time.time()
            return redirect(url_for('dashboard'))

        flash('Identifiants incorrects.', 'error')

    return render_template('login.html')
```

**Points importants** :
- L'utilisateur n'est **pas** connecté (`login_user` n'est pas appelé) — il est en attente
- Son `id` est stocké dans `session['2fa_pending_user_id']` (pas dans la session Flask-Login)
- `session['2fa_next']` conserve l'URL de redirection post-login si elle existe

---

## 5. Route — Vérification TOTP (`/verify_2fa`)

```python
@app.route('/verify_2fa', methods=['GET', 'POST'])
def verify_2fa():
    """Étape de vérification TOTP après le mot de passe"""
    pending_id = session.get('2fa_pending_user_id')
    if not pending_id:
        return redirect(url_for('login'))

    user = User.query.get(pending_id)
    if not user:
        session.pop('2fa_pending_user_id', None)
        return redirect(url_for('login'))

    error = None
    if request.method == 'POST':
        # Nettoyer le token : retirer espaces (formatage auto du template)
        token = request.form.get('token', '').strip().replace(' ', '')

        if user.verify_totp(token):
            # Succès — finaliser la connexion
            session.pop('2fa_pending_user_id', None)
            next_url = session.pop('2fa_next', '')
            login_user(user)
            import time
            session['last_activity'] = time.time()
            flash('Connexion réussie!', 'success')
            if next_url:
                return redirect(next_url)  # utiliser secure_redirect() si disponible
            return redirect(url_for('dashboard'))
        else:
            error = 'Code invalide. Réessayez.'

    return render_template('verify_2fa.html', error=error)
```

---

## 6. Route — Activation 2FA (`/profile/2fa/setup`)

```python
@app.route('/profile/2fa/setup', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    """Activation de la 2FA — restreindre aux rôles autorisés selon le projet"""
    # Adapter cette restriction au projet :
    # if current_user.role != 'super_admin': abort(403)    ← GEC
    # if not current_user.is_admin: abort(403)             ← autre app
    # (ou supprimer la restriction pour tous les utilisateurs)

    import pyotp, qrcode, io, base64

    if request.method == 'POST':
        token = request.form.get('token', '').strip().replace(' ', '')
        pending = current_user.totp_pending_secret

        if not pending:
            flash('Session expirée, recommencez.', 'error')
            return redirect(url_for('setup_2fa'))

        totp = pyotp.TOTP(pending)
        if totp.verify(token, valid_window=1):
            # Confirmer l'activation — le pending devient le secret actif
            current_user.totp_secret = pending
            current_user.totp_pending_secret = None
            current_user.totp_enabled = True
            db.session.commit()
            flash('Double authentification activée avec succès.', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Code incorrect. Réessayez.', 'error')
            return redirect(url_for('setup_2fa'))

    # GET — générer un nouveau secret pending (chaque visite génère un nouveau)
    secret = pyotp.random_base32()
    current_user.totp_pending_secret = secret
    db.session.commit()

    # Générer l'URI otpauth:// et le QR code
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name='MonApp'  # ← nom affiché dans Google Authenticator
    )

    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return render_template('setup_2fa.html', qr_b64=qr_b64, secret=secret)
```

---

## 7. Route — Désactivation 2FA (`/profile/2fa/disable`)

```python
@app.route('/profile/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    """Désactiver la 2FA — exige le code TOTP actuel pour confirmer"""
    # Même restriction de rôle que setup_2fa

    token = request.form.get('token', '').strip().replace(' ', '')
    if not current_user.verify_totp(token):
        flash("Code incorrect. La 2FA n'a pas été désactivée.", 'error')
        return redirect(url_for('profile'))

    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.totp_pending_secret = None
    db.session.commit()
    flash('Double authentification désactivée.', 'info')
    return redirect(url_for('profile'))
```

> **Important** : toujours exiger un code TOTP valide pour désactiver la 2FA.
> Ne pas permettre la désactivation par mot de passe seul (risque si session volée).

---

## 8. Template — Page de vérification (`verify_2fa.html`)

Page **autonome** (ne pas étendre `base.html` — l'utilisateur n'est pas encore connecté,
la sidebar/navbar n'existent pas encore).

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vérification 2FA</title>
  <!-- Vos CSS habituels -->
  <style>
    body {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
      background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #312e81 100%);
    }
    .auth-card {
      width: 100%;
      max-width: 420px;
      background: var(--card-bg, #fff);
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 25px 50px rgba(0,0,0,.4);
    }
    .totp-input {
      width: 100%;
      text-align: center;
      font-size: 2rem;
      font-family: monospace;
      font-weight: 700;
      letter-spacing: .5rem;
      padding: .875rem 1rem;
      border: 2px solid #e2e8f0;
      border-radius: 8px;
      outline: none;
      box-sizing: border-box;
    }
    .totp-input:focus { border-color: #3b82f6; }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
  </style>
</head>
<body>
<div class="auth-card">

  <!-- Header gradient -->
  <div style="background:linear-gradient(135deg,#3b82f6,#1e3a8a);padding:2rem;text-align:center;">
    <div style="width:64px;height:64px;border-radius:50%;background:rgba(255,255,255,.15);
                display:flex;align-items:center;justify-content:center;margin:0 auto 1rem;">
      <i class="fas fa-shield-alt" style="color:white;font-size:1.75rem;"></i>
    </div>
    <h1 style="font-size:1.125rem;font-weight:700;color:white;margin-bottom:.375rem;">Double Authentification</h1>
    <p style="font-size:.8125rem;color:rgba(255,255,255,.75);">
      Saisissez le code à 6 chiffres de votre application d'authentification
    </p>
  </div>

  <div style="padding:2rem;display:flex;flex-direction:column;gap:1.25rem;">

    {% if error %}
    <div style="background:#fef2f2;border:1px solid #fecaca;color:#991b1b;padding:.75rem 1rem;border-radius:8px;">
      {{ error }}
    </div>
    {% endif %}

    <form method="POST" autocomplete="off" style="display:flex;flex-direction:column;gap:1rem;">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

      <div>
        <label style="display:block;font-size:.8125rem;font-weight:600;color:#475569;
                      margin-bottom:.5rem;text-align:center;">Code TOTP</label>
        <input type="text" name="token"
               inputmode="numeric"
               pattern="[0-9 ]{6,7}"
               maxlength="7"
               autofocus
               autocomplete="one-time-code"
               placeholder="000 000"
               class="totp-input">
        <div style="text-align:center;margin-top:.5rem;font-size:.75rem;color:#94a3b8;">
          <i class="fas fa-sync-alt" style="animation:spin 30s linear infinite;"></i>
          Le code se renouvelle toutes les 30 secondes
        </div>
      </div>

      <button type="submit"
              style="width:100%;padding:.875rem;background:#3b82f6;color:white;
                     border:none;border-radius:8px;font-size:.9375rem;font-weight:600;
                     cursor:pointer;">
        Vérifier le code
      </button>
    </form>

    <div style="text-align:center;">
      <a href="{{ url_for('login') }}" style="font-size:.8125rem;color:rgba(255,255,255,.6);">
        ← Retour à la connexion
      </a>
    </div>

  </div>
</div>

<script>
// Auto-format : ajoute un espace après le 3e chiffre (affichage "000 000")
document.querySelector('input[name="token"]')?.addEventListener('input', function() {
  let v = this.value.replace(/\D/g, '').slice(0, 6);
  this.value = v.length > 3 ? v.slice(0,3) + ' ' + v.slice(3) : v;
});
</script>
</body>
</html>
```

**Notes** :
- `inputmode="numeric"` — clavier numérique sur mobile
- `autocomplete="one-time-code"` — déclenche l'auto-remplissage SMS/TOTP sur iOS/Android
- Le JS retire les espaces côté template ; la route fait aussi `.replace(' ', '')` côté serveur

---

## 9. Template — Page d'activation (`setup_2fa.html`)

Cette page **étend** `base.html` (l'utilisateur est déjà connecté).

```html
{% extends "base.html" %}
{% block content %}
<div style="max-width:480px;margin:0 auto;">

  <div style="background:white;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#3b82f6,#1e3a8a);padding:1.75rem;text-align:center;">
      <h1 style="color:white;font-size:1.125rem;font-weight:700;">Activer la Double Authentification</h1>
      <p style="color:rgba(255,255,255,.75);font-size:.8125rem;">
        Renforcez la sécurité de votre compte avec une application TOTP
      </p>
    </div>

    <div style="padding:1.5rem;display:flex;flex-direction:column;gap:1.5rem;">

      <!-- Étape 1 : Scanner le QR code -->
      <div>
        <h2 style="font-size:.9375rem;font-weight:600;">1. Scannez ce QR code</h2>
        <p style="font-size:.8125rem;color:#64748b;">
          Avec Google Authenticator, Authy ou toute app TOTP compatible
        </p>
        <div style="display:flex;justify-content:center;margin-top:1rem;">
          <div style="padding:.75rem;background:white;border:2px solid #e2e8f0;border-radius:8px;">
            <img src="data:image/png;base64,{{ qr_b64 }}"
                 alt="QR Code 2FA"
                 style="width:176px;height:176px;display:block;">
          </div>
        </div>

        <!-- Fallback : code manuel -->
        <details style="margin-top:.875rem;">
          <summary style="font-size:.8125rem;color:#64748b;cursor:pointer;text-align:center;">
            Impossible de scanner ? Entrer le code manuellement
          </summary>
          <div style="margin-top:.625rem;background:#f8fafc;border:1px solid #e2e8f0;
                      border-radius:8px;padding:.875rem;">
            <div style="font-size:.75rem;color:#64748b;margin-bottom:.375rem;">Secret (base32) :</div>
            <code style="font-size:.875rem;font-family:monospace;font-weight:700;word-break:break-all;">
              {{ secret }}
            </code>
          </div>
        </details>
      </div>

      <hr style="border:none;border-top:1px solid #e2e8f0;">

      <!-- Étape 2 : Confirmer le code -->
      <div>
        <h2 style="font-size:.9375rem;font-weight:600;">2. Confirmez le code affiché</h2>

        <form method="POST" autocomplete="off" style="display:flex;flex-direction:column;gap:1rem;margin-top:1rem;">
          <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

          <input type="text" name="token"
                 id="token"
                 inputmode="numeric"
                 pattern="[0-9 ]{6,7}"
                 maxlength="7"
                 autofocus
                 autocomplete="one-time-code"
                 placeholder="000 000"
                 style="width:100%;text-align:center;font-size:1.75rem;font-weight:700;
                        letter-spacing:.375rem;font-family:monospace;padding:.875rem;
                        border:2px solid #e2e8f0;border-radius:8px;box-sizing:border-box;">

          <p style="font-size:.75rem;color:#94a3b8;text-align:center;margin:0;">
            Le code se renouvelle toutes les 30 secondes
          </p>

          <button type="submit"
                  style="width:100%;padding:.875rem;background:#3b82f6;color:white;
                         border:none;border-radius:8px;font-size:.9375rem;font-weight:600;
                         cursor:pointer;">
            Activer la 2FA
          </button>
        </form>
      </div>

    </div>
  </div>

  <div style="text-align:center;margin-top:1rem;">
    <a href="{{ url_for('profile') }}" style="font-size:.875rem;color:#64748b;">
      ← Annuler
    </a>
  </div>

</div>

<script>
document.getElementById('token')?.addEventListener('input', function() {
  let v = this.value.replace(/\D/g, '').slice(0, 6);
  this.value = v.length > 3 ? v.slice(0,3) + ' ' + v.slice(3) : v;
});
</script>
{% endblock %}
```

---

## 10. Profil utilisateur — Boutons d'activation/désactivation

Dans la page profil, afficher les boutons selon l'état actuel :

```html
<!-- Dans profile.html -->

{% if current_user.totp_enabled %}
  <!-- 2FA activée — bouton désactiver -->
  <div style="display:flex;align-items:center;gap:.75rem;padding:1rem;
              background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;">
    <i class="fas fa-shield-alt" style="color:#16a34a;font-size:1.25rem;"></i>
    <div style="flex:1;">
      <div style="font-weight:600;color:#15803d;">Double authentification activée</div>
      <div style="font-size:.8125rem;color:#166534;">Votre compte est protégé par TOTP</div>
    </div>
    <button type="button" onclick="document.getElementById('disable2faModal').style.display='flex'"
            style="padding:.5rem .875rem;background:#dc2626;color:white;
                   border:none;border-radius:6px;cursor:pointer;font-size:.8125rem;">
      Désactiver
    </button>
  </div>

  <!-- Modal désactivation -->
  <div id="disable2faModal"
       style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);
              align-items:center;justify-content:center;z-index:1000;">
    <div style="background:white;border-radius:12px;padding:1.5rem;width:100%;max-width:380px;">
      <h3 style="font-size:1rem;font-weight:700;margin-bottom:.875rem;">Désactiver la 2FA</h3>
      <p style="font-size:.8125rem;color:#475569;margin-bottom:1rem;">
        Entrez votre code TOTP actuel pour confirmer.
      </p>
      <form method="POST" action="{{ url_for('disable_2fa') }}"
            style="display:flex;flex-direction:column;gap:.875rem;">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <input type="text" name="token"
               inputmode="numeric" maxlength="7" autocomplete="one-time-code"
               placeholder="000 000"
               style="text-align:center;font-size:1.5rem;font-weight:700;font-family:monospace;
                      letter-spacing:.375rem;padding:.75rem;border:2px solid #e2e8f0;
                      border-radius:8px;box-sizing:border-box;width:100%;">
        <div style="display:flex;gap:.75rem;">
          <button type="button"
                  onclick="document.getElementById('disable2faModal').style.display='none'"
                  style="flex:1;padding:.625rem;border:1px solid #e2e8f0;background:white;
                         border-radius:6px;cursor:pointer;">
            Annuler
          </button>
          <button type="submit"
                  style="flex:1;padding:.625rem;background:#dc2626;color:white;
                         border:none;border-radius:6px;cursor:pointer;font-weight:600;">
            Désactiver
          </button>
        </div>
      </form>
    </div>
  </div>

{% else %}
  <!-- 2FA désactivée — bouton activer -->
  <div style="display:flex;align-items:center;gap:.75rem;padding:1rem;
              background:#fef3c7;border:1px solid #fde68a;border-radius:8px;">
    <i class="fas fa-shield-alt" style="color:#d97706;font-size:1.25rem;"></i>
    <div style="flex:1;">
      <div style="font-weight:600;color:#92400e;">Double authentification désactivée</div>
      <div style="font-size:.8125rem;color:#78350f;">Activez-la pour renforcer la sécurité</div>
    </div>
    <a href="{{ url_for('setup_2fa') }}"
       style="padding:.5rem .875rem;background:#3b82f6;color:white;
              border-radius:6px;text-decoration:none;font-size:.8125rem;">
      Activer
    </a>
  </div>
{% endif %}
```

---

## 11. Sécurité — Points critiques

### Pattern pending secret (anti-activation-fantôme)

```
Visite /setup_2fa (GET)
  → génère secret aléatoire
  → stocke dans totp_pending_secret (PAS totp_secret)
  → affiche QR code

Soumission du code (POST)
  → vérifie le code contre totp_pending_secret
  → si valide seulement :
       totp_secret = totp_pending_secret
       totp_pending_secret = None
       totp_enabled = True
```

Si l'utilisateur quitte sans confirmer → `totp_pending_secret` reste en DB mais `totp_enabled`
reste `False`. La prochaine visite génère un nouveau `totp_pending_secret` (écrase l'ancien).
**Le compte n'est jamais verrouillé par un secret non confirmé.**

### `valid_window=1`

```python
totp.verify(token, valid_window=1)
```

Accepte le code de la période précédente ET de la suivante (±30s).
Compense les décalages d'horloge entre le serveur et le téléphone.
`valid_window=2` (±60s) serait trop permissif.

### Nettoyage du token avant vérification

```python
token = request.form.get('token', '').strip().replace(' ', '')
```

Le template insère automatiquement un espace après le 3e chiffre (`"123 456"`).
La route doit toujours nettoyer cet espace avant de passer à `totp.verify()`.

### Ne pas logger l'utilisateur avant la vérification 2FA

```python
# CORRECT : stocker l'ID en session, pas login_user()
session['2fa_pending_user_id'] = user.id
return redirect(url_for('verify_2fa'))

# INCORRECT : appeler login_user() avant la 2FA
# login_user(user)  ← NE PAS FAIRE
```

### Désactivation protégée

Toujours exiger le code TOTP actuel pour désactiver la 2FA.
Si quelqu'un vole la session d'un utilisateur, il ne peut pas désactiver la 2FA
sans avoir aussi le téléphone.

### Restriction de rôle (adapter selon le projet)

Dans GEC, la 2FA est réservée au `super_admin` :
```python
if current_user.role != 'super_admin':
    abort(403)
```

Pour un projet où tous les utilisateurs peuvent activer la 2FA, supprimer cette restriction.
Pour limiter à un groupe, utiliser `current_user.has_permission('enable_2fa')`.

---

## Checklist d'intégration

- [ ] `pip install pyotp "qrcode[pil]"` + `requirements.txt` à jour
- [ ] Migration DB : 3 colonnes (`totp_secret`, `totp_enabled`, `totp_pending_secret`)
- [ ] Méthodes `verify_totp()` et `get_totp_uri()` dans le modèle `User`
- [ ] Intercepter dans la route `login` si `user.totp_enabled`
- [ ] Route `/verify_2fa` (GET + POST)
- [ ] Route `/profile/2fa/setup` (GET + POST)
- [ ] Route `/profile/2fa/disable` (POST uniquement)
- [ ] Template `verify_2fa.html` (standalone, sans navbar)
- [ ] Template `setup_2fa.html` (avec navbar, extend base.html)
- [ ] Boutons activation/désactivation dans la page profil
- [ ] JS auto-format TOTP (`"123 456"`) dans les deux templates
- [ ] `session['last_activity'] = time.time()` dans la route `verify_2fa` après `login_user()`

---

*Implémentation extraite de GEC-Courrier — MOA Digital Agency — Avril 2026*
