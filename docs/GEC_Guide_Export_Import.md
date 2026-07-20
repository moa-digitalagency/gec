# Guide Export/Import Cross-Platform (Linux ↔ Windows)

## 🌍 Compatibilité Multi-Plateformes

Le système d'export/import GEC est maintenant **100% compatible** entre Linux et Windows. Vous pouvez exporter des courriers depuis un serveur Linux et les importer sur Windows, ou vice-versa, **sans aucun problème de chemins de fichiers**.

## 🔐 Sécurité & Chiffrement

Les archives de sauvegarde sont **chiffrées en AES-256**. Cela garantit que les données sensibles ne peuvent pas être lues si le fichier ZIP est intercepté.

Pour chaque export, une **clé de déchiffrement unique de 16 caractères** est générée.

> ⚠️ **ATTENTION :** Vous devez **ABSOLUMENT** copier et sauvegarder cette clé en lieu sûr.
> Sans cette clé, le fichier ZIP de sauvegarde est **inutilisable**. Il est impossible de restaurer les données sans ce code.

## 📋 Comment utiliser

### Export (Backup)

1. Aller dans **"Paramètres"** → **"Sauvegardes"**.
2. Cliquer sur **"Créer une sauvegarde"**.
3. Une fois l'export terminé, vous serez redirigé vers une page de confirmation.
4. Une **clé de sécurité de 16 caractères** s'affichera à l'écran.
   - **Copiez cette clé** immédiatement.
   - Cliquez sur **"Télécharger l'archive"**.

### Import (Restauration)

Pour restaurer une sauvegarde (sur le même serveur ou un autre OS) :

1. Aller dans **"Paramètres"** → **"Sauvegardes"**.
2. Dans la section **"Restaurer une sauvegarde"** :
   - Sélectionnez le fichier ZIP de sauvegarde.
   - Entrez la **Clé de déchiffrement** de 16 caractères associée à ce fichier.
3. Validez.
   - Le système déchiffrera l'archive.
   - Les chemins seront automatiquement convertis pour l'OS de destination (Linux/Windows).
   - Les données seront restaurées.

## 🔧 Ce qui a été corrigé (Technique)

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
   - Les fichiers sont **chiffrés (AES-256)** dans le ZIP
   - La clé de déchiffrement est unique pour chaque export
   - Rechiffrés à l'import avec les clés locales de destination

3. **Compatibilité rétroactive** :
   - Les anciens exports fonctionnent toujours
   - Utilise `path_basename` si disponible
   - Sinon, fallback sur `filename`

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

### Problème : Clé de déchiffrement perdue

**Cause** : La clé n'a pas été sauvegardée lors de l'export.

**Solution** : Le ZIP est chiffré et ne peut pas être ouvert. Vous devez refaire l'export et bien noter la clé.

## 🎯 Résumé

✅ **Export Linux → Import Windows** : Fonctionne  
✅ **Export Windows → Import Linux** : Fonctionne  
✅ **Même plateforme** : Fonctionne  
✅ **Chemins normalisés automatiquement**  
✅ **Archive sécurisée par clé unique (AES-256)**
✅ **Pas de perte de données**  

---

**Développé avec ❤️ pour GEC - Gestion Électronique du Courrier**
