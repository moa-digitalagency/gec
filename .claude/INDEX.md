# INDEX — Dossier .claude du projet GEC

> Guide de navigation : quoi lire, quand.

---

## Fichiers disponibles

| Fichier            | Contenu                                               | Lire quand…                                          |
|--------------------|-------------------------------------------------------|------------------------------------------------------|
| `CLAUDE.md`        | Stack, architecture, modèles, conventions, déploiement | En début de session ou avant d'écrire du code        |
| `primer.md`        | État actuel, dernières sessions, TODOs actifs          | En début de chaque session pour reprendre le fil     |
| `deep-context.md`  | Domaine métier, flux courrier, logique sécurité        | Avant de toucher aux règles d'accès ou au métier GEC |
| `memory/MEMORY.md` | Index des apprentissages et décisions du projet        | Pour retrouver des décisions ou patterns validés     |

---

## Workflow début de session

1. Lire `primer.md` → état actuel + TODO en cours
2. Lire `CLAUDE.md` → rappel architecture si besoin
3. Identifier la tâche → lire `deep-context.md` si règles métier impliquées

## Workflow pendant la session

- Modifier le code en local
- Lancer `/validate-and-push` (screenshots → validation → commit → PR)
- Ne jamais push sur `main` directement

## Workflow fin de session

- Mettre à jour `primer.md` : cocher ce qui est fait, ajouter les nouvelles étapes
- Si une décision architecturale ou pattern inhabituel a été validé → ajouter dans `memory/MEMORY.md`
