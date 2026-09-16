<#
.SYNOPSIS
    Installation rapide et automatique de GEC sur Windows Server 2016 (ou plus récent).

.DESCRIPTION
    Lancement : double-clic sur INSTALLER-GEC.cmd, à la racine du dossier GEC.
    Aucune question (sauf le mot de passe « postgres » si PostgreSQL était déjà
    installé avant GEC). Accès Internet requis.

      1. vérifie Windows et demande les droits administrateur ;
      2. installe Python 3.13 si aucun Python 3.11 à 3.14 n'est présent ;
      3. installe PostgreSQL 16 si PostgreSQL n'est pas déjà installé ;
      4. génère des mots de passe forts ;
      5. lance installer-gec.ps1 (dépendances, base, .env, démarrage automatique, pare-feu) ;
      6. écrit les identifiants dans IDENTIFIANTS-GEC.txt, lisible par les seuls administrateurs.

    Relançable : sur une installation existante, rien n'est retéléchargé ni régénéré.
    Journal complet : logs\installation-rapide-*.log
#>
[CmdletBinding()]
param(
    [ValidateSet('Intranet', 'IIS')]
    [string]$Mode = 'Intranet',
    [int]$Port = 0,
    # Uniquement si PostgreSQL était déjà installé sur le serveur avant GEC.
    [string]$PostgresMotDePasse = '',
    # Réinstaller même si présents : sert aux tests automatisés.
    [switch]$ToujoursInstallerPython,
    [switch]$ToujoursInstallerPostgreSQL,
    # Ne pas attendre « Entrée » à la fin (exécution automatisée).
    [switch]$SansPause
)

$ErrorActionPreference = 'Stop'
# Sous PowerShell 5.1, la barre de progression ralentit fortement les téléchargements.
$ProgressPreference = 'SilentlyContinue'
. (Join-Path $PSScriptRoot 'commun-gec.ps1')

# Versions installées quand le serveur n'en a pas.
$PythonVersion = '3.13.15'
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
# Empreinte publiée par python.org pour ce fichier.
$PythonSha256 = 'EDEC09C4853AEAE9AC36EFB8C9F95B6B8E2FEE65EEE56D9767A8B7C69C574403'
$PostgresVersion = '16.15'
$PostgresMajeure = '16'
$PostgresUrl = "https://get.enterprisedb.com/postgresql/postgresql-$PostgresVersion-1-windows-x64.exe"

$Racine = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$DossierTelechargements = Join-Path $Racine 'telechargements'
$CheminEnv = Join-Path $Racine '.env'
$CheminIdentifiants = Join-Path $Racine 'IDENTIFIANTS-GEC.txt'

function Wait-Fermeture {
    if (-not $SansPause) {
        Write-Host ''
        Read-Host 'Appuyez sur Entrée pour fermer cette fenêtre' | Out-Null
    }
}

