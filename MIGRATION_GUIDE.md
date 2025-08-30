# Guide de Migration Automatique - GEC

## Système de Migration Automatique

Ce système garantit que les futures mises à jour n'obligeront plus à tout réinstaller ou à perdre les données existantes. Il détecte automatiquement les nouvelles colonnes et les ajoute de manière sécurisée.

## Comment ça fonctionne

1. **Au démarrage** : L'application vérifie automatiquement si toutes les colonnes existent
2. **Détection** : Si une colonne manque, elle est automatiquement créée
3. **Sécurité** : Les données existantes sont préservées
4. **Logs** : Toutes les migrations sont enregistrées dans les logs

## Ajouter une nouvelle migration

### Pour ajouter une nouvelle colonne à une table existante :

1. Ouvrir le fichier `migration_utils.py`
2. Ajouter la nouvelle colonne dans la section appropriée :

```python
# Migration pour parametres_systeme
if add_column_safely(engine, 'parametres_systeme', 'nouvelle_colonne', 'VARCHAR(255)'):
    migrations_applied += 1
    logging.info("✓ Migration: Nouvelle colonne ajoutée")
```

### Types de colonnes supportés :

- `VARCHAR(longueur)` - Texte de longueur limitée
- `TEXT` - Texte long
- `INTEGER` - Nombre entier
- `BOOLEAN` - Vrai/Faux
- `TIMESTAMP` - Date et heure
- `DECIMAL(precision, scale)` - Nombres décimaux

### Exemple complet :

```python
# Ajouter une colonne pour stocker la signature électronique
if add_column_safely(engine, 'user', 'signature_electronique', 'TEXT'):
    migrations_applied += 1
    logging.info("✓ Migration: Colonne signature_electronique ajoutée")
```

## Logs de Migration

Les migrations sont enregistrées dans les logs avec ces messages :

- ✅ `Aucune migration nécessaire - Base de données à jour`
- 🔄 `X migration(s) automatique(s) appliquée(s) avec succès`
- ✓ `Migration: Colonne XXX ajoutée`
- ❌ `Erreur lors des migrations automatiques`

## Avantages

1. **Pas de perte de données** : Les données existantes sont conservées
2. **Installation automatique** : Pas besoin de réinstaller l'application
3. **Compatibilité** : Fonctionne avec SQLite et PostgreSQL
4. **Sécurité** : Les migrations échouent sans casser l'application
5. **Traçabilité** : Tous les changements sont enregistrés

## Dépannage

Si une migration échoue :

1. Vérifier les logs pour voir l'erreur exacte
2. La migration sera tentée à nouveau au prochain redémarrage
3. L'application continue de fonctionner même si une migration échoue

## Structure des migrations futures

```python
def run_automatic_migrations(app, db):
    """Toutes les futures migrations vont ici"""
    
    # Migration Version 1.0.1
    if add_column_safely(engine, 'table', 'colonne', 'TYPE'):
        migrations_applied += 1
    
    # Migration Version 1.0.2
    # Ajouter les nouvelles colonnes ici
    
    # Et ainsi de suite...
```

Ce système garantit une évolution douce de l'application sans interruption de service ni perte de données.