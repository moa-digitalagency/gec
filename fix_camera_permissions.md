# Solution pour le problème de caméra dans Brave

## Le problème
Brave bloque la caméra avec l'erreur "NotAllowedError - Permission denied"

## Solutions

### Solution 1 : Via l'icône caméra
1. Regardez dans la barre d'adresse de Brave
2. Cliquez sur l'icône 📹 (caméra) 
3. Changez de "Bloquer" à "Autoriser"
4. Rafraîchissez la page (F5)

### Solution 2 : Via le cadenas
1. Cliquez sur le cadenas 🔒 à gauche de l'URL
2. Trouvez "Caméra" dans la liste
3. Changez de "Bloquer" à "Autoriser"
4. Rafraîchissez la page

### Solution 3 : Via les paramètres Brave
1. Allez dans : brave://settings/content/camera
2. Dans "Autoriser", cliquez sur "Ajouter"
3. Entrez l'URL de votre site Replit
4. Cliquez sur "Ajouter"
5. Retournez sur le site et rafraîchissez

### Solution 4 : Réinitialiser les permissions
1. brave://settings/content/all
2. Trouvez votre site Replit
3. Cliquez sur la poubelle pour supprimer
4. Retournez sur le site
5. Brave redemandera la permission - acceptez

## Vérification
Après avoir appliqué une solution, allez sur `/test_webcam` et vous devriez voir :
- ✅ "Caméra autorisée" en vert
- Le bouton "Démarrer Webcam" devrait fonctionner

## Note importante
Le code fonctionne correctement. Le problème vient uniquement des permissions Brave qui sont restrictives par défaut pour la sécurité.