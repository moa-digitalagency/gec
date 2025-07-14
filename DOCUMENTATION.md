# Documentation Technique - GEC Mines
## Cahier des Charges et Spécifications Complètes

---

## Table des matières

1. [Architecture du système](#architecture-du-système)
2. [Modèles de données](#modèles-de-données)
3. [Fonctionnalités détaillées](#fonctionnalités-détaillées)
4. [API et Routes](#api-et-routes)
5. [Système de permissions](#système-de-permissions)
6. [Interface utilisateur](#interface-utilisateur)
7. [Sécurité](#sécurité)
8. [Configuration et déploiement](#configuration-et-déploiement)

---

## Architecture du système

### Stack technologique

#### Backend
- **Framework** : Flask 2.3+ (Python)
- **ORM** : SQLAlchemy 2.0+ avec Flask-SQLAlchemy
- **Base de données** : PostgreSQL (production) / SQLite (développement)
- **Authentification** : Flask-Login avec sessions
- **Validation** : Werkzeug Security + validation métier
- **PDF** : ReportLab avec templates personnalisés
- **Serveur** : Gunicorn avec ProxyFix pour production

#### Frontend
- **CSS Framework** : Tailwind CSS 3.3+
- **JavaScript** : Vanilla JS + jQuery 3.6+
- **Tables** : DataTables 1.13.6 avec i18n français
- **Icons** : Font Awesome 6.0.0
- **Templates** : Jinja2 avec système d'héritage

#### Infrastructure
- **Hosting** : Replit Deployments (auto-scaling)
- **Storage** : Système de fichiers local avec backup
- **Monitoring** : Logs intégrés + métriques Flask
- **SSL** : Automatique via Replit

### Architecture des fichiers

```
/
├── app.py              # Configuration Flask principale
├── main.py             # Point d'entrée application
├── models.py           # Modèles SQLAlchemy
├── views.py            # Routes et logique métier
├── utils.py            # Fonctions utilitaires
├── lang/               # Système multilingue
│   ├── fr.json         # Traductions françaises
│   └── en.json         # Traductions anglaises
├── templates/          # Templates Jinja2
│   ├── base.html       # Template de base
│   ├── new_base.html   # Nouvelle base avec design RDC
│   ├── dashboard.html  # Tableau de bord
│   ├── view_mail.html  # Liste des courriers
│   ├── mail_detail_new.html # Détail courrier
│   ├── register_mail.html   # Formulaire enregistrement
│   ├── search.html     # Recherche avancée
│   ├── settings.html   # Configuration système
│   └── manage_*.html   # Gestion admin
├── static/             # Assets statiques
│   ├── js/app.js       # JavaScript principal
│   ├── css/           # Styles personnalisés
│   └── images/        # Logos et images
├── uploads/           # Fichiers téléchargés
├── exports/           # Exports PDF générés
└── utils/             # Modules utilitaires
    └── lang.py        # Gestion des langues
```

---

## Modèles de données

### Modèle User
```python
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    nom_complet = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    actif = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), nullable=False, default='user')
    langue = db.Column(db.String(5), nullable=False, default='fr')
    photo_profile = db.Column(db.String(255), nullable=True)
    departement_id = db.Column(db.Integer, db.ForeignKey('departement.id'))
    matricule = db.Column(db.String(50), nullable=True)
    fonction = db.Column(db.String(200), nullable=True)
```

### Modèle Courrier
```python
class Courrier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_accuse_reception = db.Column(db.String(50), unique=True, nullable=False)
    numero_reference = db.Column(db.String(100), nullable=True)
    objet = db.Column(db.Text, nullable=False)
    type_courrier = db.Column(db.String(20), nullable=False, default='ENTRANT')
    expediteur = db.Column(db.String(200), nullable=True)  # Pour ENTRANT
    destinataire = db.Column(db.String(200), nullable=True)  # Pour SORTANT
    date_enregistrement = db.Column(db.DateTime, default=datetime.utcnow)
    fichier_nom = db.Column(db.String(255), nullable=True)
    fichier_chemin = db.Column(db.String(500), nullable=True)
    fichier_type = db.Column(db.String(50), nullable=True)
    statut = db.Column(db.String(50), nullable=False, default='RECU')
    date_modification_statut = db.Column(db.DateTime, default=datetime.utcnow)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    modifie_par_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
```

### Relations clés
- **User ↔ Departement** : Many-to-One (un utilisateur appartient à un département)
- **User ↔ Courrier** : One-to-Many (un utilisateur enregistre plusieurs courriers)
- **User ↔ LogActivite** : One-to-Many (traçabilité des actions)
- **Role ↔ RolePermission** : One-to-Many (permissions granulaires)

---

## Fonctionnalités détaillées

### 1. Authentification et gestion des sessions

#### Connexion
- **Route** : `/login` (GET/POST)
- **Méthode** : Flask-Login avec session persistante
- **Validation** : Werkzeug password verification
- **Sécurité** : Protection contre force brute (rate limiting côté serveur)

#### Gestion des rôles
```python
ROLES_HIERARCHY = {
    'super_admin': ['read_all_mail', 'manage_users', 'manage_system'],
    'admin': ['read_department_mail', 'manage_department'],
    'user': ['read_own_mail', 'register_mail']
}
```

### 2. Enregistrement de courrier

#### Processus complet
1. **Validation formulaire** : Champs obligatoires + types fichiers
2. **Upload sécurisé** : Validation MIME type + taille limite 16MB
3. **Génération numéro** : Format configurable `GEC-{year}-{counter:05d}`
4. **Stockage base** : Transaction atomique avec rollback
5. **Log activité** : Traçabilité complète de l'action

#### Types de courrier supportés
- **ENTRANT** : Courrier reçu (champ expediteur obligatoire)
- **SORTANT** : Courrier envoyé (champ destinataire obligatoire)

#### Extensions fichier autorisées
```python
ALLOWED_EXTENSIONS = {
    'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 
    'xls', 'xlsx', 'txt', 'rtf'
}
```

### 3. Système de recherche avancée

#### Critères de recherche
- **Texte libre** : Recherche dans objet, expéditeur, destinataire, référence
- **Plage de dates** : Date début/fin avec validation
- **Statut** : Filtre par état actuel
- **Type** : Entrant/Sortant
- **Tri** : Multi-critères avec ordre ASC/DESC

#### Implémentation technique
```python
# Exemple de requête complexe
query = Courrier.query.filter(
    or_(
        Courrier.objet.contains(search),
        Courrier.numero_reference.contains(search),
        Courrier.expediteur.contains(search),
        Courrier.destinataire.contains(search)
    )
).filter(Courrier.statut == statut)
```

### 4. Export PDF avec branding officiel

#### Contenu du PDF
- **En-tête** : Logo + titre + sous-titre configurables
- **Métadonnées** : Toutes les informations du courrier
- **QR Code** : Lien direct vers le courrier (optionnel)
- **Footer** : Copyright + date génération

#### Template ReportLab
```python
def export_courrier_pdf(courrier):
    # Configuration depuis ParametresSysteme
    params = ParametresSysteme.get_parametres()
    
    # Génération PDF avec template officiel
    # Logo, titre, sous-titre personnalisables
    # Styles conformes à l'identité visuelle RDC
```

### 5. Gestion des statuts dynamiques

#### Statuts par défaut
- **RECU** : État initial (couleur grise)
- **EN_COURS** : En traitement (couleur bleue)
- **TRAITE** : Finalisé (couleur verte)
- **ARCHIVE** : Archivé (couleur neutre)
- **URGENT** : Prioritaire (couleur rouge)

#### Configuration avancée
- **Couleurs personnalisables** : Classes Tailwind CSS
- **Ordre d'affichage** : Tri par champ `ordre`
- **Statuts actifs/inactifs** : Gestion du cycle de vie

### 6. Système multilingue

#### Architecture i18n
```python
def t(key, lang_code=None, **kwargs):
    """Fonction de traduction avec fallback"""
    translations = load_translations(lang_code or get_current_language())
    return translations.get(key, key).format(**kwargs)
```

#### Langues supportées
- **Français (fr)** : Langue par défaut
- **Anglais (en)** : Langue secondaire
- **Extensible** : Ajout facile de nouvelles langues

### 7. Dashboard et métriques

#### Widgets temps réel
- **Courriers totaux** : Compte global par utilisateur
- **Courriers récents** : 5 derniers enregistrements
- **Statistiques temporelles** : Aujourd'hui/Semaine/Mois
- **Actions rapides** : Liens directs vers fonctions principales

#### Permissions d'accès
- **Super Admin** : Vue globale tous départements
- **Admin** : Vue département assigné
- **User** : Vue personnelle uniquement

### 8. Système de sauvegarde et restauration

#### Fonctionnalités de backup
- **Archive complète** : Base de données + fichiers système + uploads + configuration
- **Format ZIP** : Archive compressée avec métadonnées
- **Sauvegarde automatisée** : Via tâches CRON programmables
- **Historique** : Liste des sauvegardes avec date/taille/téléchargement

#### Processus de sauvegarde
```python
def create_system_backup():
    # 1. Sauvegarde base de données (pg_dump/sqlite copy)
    # 2. Archive fichiers système critiques
    # 3. Include uploads et exports
    # 4. Métadonnées avec timestamp et utilisateur
    # 5. Compression ZIP optimisée
```

#### Restauration système
- **Sauvegarde de sécurité** : Backup automatique avant restauration
- **Extraction sélective** : Évite l'écrasement de fichiers critiques
- **Validation métadonnées** : Vérification compatibilité archive
- **Logs détaillés** : Traçabilité complète du processus

#### Sécurité des sauvegardes
- **Accès restreint** : Super Admin uniquement
- **Protection dossier** : Restriction Apache/Nginx
- **Chiffrement** : Archive protégée avec métadonnées intégrées
- **Nettoyage automatique** : Suppression anciennes sauvegardes (configurable)

---

## API et Routes

### Routes d'authentification
```python
@app.route('/login', methods=['GET', 'POST'])
@app.route('/logout')
```

### Routes courrier
```python
@app.route('/')                          # Dashboard
@app.route('/register_mail', methods=['GET', 'POST'])
@app.route('/view_mail')                 # Liste + filtres
@app.route('/mail/<int:id>')             # Détail
@app.route('/search')                    # Recherche avancée
@app.route('/export_pdf/<int:id>')       # Export PDF
@app.route('/download_file/<int:id>')    # Téléchargement fichier
@app.route('/view_file/<int:id>')        # Visualisation fichier
@app.route('/change_status/<int:id>', methods=['POST'])
```

### Routes administration (Super Admin uniquement)
```python
@app.route('/settings', methods=['GET', 'POST'])
@app.route('/manage_users')
@app.route('/manage_roles')
@app.route('/manage_departments')
@app.route('/manage_statuses')
@app.route('/view_logs')
@app.route('/backup_system', methods=['POST'])
@app.route('/restore_system', methods=['POST'])
@app.route('/download_backup/<filename>')
```

### API JSON (futures extensions)
```python
# Endpoints RESTful pour intégrations futures
@app.route('/api/courriers')             # GET: Liste paginée
@app.route('/api/courriers', methods=['POST'])  # POST: Création
@app.route('/api/courriers/<int:id>')    # GET/PUT/DELETE
@app.route('/api/stats')                 # GET: Métriques
```

---

## Système de permissions

### Matrice de permissions

| Permission | Super Admin | Admin | User |
|------------|-------------|--------|------|
| `read_all_mail` | ✅ | ❌ | ❌ |
| `read_department_mail` | ✅ | ✅ | ❌ |
| `read_own_mail` | ✅ | ✅ | ✅ |
| `register_mail` | ✅ | ✅ | ✅ |
| `manage_users` | ✅ | ❌ | ❌ |
| `manage_system` | ✅ | ❌ | ❌ |
| `view_logs` | ✅ | ❌ | ❌ |
| `manage_departments` | ✅ | ❌ | ❌ |
| `manage_roles` | ✅ | ❌ | ❌ |
| `backup_system` | ✅ | ❌ | ❌ |
| `restore_system` | ✅ | ❌ | ❌ |

### Implémentation des contrôles
```python
def can_view_courrier(self, courrier):
    """Vérifie l'accès à un courrier spécifique"""
    if self.has_permission('read_all_mail'):
        return True
    elif self.has_permission('read_department_mail'):
        return courrier.utilisateur.departement_id == self.departement_id
    elif self.has_permission('read_own_mail'):
        return courrier.utilisateur_id == self.id
    return False
```

---

## Interface utilisateur

### Design System RDC

#### Palette de couleurs
```css
:root {
    --rdc-blue: #003087;    /* Navigation, primaire */
    --rdc-yellow: #FFD700;  /* Recherche, attention */
    --rdc-red: #CE1126;     /* Export, urgence */
    --rdc-green: #009639;   /* Succès, validation */
}
```

#### Composants UI standardisés

##### Boutons d'action
```html
<!-- Bouton primaire -->
<button class="bg-rdc-blue hover:bg-opacity-90 text-white px-4 py-2 rounded-md">
    <i class="fas fa-plus mr-2"></i>
    Action Primaire
</button>

<!-- Bouton secondaire -->
<button class="border border-gray-300 text-gray-700 bg-white hover:bg-gray-50 px-4 py-2 rounded-md">
    Action Secondaire
</button>
```

##### Cards avec shadow RDC
```html
<div class="bg-white shadow-rdc rounded-xl p-6">
    <h2 class="text-xl font-semibold text-gray-900 flex items-center">
        <i class="fas fa-icon mr-2 text-rdc-blue"></i>
        Titre de section
    </h2>
    <!-- Contenu -->
</div>
```

### Navigation adaptative

#### Menu hamburger universel
```javascript
// Menu responsive avec gestion d'état
function toggleMobileMenu() {
    const menu = document.getElementById('mobile-menu');
    const isHidden = menu.classList.contains('hidden');
    
    if (isHidden) {
        menu.classList.remove('hidden');
        menu.style.opacity = '0';
        menu.style.transform = 'translateY(-10px)';
        
        requestAnimationFrame(() => {
            menu.style.transition = 'all 0.2s ease-out';
            menu.style.opacity = '1';
            menu.style.transform = 'translateY(0)';
        });
    } else {
        menu.style.opacity = '0';
        menu.style.transform = 'translateY(-10px)';
        setTimeout(() => menu.classList.add('hidden'), 200);
    }
}
```

#### Actions rapides contextuelles
Chaque page dispose d'une sidebar avec actions pertinentes :
- **Dashboard** : Nouveau courrier, Consulter, Recherche, Récents
- **Liste courriers** : Nouveau, Recherche, Dashboard, Récents
- **Détail courrier** : Modifier statut, Export PDF, Retour liste

### Responsive design

#### Breakpoints Tailwind
```css
/* Mobile first approach */
.class { /* Mobile (default) */ }
@media (min-width: 640px) { .sm\:class { /* Small */ } }
@media (min-width: 768px) { .md\:class { /* Medium */ } }
@media (min-width: 1024px) { .lg\:class { /* Large */ } }
@media (min-width: 1280px) { .xl\:class { /* Extra Large */ } }
```

#### Adaptations mobiles
- **Navigation** : Menu hamburger avec overlay
- **Tables** : Scroll horizontal avec sticky headers
- **Formulaires** : Stack vertical des champs
- **Actions** : Boutons adaptés au touch

---

## Sécurité

### Authentification et autorisation

#### Hachage des mots de passe
```python
from werkzeug.security import generate_password_hash, check_password_hash

# Stockage sécurisé (utilise pbkdf2:sha256 par défaut)
password_hash = generate_password_hash(password)

# Vérification
is_valid = check_password_hash(password_hash, password)
```

#### Sessions Flask-Login
```python
# Configuration session
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS uniquement
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Pas d'accès JS
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
```

### Validation des données

#### Upload de fichiers
```python
def allowed_file(filename):
    """Validation extension + MIME type"""
    if '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS

# Validation taille (16MB max)
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
```

#### Validation formulaires
- **Côté client** : JavaScript pour UX immédiate
- **Côté serveur** : Validation stricte pour sécurité
- **Sanitisation** : Échappement automatique Jinja2

### Protection CSRF

#### Implémentation Flask
```python
# Protection native Flask via sessions
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1h
```

### Logs et audit

#### Logging complet
```python
def log_activity(user_id, action, description, courrier_id=None):
    """Enregistrement traçable de toutes les actions"""
    log = LogActivite(
        utilisateur_id=user_id,
        action=action,
        description=description,
        courrier_id=courrier_id,
        ip_address=request.remote_addr,
        date_action=datetime.utcnow()
    )
    db.session.add(log)
    db.session.commit()
```

#### Actions tracées
- Connexions/déconnexions
- Enregistrements de courrier
- Consultations de documents
- Modifications de statut
- Exports PDF
- Actions administratives

---

## Configuration et déploiement

### Variables d'environnement

#### Configuration production
```bash
# Base de données
DATABASE_URL=postgresql://user:password@host:port/database

# Sécurité
SESSION_SECRET=your_very_long_random_secret_key_here

# Flask
FLASK_ENV=production
FLASK_DEBUG=False

# Application
MAX_CONTENT_LENGTH=16777216  # 16MB
UPLOAD_FOLDER=uploads
EXPORT_FOLDER=exports
```

#### Configuration développement
```bash
DATABASE_URL=sqlite:///gec_mines.db
SESSION_SECRET=dev_secret_change_in_production
FLASK_ENV=development
FLASK_DEBUG=True
```

### Déploiement Replit

#### Fichier de configuration (.replit)
```toml
[deployment]
run = "gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app"
deploymentTarget = "gce"

[env]
PYTHONPATH = "."
```

#### Optimisations production
```python
# Middleware proxy pour déploiement
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configuration base de données
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,      # Recyclage connexions
    "pool_pre_ping": True,    # Vérification connexions
    "pool_size": 10,          # Taille pool
    "max_overflow": 20        # Connexions overflow
}
```

### Maintenance et monitoring

#### Sauvegarde données
```bash
# Sauvegarde PostgreSQL
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Sauvegarde fichiers uploads
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/
```

#### Monitoring logs
```python
import logging

# Configuration logging production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

### Performance et scalabilité

#### Optimisations base de données
```sql
-- Index pour recherche rapide
CREATE INDEX idx_courrier_search ON courrier(objet, expediteur, destinataire);
CREATE INDEX idx_courrier_date ON courrier(date_enregistrement);
CREATE INDEX idx_courrier_status ON courrier(statut);
CREATE INDEX idx_courrier_user ON courrier(utilisateur_id);
```

#### Cache et pagination
```python
# Pagination efficace
courriers = query.paginate(
    page=page, 
    per_page=20, 
    error_out=False,
    max_per_page=100
)
```

---

## Évolutions futures

### Fonctionnalités en développement

1. **API REST complète** pour intégrations externes
2. **Notifications push** pour changements de statut
3. **Workflow automatisé** avec règles métier
4. **OCR intégré** pour extraction automatique métadonnées
5. **Signature électronique** pour validation officielle
6. **Archivage automatique** selon politiques de rétention
7. **Reporting avancé** avec graphiques et métriques
8. **Integration SSO** avec Active Directory

### Architecture microservices (roadmap)

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend SPA  │    │  Auth Service   │    │ Document Service│
│   (React/Vue)   │◄──►│   (FastAPI)     │◄──►│   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Gateway API    │    │  User Service   │    │ Storage Service │
│   (Kong/Nginx)  │    │  (PostgreSQL)   │    │ (MinIO/S3)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

**© 2025 GEC Mines - Documentation Technique v1.0**
*Dernière mise à jour : 14 juillet 2025*