# Guide de Démarrage Rapide - GEC Mines

## 🚀 Installation immédiate

### 1. Configuration de base
```bash
# Variables d'environnement requises
export DATABASE_URL=postgresql://user:pass@host:port/db
export SESSION_SECRET=your_very_long_secret_key

# Pour développement local (SQLite)
export DATABASE_URL=sqlite:///gec_mines.db
export SESSION_SECRET=dev_secret_key
```

### 2. Lancement direct
```bash
# Démarrage serveur
python main.py

# Ou avec Gunicorn (production)
gunicorn --bind 0.0.0.0:5000 main:app
```

### 3. Premier accès
- **URL** : http://localhost:5000
- **Login** : `admin`
- **Mot de passe** : `admin123`
- **Rôle** : Super Administrateur

## ⚡ Actions rapides

### Enregistrer votre premier courrier
1. Dashboard → **"Nouveau Courrier"**
2. Remplir les champs obligatoires :
   - **Type** : Entrant ou Sortant
   - **Objet** : Description du courrier
   - **Contact** : Expéditeur (entrant) ou Destinataire (sortant)
3. **Upload fichier** (optionnel)
4. **Sauvegarder** → Numéro d'accusé généré automatiquement

### Rechercher un courrier
1. Navigation → **"Consulter Courriers"**
2. Utiliser les **filtres** :
   - Recherche textuelle
   - Plage de dates
   - Statut spécifique
3. **Export PDF** disponible pour chaque courrier

### Créer un nouvel utilisateur
1. Menu hamburger → **"Gérer Utilisateurs"** (Super Admin uniquement)
2. **"Ajouter Utilisateur"**
3. Définir le rôle et département
4. L'utilisateur recevra ses identifiants

## 🎨 Personnalisation système

### Modifier le branding
1. Menu → **"Paramètres"** → **"Configuration Système"**
2. **Logo principal** : Upload de votre logo (.png, .jpg)
3. **Nom du logiciel** : Personnaliser le titre
4. **Format accusé** : Variables disponibles `{year}`, `{counter:05d}`

### Configurer l'organisation
- **Adresse complète** de votre organisme
- **Téléphone et email** de contact
- **Logo PDF** spécifique pour les exports

## 🔧 Configuration avancée

### Statuts personnalisés
1. **"Gérer les Statuts"** (Super Admin)
2. Ajouter vos statuts métier :
   - Nom et description
   - Couleur d'affichage (classes Tailwind)
   - Ordre d'affichage

### Départements et structure
1. **"Gérer Départements"**
2. Créer votre structure organisationnelle
3. Assigner un chef de département
4. Les utilisateurs voient uniquement leur périmètre

### Rôles et permissions
- **Super Admin** : Accès complet système
- **Admin** : Gestion département + consultation inter-services  
- **User** : Consultation personnelle + enregistrement

## 📱 Interface mobile

### Navigation responsive
- **Menu hamburger** accessible partout
- **Actions rapides** en sidebar sur desktop
- **Swipe** pour navigation mobile
- **Touch-friendly** boutons et formulaires

### Fonctionnalités mobiles
- Upload photos directement depuis l'appareil
- Consultation courriers en déplacement
- Notifications visuelles des changements statut

## 🌍 Multilingue

### Changer la langue
1. **Menu utilisateur** → Sélecteur de langue
2. **Français/English** disponibles
3. Préférence sauvegardée par utilisateur

### Ajouter une langue
1. Créer `lang/xx.json` (xx = code langue)
2. Copier structure de `fr.json`
3. Traduire toutes les clés
4. Ajouter dans `utils/lang.py`

## 📊 Tableaux de bord

### Métriques en temps réel
- **Courriers totaux** selon vos permissions
- **Activité récente** (aujourd'hui, semaine, mois)
- **Statuts en cours** avec compteurs
- **Accès rapide** aux fonctions fréquentes

### Logs d'activité (Super Admin)
- **Traçabilité complète** de toutes les actions
- **Filtrage** par utilisateur, date, type d'action
- **Export** pour audit et reporting

## 🔒 Sécurité

### Bonnes pratiques
- **Changer** le mot de passe admin par défaut
- **Sessions** expiration automatique (8h)
- **Permissions** vérifiées à chaque accès
- **Logs** complets pour audit

### Sauvegarde recommandée
```bash
# Base de données
pg_dump $DATABASE_URL > backup.sql

# Fichiers uploads
tar -czf uploads_backup.tar.gz uploads/
```

## 🚨 Résolution de problèmes

### Problèmes courants

**Upload échoue** → Vérifier taille fichier (limite 16MB)
**Session expire** → Reconnecter, sessions limitées à 8h
**Permissions refusées** → Vérifier rôle utilisateur assigné
**Page blanche** → Vérifier logs erreur dans console navigateur

### Support technique
1. **Logs application** : Consulter terminal/fichiers log
2. **Logs base données** : Vérifier connexion PostgreSQL
3. **Variables environnement** : Valider DATABASE_URL et SESSION_SECRET

## 📈 Cas d'usage types

### Secrétariat classique
1. **Courriers entrants** : Scan + enregistrement + dispatch
2. **Suivi traitement** : Changement statuts + relances
3. **Archivage** : Export PDF + classement

### Direction administrative  
1. **Vue d'ensemble** : Dashboard + statistiques
2. **Pilotage** : Logs activité + métriques
3. **Reporting** : Exports périodiques

### Utilisateur terrain
1. **Consultation mobile** : Accès courriers personnels
2. **Enregistrement** : Upload direct depuis terrain
3. **Suivi** : Notifications changements statut

---

🎯 **En 5 minutes** vous pouvez avoir un système de gestion du courrier 100% opérationnel !

**Support** : Consultez DOCUMENTATION.md pour les spécifications complètes