# ─── Droits administrateur : relance élevée si nécessaire ─────────────────────
if (-not (Test-Administrateur)) {
    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"")
    foreach ($p in $PSBoundParameters.GetEnumerator()) {
        if ($p.Value -is [System.Management.Automation.SwitchParameter]) {
            if ($p.Value.IsPresent) { $arguments += "-$($p.Key)" }
        } else {
            $arguments += "-$($p.Key)", "`"$($p.Value)`""
        }
    }
    Write-Host "Droits administrateur nécessaires : confirmez dans la fenêtre Windows qui s'ouvre."
    try {
        Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $arguments | Out-Null
    } catch {
        Write-Host "Élévation refusée : l'installation n'a pas été lancée." -ForegroundColor Red
        Wait-Fermeture
        exit 1
    }
    exit 0
}

function Get-Telechargement([string]$Url, [string]$NomFichier) {
    New-Item -ItemType Directory -Force -Path $DossierTelechargements | Out-Null
    $cible = Join-Path $DossierTelechargements $NomFichier
    if ((Test-Path $cible) -and (Get-Item $cible).Length -gt 0) {
        Write-Ok "$NomFichier déjà téléchargé"
        return $cible
    }
    $partiel = "$cible.partiel"
    for ($essai = 1; $essai -le 3; $essai++) {
        try {
            Write-Info "Téléchargement de $NomFichier (essai $essai/3)..."
            Invoke-WebRequest -Uri $Url -OutFile $partiel -UseBasicParsing
            Move-Item -Force $partiel $cible
            $mo = [math]::Round((Get-Item $cible).Length / 1MB)
            Write-Ok "$NomFichier téléchargé ($mo Mo)"
            return $cible
        } catch {
            Remove-Item $partiel -ErrorAction SilentlyContinue
            if ($essai -eq 3) {
                Stop-Installation "téléchargement impossible : $Url — vérifiez l'accès Internet du serveur ($($_.Exception.Message))"
            }
            Start-Sleep -Seconds 10
        }
    }
}

function Test-SignatureEditeur([string]$Fichier, [string]$Editeur) {
    $signature = Get-AuthenticodeSignature -FilePath $Fichier
    $sujet = if ($signature.SignerCertificate) { $signature.SignerCertificate.Subject } else { '(aucun certificat)' }
    Write-Info "Signature : $($signature.Status) — $sujet"
    if ($signature.Status -ne 'Valid' -or $sujet -notmatch $Editeur) {
        Remove-Item $Fichier -Force -ErrorAction SilentlyContinue
        Stop-Installation ("signature numérique de $(Split-Path $Fichier -Leaf) invalide ou inattendue " +
            "(attendu : $Editeur). Fichier supprimé. Si le serveur n'a jamais reçu les mises à jour " +
            "Windows, ses certificats racines peuvent manquer : lancez Windows Update puis relancez.")
    }
}

function Get-PythonDuRegistre([string]$Version) {
    <#
    Emplacement déclaré par Python lui-même dans le registre (PEP 514), celui que lit
    le lanceur py. Une version déjà installée ailleurs est mise à jour sur place par
    l'installateur, qui ignore alors le dossier par défaut Program Files\PythonXY.
    #>
    foreach ($base in 'HKLM:\SOFTWARE\Python\PythonCore', 'HKCU:\SOFTWARE\Python\PythonCore') {
        $cle = Join-Path $base "$Version\InstallPath"
        if (-not (Test-Path $cle)) { continue }
        $valeurs = Get-ItemProperty -Path $cle
        if ($valeurs.ExecutablePath -and (Test-Path $valeurs.ExecutablePath)) { return $valeurs.ExecutablePath }
        $dossier = $valeurs.'(default)'
        if ($dossier -and (Test-Path (Join-Path $dossier 'python.exe'))) { return (Join-Path $dossier 'python.exe') }
    }
    return $null
}

function Find-PythonCompatible {
    $candidats = @()
    foreach ($v in '3.13', '3.12', '3.14', '3.11') {
        $exe = Get-PythonDuRegistre $v
        if ($exe) { $candidats += , @($exe) }
    }
    foreach ($v in '3.13', '3.12', '3.14', '3.11') { $candidats += , @('py', "-$v") }
    $candidats += , @('python')
    foreach ($c in $candidats) {
        $exe = $c[0]
        $suite = @(); if ($c.Count -gt 1) { $suite = $c[1..($c.Count - 1)] }
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue) -and -not (Test-Path $exe)) { continue }
        $precedent = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        $info = & $exe @suite -c "import sys; print(sys.executable); print('%d.%d' % sys.version_info[:2])" 2>$null
        $code = $LASTEXITCODE; $ErrorActionPreference = $precedent
        if ($code -ne 0 -or @($info).Count -lt 2) { continue }
        $version = [version]@($info)[1]
        if ($version -ge [version]'3.11' -and $version -le [version]'3.14') { return @($info)[0] }
    }
    return $null
}

function Get-VersionService($Nom) {
    # « postgresql-x64-16 » → 16 ; comparaison numérique (en texte, « 9.6 » passerait devant « 16 »).
    if ($Nom -match '(\d+)(?:\.\d+)?$') { return [int]$Matches[1] }
    return 0
}

function Get-ServicePostgres {
    <#
    Un serveur peut garder plusieurs PostgreSQL (ancienne version arrêtée, par exemple) :
    on retient celui qui tourne, sinon la version la plus récente.
    #>
    $services = @(Get-Service -Name 'postgresql*' -ErrorAction SilentlyContinue)
    $actif = $services | Where-Object { $_.Status -eq 'Running' } |
        Sort-Object { Get-VersionService $_.Name } -Descending | Select-Object -First 1
    if ($actif) { return $actif }
    return $services | Sort-Object { Get-VersionService $_.Name } -Descending | Select-Object -First 1
}

function Get-DossierBinPostgres {
    $choisi = Get-ServicePostgres
    if (-not $choisi) { return $null }
    $service = Get-CimInstance Win32_Service -Filter "Name = '$($choisi.Name)'" -ErrorAction SilentlyContinue
    if ($service -and $service.PathName -match '^"?([^"]+\\bin)\\pg_ctl\.exe') { return $Matches[1] }
    return $null
}

$horodatage = Get-Date -Format 'yyyyMMdd-HHmmss'
New-Item -ItemType Directory -Force -Path (Join-Path $Racine 'logs') | Out-Null
$journal = Join-Path $Racine "logs\installation-rapide-$horodatage.log"
Start-Transcript -Path $journal | Out-Null
$codeSortie = 0

try {
    Write-Host ''
    Write-Host 'GEC — installation rapide automatique' -ForegroundColor White
    Write-Host "Dossier : $Racine"

    # ─── 1. Système ───────────────────────────────────────────────────────────
    Write-Etape 'A' 'Système'
    $os = Get-CimInstance Win32_OperatingSystem
    Write-Ok "$($os.Caption) (build $($os.BuildNumber))"
    if ([int]$os.BuildNumber -lt 14393) {
        Stop-Installation 'Windows Server 2016 (build 14393) ou plus récent requis.'
    }
    if ($Racine -match '\\Users\\') {
        Write-Alerte "GEC est dans un profil utilisateur ($Racine). Préférez C:\GEC : un nettoyage du profil supprimerait l'application."
    }
    # Windows Server 2016 négocie encore d'anciennes versions de TLS que python.org
    # et EnterpriseDB refusent : TLS 1.2 imposé pour les téléchargements.
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    $installationExistante = Test-Path $CheminEnv
    if ($installationExistante) {
        Write-Ok 'GEC déjà installé ici (.env présent) : vérification et remise en état, sans nouveaux mots de passe.'
    }

    # ─── 2. Python ────────────────────────────────────────────────────────────
    Write-Etape 'B' 'Python'
    $python = $null
    if (-not $ToujoursInstallerPython) { $python = Find-PythonCompatible }
    if ($python) {
        Write-Ok "Python déjà présent : $python"
    } else {
        $installeur = Get-Telechargement $PythonUrl "python-$PythonVersion-amd64.exe"
        $empreinte = (Get-FileHash -Algorithm SHA256 $installeur).Hash
        if ($empreinte -ne $PythonSha256) {
            Remove-Item $installeur -Force
            Stop-Installation "empreinte SHA-256 de l'installateur Python incorrecte ($empreinte) : fichier supprimé, relancez."
        }
        Write-Ok 'empreinte SHA-256 conforme à celle publiée par python.org'
        Test-SignatureEditeur $installeur 'Python Software Foundation'
        Write-Info "Installation silencieuse de Python $PythonVersion..."
        $p = Start-Process -FilePath $installeur -Wait -PassThru -ArgumentList @(
            '/quiet', 'InstallAllUsers=1', 'PrependPath=1', 'Include_launcher=1',
            'InstallLauncherAllUsers=1', 'Include_test=0', 'Include_doc=0',
            '/log', "`"$(Join-Path $Racine "logs\python-installation-$horodatage.log")`"")
        if ($p.ExitCode -ne 0 -and $p.ExitCode -ne 3010) {
            Stop-Installation "installation de Python en échec (code $($p.ExitCode)) — voir logs\python-installation-$horodatage.log"
        }
        $python = Get-PythonDuRegistre '3.13'
        if (-not $python) {
            Stop-Installation "Python 3.13 introuvable dans le registre après installation — voir logs\python-installation-$horodatage.log"
        }
        $precedent = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        $versionInstallee = (& $python -c "import platform; print(platform.python_version())" 2>$null)
        $ErrorActionPreference = $precedent
        if ($versionInstallee -ne $PythonVersion) {
            Stop-Installation "Python $PythonVersion attendu, $versionInstallee trouvé ($python)."
        }
        Write-Ok "Python $versionInstallee installé : $python"
    }

    # ─── 3. PostgreSQL ────────────────────────────────────────────────────────
    Write-Etape 'C' 'PostgreSQL'
    $serviceExistant = Get-ServicePostgres
    $postgresInstalleParGEC = $false
    $motsDePasse = $null

    if (-not $installationExistante) {
        $sortie = Invoke-Natif $python @((Join-Path $PSScriptRoot 'mots_de_passe.py')) 'génération des mots de passe impossible' -Silencieux
        $motsDePasse = ($sortie -join '') | ConvertFrom-Json
        Write-Ok 'mots de passe générés'
    }

    if ($serviceExistant -and -not $ToujoursInstallerPostgreSQL) {
        Write-Ok "PostgreSQL déjà installé (service $($serviceExistant.Name))"
        if ($serviceExistant.Status -ne 'Running') {
            Set-Service -Name $serviceExistant.Name -StartupType Automatic
            Start-Service -Name $serviceExistant.Name
            Write-Ok 'service PostgreSQL démarré'
        }
        if (-not $installationExistante -and -not $PostgresMotDePasse) {
            Write-Alerte "PostgreSQL était déjà installé : son mot de passe « postgres » est nécessaire pour créer la base de GEC."
            $saisie = Read-Host -Prompt 'Mot de passe du compte postgres' -AsSecureString
            $PostgresMotDePasse = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                [Runtime.InteropServices.Marshal]::SecureStringToBSTR($saisie))
        }
    } elseif (-not $installationExistante -or $ToujoursInstallerPostgreSQL) {
        $installeur = Get-Telechargement $PostgresUrl "postgresql-$PostgresVersion-1-windows-x64.exe"
        Test-SignatureEditeur $installeur 'EnterpriseDB'
        if (-not $motsDePasse) { Stop-Installation 'mot de passe postgres indisponible.' }
        $PostgresMotDePasse = $motsDePasse.postgres

        $prefixe = Join-Path $env:ProgramFiles "PostgreSQL\$PostgresMajeure"
        # Le mot de passe passe par un fichier d'options, pas par la ligne de commande
        # (visible dans la liste des processus pendant l'installation).
        $options = Join-Path $env:TEMP "gec-postgresql-$horodatage.txt"
        [IO.File]::WriteAllText($options, "superpassword=$PostgresMotDePasse`r`n", (New-Object Text.UTF8Encoding $false))
        try {
            Write-Info "Installation silencieuse de PostgreSQL $PostgresVersion (plusieurs minutes)..."
            $p = Start-Process -FilePath $installeur -Wait -PassThru -ArgumentList @(
                '--mode', 'unattended', '--unattendedmodeui', 'none',
                '--optionfile', "`"$options`"",
                '--serverport', '5432',
                '--prefix', "`"$prefixe`"", '--datadir', "`"$(Join-Path $prefixe 'data')`"",
                '--servicename', "postgresql-x64-$PostgresMajeure",
                '--disable-components', 'pgAdmin,stackbuilder')
        } finally {
            Remove-Item $options -Force -ErrorAction SilentlyContinue
        }
        if ($p.ExitCode -ne 0) {
            Stop-Installation "installation de PostgreSQL en échec (code $($p.ExitCode)) — journal : $env:TEMP\install-postgresql.log"
        }
        $postgresInstalleParGEC = $true
        Write-Ok "PostgreSQL $PostgresVersion installé (service postgresql-x64-$PostgresMajeure)"
    }

    # pg_dump et psql dans le PATH système : utilisés par les sauvegardes de GEC.
    $binPostgres = Get-DossierBinPostgres
    if ($binPostgres) {
        $cheminSysteme = [Environment]::GetEnvironmentVariable('Path', 'Machine')
        if (($cheminSysteme -split ';') -notcontains $binPostgres) {
            [Environment]::SetEnvironmentVariable('Path', "$cheminSysteme;$binPostgres", 'Machine')
            Write-Ok "outils PostgreSQL ajoutés au PATH système ($binPostgres)"
        }
        $env:Path = "$env:Path;$binPostgres"
    }

    Write-Info 'Attente de PostgreSQL sur le port 5432...'
    $limite = (Get-Date).AddSeconds(90)
    while (-not (Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue)) {
        if ((Get-Date) -gt $limite) { Stop-Installation 'PostgreSQL ne répond pas sur le port 5432.' }
        Start-Sleep -Seconds 2
    }
    Write-Ok 'PostgreSQL répond'

    # ─── 4. GEC ───────────────────────────────────────────────────────────────
    Write-Etape 'D' 'Installation de GEC'
    $parametres = @{ Mode = $Mode; Python = $python }
    if ($Port -gt 0) { $parametres.Port = $Port }
    if (-not $installationExistante) {
        $parametres.DbMotDePasse = $motsDePasse.base
        $parametres.AdminMotDePasse = $motsDePasse.admin
        $parametres.PostgresMotDePasse = $PostgresMotDePasse
    }
    & (Join-Path $PSScriptRoot 'installer-gec.ps1') @parametres

    # ─── 5. Identifiants ──────────────────────────────────────────────────────
    if (-not $installationExistante) {
        $portFinal = [int](Read-ValeurEnv -CheminEnv $CheminEnv -Cle 'GEC_PORT' -Defaut '80')
        $suffixe = if ($portFinal -eq 80) { '' } else { ":$portFinal" }
        $adresses = @("http://$($env:COMPUTERNAME)$suffixe/")
        if ($Mode -eq 'Intranet') {
            $adresses += Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
                Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
                ForEach-Object { "http://$($_.IPAddress)$suffixe/" }
        } else {
            $adresses = @("adresse HTTPS publiée par IIS (GEC écoute sur http://127.0.0.1:$portFinal/)")
        }
        $lignesPostgres = if ($postgresInstalleParGEC) {
            "  Compte postgres       : postgres`r`n  Mot de passe postgres : $PostgresMotDePasse"
        } else {
            '  Compte postgres       : inchangé (PostgreSQL était déjà installé)'
        }
        $texte = @"
GEC — IDENTIFIANTS D'INSTALLATION
Créé le $(Get-Date -Format 'dd/MM/yyyy à HH:mm') sur $($env:COMPUTERNAME)

À FAIRE MAINTENANT :
  1. Recopier ce fichier ET le fichier .env dans un lieu sûr hors du serveur
     (coffre-fort de mots de passe, clé USB rangée).
  2. Supprimer ensuite ce fichier du serveur.
  3. Se connecter à GEC et changer le mot de passe du compte sa.gec001.

Sans le fichier .env (clé GEC_MASTER_KEY), les courriers et pièces jointes
chiffrés sont définitivement illisibles.

ACCÈS À GEC
$(($adresses | ForEach-Object { "  $_" }) -join "`r`n")
  Identifiant  : sa.gec001
  Mot de passe : $($motsDePasse.admin)

BASE DE DONNÉES
  Serveur      : localhost:5432
  Base         : gec_db
  Utilisateur  : gec_user
  Mot de passe : $($motsDePasse.base)
$lignesPostgres

FICHIERS
  Application  : $Racine
  Configuration: $CheminEnv
  Journal      : $(Join-Path $Racine 'logs\gec.log')
"@
        # UTF-8 avec BOM : le Bloc-notes de Windows Server 2016 affiche alors les accents correctement.
        [IO.File]::WriteAllText($CheminIdentifiants, $texte, (New-Object Text.UTF8Encoding $true))
        $precedent = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        & icacls $CheminIdentifiants /inheritance:r /grant:r '*S-1-5-32-544:(F)' '*S-1-5-18:(F)' 2>&1 | Out-Null
        $ErrorActionPreference = $precedent

        Write-Host ''
        Write-Host '════════════════════════════════════════════════════════════════' -ForegroundColor Green
        Write-Host ' GEC est installé.' -ForegroundColor Green
        Write-Host " Identifiants : $CheminIdentifiants" -ForegroundColor Green
        Write-Host ' (lisible par les administrateurs uniquement)' -ForegroundColor Green
        Write-Host ' Sauvegardez ce fichier et .env hors du serveur, puis supprimez' -ForegroundColor Green
        Write-Host ' IDENTIFIANTS-GEC.txt du serveur.' -ForegroundColor Green
        Write-Host '════════════════════════════════════════════════════════════════' -ForegroundColor Green
    } else {
        Write-Host ''
        Write-Host 'GEC est vérifié et en marche. Identifiants inchangés.' -ForegroundColor Green
    }
    Write-Host "Journal de cette installation : $journal"
} catch {
    $codeSortie = 1
    Write-Host ''
    Write-Host "L'installation s'est arrêtée : $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Envoyez ce fichier au support : $journal" -ForegroundColor Red
} finally {
    Stop-Transcript | Out-Null
}

Wait-Fermeture
exit $codeSortie
