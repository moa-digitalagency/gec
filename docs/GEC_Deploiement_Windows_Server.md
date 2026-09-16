# GEC — Déploiement sur Windows Server 2016

*Mise à jour : septembre 2026. Valable aussi pour Windows Server 2019 et 2022.*

L'installation se fait avec un script PowerShell qui réalise toute la configuration.
Le déploiement Linux (nginx, gunicorn, PM2) est décrit dans `GEC_Installation_Deploiement.md`.

---

## Installation rapide automatique (recommandée)

Serveur avec accès Internet. **Aucun logiciel à installer au préalable, aucune question.**

1. Copier le dossier GEC sur le serveur, par exemple dans `C:\GEC`. Pour une
   archive ZIP téléchargée depuis GitHub : clic droit sur le ZIP › *Propriétés* ›
   cocher **Débloquer**, *avant* d'extraire.
2. **Double-cliquer sur `INSTALLER-GEC.cmd`**, à la racine du dossier.
3. Accepter la demande de droits administrateur, puis patienter (10 à 15 minutes
   selon la connexion : PostgreSQL pèse 350 Mo).

Le script installe au besoin **Python 3.13** et **PostgreSQL 16**, génère tous les
mots de passe, installe GEC comme tâche planifiée et ouvre le pare-feu. À la fin :

- **`C:\GEC\IDENTIFIANTS-GEC.txt`** contient les adresses d'accès, le mot de passe du
  compte `sa.gec001` et ceux de la base. Il n'est lisible que par les administrateurs.
- **Recopier ce fichier et `C:\GEC\.env` hors du serveur**, puis supprimer
  `IDENTIFIANTS-GEC.txt` du serveur et changer le mot de passe de `sa.gec001` dans GEC.

| Point | Détail |
|---|---|
| Déjà installés ? | Un Python 3.11 à 3.14 existant est réutilisé. Un PostgreSQL existant aussi : c'est alors le seul cas où le mot de passe `postgres` est demandé |
| Intégrité | Installateur Python contrôlé par son empreinte SHA-256 publiée par python.org et sa signature numérique ; installateur PostgreSQL par la signature numérique d'EnterpriseDB |
| Relance | Sans risque : rien n'est retéléchargé (dossier `telechargements`), ni les mots de passe ni `.env` ne sont régénérés |
| Journal | `C:\GEC\logs\installation-rapide-AAAAMMJJ-HHMMSS.log`, à envoyer au support en cas d'échec |
| Options | `INSTALLER-GEC.cmd -Port 8080` ou `INSTALLER-GEC.cmd -Mode IIS`, depuis une invite de commandes |

> Sans accès Internet, suivre l'installation manuelle ci-dessous.

---

## Installation manuelle en 3 étapes

### 1. Installer les deux prérequis

| Logiciel | Où le trouver | À noter pendant l'installation |
|---|---|---|
| **Python 3.12** | python.org › Downloads › Windows installer (64-bit) | Cocher **« Add python.exe to PATH »** |
| **PostgreSQL** (14 ou plus récent) | postgresql.org › Download › Windows (installateur EnterpriseDB) | **Noter le mot de passe** du compte `postgres` |

Python 3.11, 3.13 et 3.14 fonctionnent aussi. Rien d'autre n'est à installer :
ni Git, ni IIS, ni outil de service.

### 2. Copier GEC sur le serveur

Au choix :

- **Sans Git** : sur github.com (connecté au compte qui a accès au dépôt), ouvrir
  `moa-digitalagency/gec` › **Code** › **Download ZIP**, puis extraire l'archive dans
  `C:\GEC` (le dossier doit contenir directement `run_waitress.py`).
- **Avec Git** : `git clone https://github.com/moa-digitalagency/gec.git C:\GEC`

### 3. Lancer l'installateur

Ouvrir **PowerShell en tant qu'administrateur** (clic droit › *Exécuter en tant
qu'administrateur*), puis :

```powershell
cd C:\GEC
powershell -ExecutionPolicy Bypass -File deploy\windows\installer-gec.ps1
```

Le script demande trois mots de passe :

1. celui à donner à l'utilisateur `gec_user` de la base (au moins 12 caractères) ;
2. celui du compte `postgres`, choisi à l'installation de PostgreSQL ;
3. celui du compte super admin de GEC, **`sa.gec001`** (au moins 12 caractères).

