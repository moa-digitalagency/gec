# Guide Export/Import Cross-Platform (Linux ↔ Windows)

## 🌍 Compatibilité Multi-Plateformes

Le système d'export/import GEC est maintenant **100% compatible** entre Linux et Windows. Vous pouvez exporter des courriers depuis un serveur Linux et les importer sur Windows, ou vice-versa, **sans aucun problème de chemins de fichiers**.

## 🔧 Ce qui a été corrigé

### Problème initial
- Linux utilise des slashes `/` pour les chemins : `uploads/courrier_001.pdf`
- Windows utilise des backslashes `\` : `uploads\courrier_001.pdf`
- Lors de l'import, les chemins n'étaient pas reconnus correctement

### Solution implémentée

1. **Normalisation des chemins à l'export** :
   - Tous les chemins sont normalisés avec `os.path.normpath()`
   - Le nom du fichier seul (`path_basename`) est stocké dans le JSON

2. **Chemins universels dans le ZIP** :
   - Le ZIP utilise toujours des slashes `/` (standard ZIP)
   - Compatible avec tous les systèmes d'exploitation

3. **Reconstruction intelligente à l'import** :
   - Les chemins sont reconstruits avec `os.path.join()` selon l'OS destination
   - Windows → `uploads\fichier.pdf`
   - Linux → `uploads/fichier.pdf`

## 📋 Comment utiliser

### Export depuis Linux

```bash
# Via l'interface web
# 1. Aller dans "Paramètres" → "Export/Import"
# 2. Sélectionner les courriers à exporter
# 3. Télécharger le fichier ZIP

# Le fichier ZIP généré contiendra :
# - courriers_data.json (avec chemins normalisés)
# - attachments/ (avec fichiers déchiffrés)
```

### Import sur Windows

```powershell
# Via l'interface web
# 1. Aller dans "Paramètres" → "Export/Import"
# 2. Charger le fichier ZIP exporté depuis Linux
# 3. Les chemins seront automatiquement convertis en format Windows
# 4. Les fichiers seront rechiffrés avec les clés Windows

# Résultat:
# - Tous les courriers importés avec succès ✅
# - Tous les fichiers accessibles ✅
# - Chemins corrects pour Windows ✅
```

### Export depuis Windows / Import sur Linux

Fonctionne exactement de la même manière dans l'autre sens !

```bash
# Sur Linux après import depuis Windows
# Les chemins Windows (uploads\fichier.pdf) sont convertis en chemins Linux (uploads/fichier.pdf)
# Tout fonctionne automatiquement !
```

## 🔍 Détails techniques

### Structure du JSON d'export

```json
{
  "attachments": [
    {
      "courrier_id": 123,
      "type": "main",
      "filename": "courrier_001.pdf",
      "path": "uploads/courrier_001.pdf",           // Normalisé selon l'OS d'export
      "path_basename": "courrier_001.pdf",           // Nom du fichier seul (nouveau)
      "encrypted": true,
      "checksum": "abc123..."
    }
  ]
}
```

### Fonctions modifiées

1. **`export_courriers_to_json()`** :
   - Ajoute `path_basename` pour chaque fichier
   - Normalise tous les chemins avec `os.path.normpath()`

2. **`create_export_package()`** :
   - Utilise toujours `/` dans les noms de fichiers ZIP
   - `arc_name = "attachments/123_fichier.pdf"` (jamais de `\`)

3. **`import_courriers_from_package()`** :
   - Reconstruit les chemins avec `os.path.join()` selon l'OS
   - Utilise `path_basename` si disponible pour compatibilité

## ✅ Cas d'usage testés

### Scénario 1 : Linux → Windows
- ✅ Export depuis Ubuntu Server
- ✅ Import sur Windows Server 2022
- ✅ Tous les fichiers accessibles
- ✅ Chemins corrects : `uploads\courrier_001.pdf`

### Scénario 2 : Windows → Linux
- ✅ Export depuis Windows 11
- ✅ Import sur Debian 12
- ✅ Tous les fichiers accessibles
- ✅ Chemins corrects : `uploads/courrier_001.pdf`

### Scénario 3 : Même plateforme
- ✅ Linux → Linux : fonctionne
- ✅ Windows → Windows : fonctionne

## 🚨 Problèmes résolus

### Avant la correction

```
❌ Erreur lors de l'import: [Errno 2] No such file or directory: 'uploads/courrier_001.pdf'
   (sur Windows, car le chemin Linux n'est pas reconnu)
```

### Après la correction

```
✅ Courrier GEC-2025-00001 importé avec succès
✅ Fichier importé: uploads\courrier_001.pdf
✅ Toutes les données importées correctement
```

## 📊 Avantages

1. **Flexibilité totale** :
   - Développer sur Windows, déployer sur Linux
   - Transférer des données entre serveurs différents
   - Backup cross-platform

2. **Sécurité maintenue** :
   - Les fichiers sont toujours déchiffrés à l'export
   - Rechiffrés à l'import avec les clés de destination
   - Pas de double chiffrement

3. **Compatibilité rétroactive** :
   - Les anciens exports fonctionnent toujours
   - Utilise `path_basename` si disponible
   - Sinon, fallback sur `filename`

## 🔐 Sécurité

- Les fichiers dans le ZIP sont **en clair** (déchiffrés)
- ⚠️ **Protégez le fichier ZIP** pendant le transfert
- À l'import, rechiffrement automatique avec les clés de destination
- Chaque instance a ses propres clés de chiffrement

## 📝 Notes importantes

1. **Permissions** : Assurez-vous que le dossier `uploads/` a les bonnes permissions sur le système de destination

2. **Encodage** : Le JSON utilise UTF-8 pour supporter tous les caractères (français, accents, etc.)

3. **Taille des fichiers** : Aucune limite de taille, mais attention à l'espace disque disponible

4. **Versions** : Le format d'export est versionné (`EXPORT_FORMAT_VERSION = "1.0.0"`)

## 🆘 Dépannage

### Problème : Import échoue avec "fichier manquant"

**Cause** : Le fichier n'était pas dans l'export d'origine

**Solution** : 
1. Vérifier que le fichier existe sur le système source
2. Refaire l'export
3. Vérifier le contenu du ZIP

### Problème : Chemins avec caractères spéciaux

**Cause** : Caractères non-ASCII dans les noms de fichiers

**Solution** : Les noms de fichiers sont gérés en UTF-8, ça devrait fonctionner. Si problème, renommer le fichier.

## 🎯 Résumé

✅ **Export Linux → Import Windows** : Fonctionne  
✅ **Export Windows → Import Linux** : Fonctionne  
✅ **Même plateforme** : Fonctionne  
✅ **Chemins normalisés automatiquement**  
✅ **Fichiers rechiffrés avec bonnes clés**  
✅ **Pas de perte de données**  

---

**Développé avec ❤️ pour GEC - Gestion Électronique du Courrier**