À la fin, il affiche les adresses où ouvrir GEC, par exemple `http://SRV-GEC/`.

> **Sauvegardez `C:\GEC\.env` hors du serveur** (clé USB, coffre-fort de mots de
> passe). Il contient `GEC_MASTER_KEY`, la clé qui chiffre les courriers et les
> pièces jointes : si elle est perdue, ces données sont **définitivement illisibles**.

---

## Ce que fait l'installateur

Le script peut être relancé sans risque : il conserve la base et le fichier `.env`
existants.

| Étape | Détail |
|---|---|
| 1. Python | Cherche Python 3.11 à 3.14 (`py -3.12`, puis les autres versions, puis `python`) |
| 2. Dépendances | Crée `C:\GEC\.venv` et y installe les dépendances |
| 3. Base | Crée l'utilisateur `gec_user` et la base `gec_db` en UTF-8 s'ils n'existent pas |
| 4. `.env` | Génère des secrets neufs ; un `.env` existant n'est **jamais** régénéré. Lecture réservée aux Administrateurs et à SYSTEM |
| 5. Démarrage | Tâche planifiée **GEC** : démarre avec le serveur, sous le compte SYSTEM, et relance GEC s'il s'arrête |
| 6. Réseau | Ouvre le port dans le pare-feu et affiche les adresses d'accès |

Les tables sont créées au premier démarrage de GEC ; aucune commande de migration
n'est à lancer.

---

## Deux modes d'installation

| | **Intranet** (par défaut) | **IIS** |
|---|---|---|
| Accès | `http://nom-du-serveur/` | `https://gec.exemple.cd/` |
| Chiffrement réseau | Non (HTTP simple) | Oui (certificat installé dans IIS) |
| GEC écoute sur | toutes les interfaces, port 80 | `127.0.0.1:5004` uniquement |
| À installer en plus | rien | IIS, URL Rewrite, Application Request Routing |
| Usage adapté | réseau interne d'une administration | accès depuis Internet, ou exigence de HTTPS |

```powershell
# Intranet sur un autre port (si le port 80 est déjà pris)
powershell -ExecutionPolicy Bypass -File deploy\windows\installer-gec.ps1 -Port 8080

# Derrière IIS
powershell -ExecutionPolicy Bypass -File deploy\windows\installer-gec.ps1 -Mode IIS
```

### Paramètres

| Paramètre | Défaut | Rôle |
|---|---|---|
| `-Mode` | `Intranet` | `Intranet` ou `IIS` |
| `-Port` | 80 (Intranet), 5004 (IIS) | Port d'écoute de GEC |
| `-Python` | détection automatique | Chemin d'un `python.exe` précis |
| `-DbHote`, `-DbPort` | `localhost`, `5432` | Serveur PostgreSQL |
| `-DbNom`, `-DbUtilisateur` | `gec_db`, `gec_user` | Base et utilisateur à créer |
| `-PostgresUtilisateur` | `postgres` | Compte administrateur de PostgreSQL |
| `-SansService` | — | Installe et teste le démarrage, sans tâche planifiée |

Les mots de passe peuvent aussi être passés en paramètres (`-DbMotDePasse`,
`-PostgresMotDePasse`, `-AdminMotDePasse`) pour une installation sans questions ;
ils apparaissent alors dans l'historique de PowerShell.

---

## Au quotidien

Dans PowerShell en administrateur :

| Action | Commande |
|---|---|
| Arrêter GEC | `Stop-ScheduledTask -TaskName GEC` |
| Démarrer GEC | `Start-ScheduledTask -TaskName GEC` |
| Lire le journal | `Get-Content C:\GEC\logs\gec.log -Tail 50` |
| Mettre à jour (Git) | `powershell -ExecutionPolicy Bypass -File deploy\windows\mettre-a-jour-gec.ps1` |
| Mettre à jour (ZIP) | `powershell -ExecutionPolicy Bypass -File deploy\windows\mettre-a-jour-gec.ps1 -Archive C:\Temp\gec-main.zip` |

La mise à jour par archive n'écrase jamais `.env`, `.venv`, `logs`, `uploads`,
`static\uploads`, `backups`, `exports` ni `security\temp`.

Le journal tourne automatiquement au-delà de 20 Mo (5 fichiers conservés).

---

## Mode IIS (HTTPS)

1. **Gestionnaire de serveur** › Ajouter des rôles › **Serveur Web (IIS)**.
2. Installer **URL Rewrite 2.1** et **Application Request Routing 3.0**
   (téléchargements Microsoft).
3. Gestionnaire IIS › nœud du serveur › **Application Request Routing Cache** ›
   *Server Proxy Settings* › cocher **Enable proxy**.
4. Lancer `installer-gec.ps1 -Mode IIS` : il autorise les variables serveur dont
   `web.config` a besoin.
5. Créer un site IIS pointant sur un dossier vide, y copier
   `deploy\windows\web.config`, puis lier le certificat HTTPS au site.

Le `web.config` relaie tout vers `127.0.0.1:5004`, transmet l'adresse réelle des
utilisateurs pour le journal d'audit, et relève la taille maximale des envois à
100 Mo (IIS refuse au-delà de 30 Mo par défaut).

---

## Dépannage

| Message ou symptôme | Cause | Solution |
|---|---|---|
| `aucun Python 3.11 à 3.14 trouvé` | Python absent, ou pas dans le PATH | Réinstaller Python 3.12 en cochant « Add python.exe to PATH », rouvrir PowerShell |
| `connexion à PostgreSQL impossible avec le compte « postgres »` | Mot de passe `postgres` erroné, ou service arrêté | Vérifier le service *postgresql-x64-…* dans `services.msc` |
| `le port 80 est déjà utilisé par System` | IIS occupe déjà le port 80 | `-Port 8080`, ou `-Mode IIS` |
| GEC s'ouvre sur le serveur mais pas depuis un autre poste | Pare-feu ou pare-feu réseau intermédiaire | Vérifier la règle « GEC (HTTP 80) » dans le Pare-feu Windows |
| `signature numérique … invalide ou inattendue` | Certificats racines absents sur un serveur jamais mis à jour | Lancer Windows Update, puis relancer `INSTALLER-GEC.cmd` |
| `téléchargement impossible` | Pas d'accès Internet, ou proxy d'entreprise | Vérifier l'accès à python.org et get.enterprisedb.com, ou installer manuellement |
| « Session de sécurité expirée » à chaque connexion | GEC installé en mode IIS mais ouvert en HTTP | Ouvrir l'adresse HTTPS publiée par IIS, ou réinstaller en mode Intranet |
| `GEC ne répond pas … après 3 minutes` | Erreur au démarrage | Lire `C:\GEC\logs\gec.log` |
| `.env existant incomplet ou invalide` | `.env` modifié à la main | Le corriger à la main ; il n'est jamais régénéré, pour protéger la clé |

---

## Particularités de Windows prises en compte

Ces points, invisibles sous Linux, sont corrigés dans le code et vérifiés
automatiquement sous Windows à chaque modification (job CI « Windows Server ») :

- **Pièces jointes déchiffrées** : Windows refuse d'effacer un fichier ouvert. Le
  fichier déchiffré pour un téléchargement est supprimé après la fin de l'envoi, et
  les fichiers laissés par un arrêt brutal sont effacés au démarrage.
- **Encodage** : Python écrit en cp1252 par défaut sous Windows. Tous les fichiers
  texte de GEC sont lus et écrits en UTF-8, et GEC tourne en mode UTF-8.
- **`.env` du Bloc-notes** : enregistré en UTF-8 avec BOM, il est lu correctement.
- **HTTP simple** : en mode Intranet, le cookie de session n'exige pas HTTPS
  (`GEC_HTTPS=0`), sans quoi aucune connexion ne serait possible.
- **Adresse des utilisateurs** : sans proxy (`GEC_DERRIERE_PROXY=0`), les en-têtes
  `X-Real-IP` et `X-Forwarded-For` envoyés par le navigateur sont ignorés, pour qu'un
  client ne puisse pas contourner la limitation des tentatives de connexion.
- **Démarrage du serveur** : si GEC démarre avant PostgreSQL, il est relancé
  automatiquement jusqu'à ce que la base réponde.
