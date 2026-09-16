<#
.SYNOPSIS
    Installe GEC sur Windows Server 2016 (ou plus récent) en une commande.

.DESCRIPTION
    Prérequis déjà installés sur le serveur : Python 3.11 à 3.14 et PostgreSQL.
    Rien n'est téléchargé en dehors des dépendances Python (pip).

    Le script, relançable sans risque :
      1. vérifie Python ;
      2. crée l'environnement Python (.venv) et installe les dépendances ;
      3. crée l'utilisateur et la base PostgreSQL s'ils n'existent pas ;
      4. crée le fichier .env avec des secrets neufs (un .env existant est conservé) ;
      5. installe GEC comme tâche planifiée qui démarre avec le serveur et se relance ;
      6. ouvre le pare-feu (mode Intranet) et vérifie que GEC répond.

    Modes :
      Intranet  GEC écoute directement sur le réseau, en HTTP (par défaut, port 80).
      IIS       GEC écoute sur 127.0.0.1:5004 ; IIS le publie en HTTPS (voir la doc).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File deploy\windows\installer-gec.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File deploy\windows\installer-gec.ps1 -Mode IIS
#>
[CmdletBinding()]
param(
    [ValidateSet('Intranet', 'IIS')]
    [string]$Mode = 'Intranet',
    [int]$Port = 0,
    [string]$Python = '',

    [string]$DbHote = 'localhost',
    [int]$DbPort = 5432,
    [string]$DbNom = 'gec_db',
    [string]$DbUtilisateur = 'gec_user',
    [string]$DbMotDePasse = '',
    [string]$PostgresUtilisateur = 'postgres',
    [string]$PostgresMotDePasse = '',

    [string]$AdminMotDePasse = '',
    [switch]$SansService
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'commun-gec.ps1')

$Racine = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$PythonVenv = Join-Path $Racine '.venv\Scripts\python.exe'
$CheminEnv = Join-Path $Racine '.env'
if ($Port -eq 0) { if ($Mode -eq 'Intranet') { $Port = 80 } else { $Port = 5004 } }

function Read-Secret([string]$Invite, [int]$LongueurMin) {
    while ($true) {
        $saisie = Read-Host -Prompt $Invite -AsSecureString
        $clair = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($saisie))
        if ($clair.Length -ge $LongueurMin) { return $clair }
        Write-Alerte "au moins $LongueurMin caractères."
    }
}

Write-Host ''
Write-Host "Installation de GEC — mode $Mode, port $Port" -ForegroundColor White
Write-Host "Dossier : $Racine"

if (-not (Test-Path (Join-Path $Racine 'run_waitress.py'))) {
    Stop-Installation "run_waitress.py introuvable dans $Racine : lancez le script depuis le dossier GEC complet."
}
if (-not $SansService -and -not (Test-Administrateur)) {
    Stop-Installation "ouvrez PowerShell en tant qu'administrateur (clic droit > Exécuter en tant qu'administrateur)."
}

# ─── 1. Python ────────────────────────────────────────────────────────────────
Write-Etape '1/6' 'Python'
$candidats = @()
if ($Python) { $candidats += , @($Python) }
foreach ($v in '3.12', '3.13', '3.14', '3.11') { $candidats += , @('py', "-$v") }
$candidats += , @('python')

$PythonBase = $null
foreach ($c in $candidats) {
    $exe = $c[0]
    $args0 = @()
    if ($c.Count -gt 1) { $args0 = $c[1..($c.Count - 1)] }
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
    $precedent = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $info = & $exe @args0 -c "import sys; print(sys.executable); print('%d.%d' % sys.version_info[:2])" 2>$null
    $code = $LASTEXITCODE; $ErrorActionPreference = $precedent
    if ($code -ne 0 -or -not $info -or @($info).Count -lt 2) { continue }
    $version = [version]@($info)[1]
    if ($version -ge [version]'3.11' -and $version -le [version]'3.14') {
        $PythonBase = @($info)[0]
        Write-Ok "Python $version : $PythonBase"
        break
    }
    Write-Alerte "Python $version ignoré (versions prises en charge : 3.11 à 3.14)."
}
if (-not $PythonBase) {
    Stop-Installation "aucun Python 3.11 à 3.14 trouvé. Installez Python 3.12 depuis python.org (cocher « Add python.exe to PATH »), puis relancez."
}

# ─── 2. Environnement Python ──────────────────────────────────────────────────
Write-Etape '2/6' 'Environnement Python et dépendances'
if (-not (Test-Path $PythonVenv)) {
    Invoke-Natif $PythonBase @('-m', 'venv', (Join-Path $Racine '.venv')) 'création de .venv impossible' -Silencieux | Out-Null
    Write-Ok 'environnement .venv créé'
} else {
    Write-Ok 'environnement .venv existant réutilisé'
}
Invoke-Natif $PythonVenv @('-m', 'pip', 'install', '--disable-pip-version-check', '-q', '--upgrade', 'pip') 'mise à jour de pip impossible' -Silencieux | Out-Null
Invoke-Natif $PythonVenv @('-m', 'pip', 'install', '--disable-pip-version-check', '-q', '-r', (Join-Path $Racine 'requirements.txt')) 'installation des dépendances impossible' -Silencieux | Out-Null
Write-Ok 'dépendances installées'

foreach ($dossier in 'logs', 'uploads', 'static\uploads', 'static\uploads\profiles', 'security\temp', 'backups', 'exports') {
    New-Item -ItemType Directory -Force -Path (Join-Path $Racine $dossier) | Out-Null
}

# ─── 3. Base PostgreSQL ───────────────────────────────────────────────────────
Write-Etape '3/6' 'Base de données PostgreSQL'
$envExiste = Test-Path $CheminEnv
if (-not $envExiste) {
    if (-not $DbMotDePasse) { $DbMotDePasse = Read-Secret "Mot de passe à donner à l'utilisateur « $DbUtilisateur » de la base" 12 }
    if (-not $PostgresMotDePasse) { $PostgresMotDePasse = Read-Secret "Mot de passe du compte PostgreSQL « $PostgresUtilisateur » (choisi à l'installation de PostgreSQL)" 1 }
    $env:GEC_PG_HOTE = $DbHote; $env:GEC_PG_PORT = "$DbPort"
    $env:GEC_PG_ADMIN = $PostgresUtilisateur; $env:GEC_PG_ADMIN_MDP = $PostgresMotDePasse
    $env:GEC_DB_NOM = $DbNom; $env:GEC_DB_UTILISATEUR = $DbUtilisateur; $env:GEC_DB_MDP = $DbMotDePasse
    try {
        Invoke-Natif $PythonVenv @((Join-Path $PSScriptRoot 'preparer_base.py')) 'préparation de la base impossible'
    } finally {
        Remove-Item Env:\GEC_PG_ADMIN_MDP -ErrorAction SilentlyContinue
    }
} else {
    Write-Ok '.env existant : base déjà configurée, étape ignorée'
}

# ─── 4. Fichier .env ──────────────────────────────────────────────────────────
Write-Etape '4/6' 'Configuration (.env)'
if (-not $envExiste -and -not $AdminMotDePasse) {
    $AdminMotDePasse = Read-Secret "Mot de passe du compte super admin « sa.gec001 »" 12
}
$env:GEC_ENV_CHEMIN = $CheminEnv
$env:GEC_ADMIN_MDP = $AdminMotDePasse
if ($Mode -eq 'Intranet') {
    $env:GEC_HOST = '0.0.0.0'; $env:GEC_HTTPS = '0'; $env:GEC_DERRIERE_PROXY = '0'
} else {
    $env:GEC_HOST = '127.0.0.1'; $env:GEC_HTTPS = '1'; $env:GEC_DERRIERE_PROXY = '1'
}
$env:GEC_PORT = "$Port"
try {
    Invoke-Natif $PythonVenv @((Join-Path $PSScriptRoot 'generer_env.py')) 'création du fichier .env impossible'
} finally {
    Remove-Item Env:\GEC_DB_MDP, Env:\GEC_ADMIN_MDP -ErrorAction SilentlyContinue
}
# Le .env contient la clé qui chiffre les données : lecture réservée aux
# Administrateurs (S-1-5-32-544) et à SYSTEM (S-1-5-18), noms indépendants de la langue.
$precedent = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
& icacls $CheminEnv /inheritance:r /grant:r '*S-1-5-32-544:(F)' '*S-1-5-18:(F)' 2>&1 | Out-Null
$ErrorActionPreference = $precedent
Write-Ok '.env accessible aux seuls Administrateurs et SYSTEM'
if (-not $envExiste) {
    Write-Alerte "GARDEZ UNE COPIE DE $CheminEnv HORS DU SERVEUR : sans GEC_MASTER_KEY, les données chiffrées sont perdues."
}

# ─── 5. Démarrage automatique ─────────────────────────────────────────────────
Write-Etape '5/6' 'Démarrage automatique'
Stop-TacheGEC -Port $Port
$occupe = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($occupe) {
    $proprietaire = Get-Process -Id $occupe.OwningProcess -ErrorAction SilentlyContinue
    $nom = if ($proprietaire) { $proprietaire.ProcessName } else { "PID $($occupe.OwningProcess)" }
    $conseil = ''
    if ($occupe.OwningProcess -eq 4) { $conseil = ' (probablement IIS : utilisez -Port 8080, ou -Mode IIS)' }
    Stop-Installation "le port $Port est déjà utilisé par $nom$conseil."
}

if ($SansService) {
    Write-Info 'Option -SansService : test de démarrage uniquement.'
    $journalTest = Join-Path $Racine 'logs\installation-test.log'
    $p = Start-Process -FilePath $PythonVenv -ArgumentList '-X', 'utf8', 'run_waitress.py' `
        -WorkingDirectory $Racine -RedirectStandardOutput $journalTest `
        -RedirectStandardError "$journalTest.err" -WindowStyle Hidden -PassThru
    $repond = Wait-GEC -Port $Port
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    if (-not $repond) {
        Get-Content "$journalTest.err" -Tail 40 -ErrorAction SilentlyContinue | ForEach-Object { Write-Info $_ }
        Stop-Installation "GEC ne répond pas sur le port $Port."
    }
    Write-Ok "GEC démarre et répond (arrêté après le test)."
} else {
    $action = New-ScheduledTaskAction -Execute $PythonVenv `
        -Argument ('-X utf8 "' + (Join-Path $PSScriptRoot 'superviseur_gec.py') + '"') `
        -WorkingDirectory $Racine
    $declencheur = New-ScheduledTaskTrigger -AtStartup
    $compte = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $reglages = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $script:NomTache -Action $action -Trigger $declencheur `
        -Principal $compte -Settings $reglages -Force `
        -Description 'GEC — Gestion Électronique du Courrier (démarre avec le serveur, se relance en cas d''arrêt)' | Out-Null
    Start-ScheduledTask -TaskName $script:NomTache
    Write-Ok "tâche planifiée « $script:NomTache » installée et démarrée (compte SYSTEM)"

    Write-Info 'Attente de la réponse de GEC (premier démarrage : création des tables)...'
    if (-not (Wait-GEC -Port $Port -DelaiSecondes 180)) {
        Show-JournalGEC -Racine $Racine
        Stop-Installation "GEC ne répond pas sur le port $Port après 3 minutes."
    }
    Write-Ok "GEC répond sur le port $Port"
}

# ─── 6. Réseau ────────────────────────────────────────────────────────────────
Write-Etape '6/6' 'Accès réseau'
if ($Mode -eq 'Intranet') {
    $regle = "GEC (HTTP $Port)"
    # Un serveur hors domaine voit souvent son réseau classé « Public » : une règle
    # limitée aux profils Domaine et Privé n'y aurait aucun effet.
    $profils = @('Domain', 'Private')
    $publics = @(Get-NetConnectionProfile -ErrorAction SilentlyContinue |
        Where-Object { $_.NetworkCategory -eq 'Public' })
    if ($publics.Count -gt 0) {
        $profils += 'Public'
        Write-Alerte "réseau « $($publics[0].Name) » classé Public : le port $Port y est aussi ouvert."
    }
    if (-not (Get-NetFirewallRule -DisplayName $regle -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $regle -Direction Inbound -Protocol TCP `
            -LocalPort $Port -Action Allow -Profile $profils | Out-Null
        Write-Ok "pare-feu : port $Port ouvert (profils $($profils -join ', '))"
    } else {
        Set-NetFirewallRule -DisplayName $regle -Profile $profils | Out-Null
        Write-Ok "pare-feu : règle « $regle » présente (profils $($profils -join ', '))"
    }
    $adresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
        Select-Object -ExpandProperty IPAddress
    $suffixe = if ($Port -eq 80) { '' } else { ":$Port" }
    Write-Host ''
    Write-Host 'GEC est installé. Adresses à ouvrir dans un navigateur :' -ForegroundColor Green
    Write-Host "    http://$($env:COMPUTERNAME)$suffixe/" -ForegroundColor Green
    foreach ($a in $adresses) { Write-Host "    http://$a$suffixe/" -ForegroundColor Green }
} else {
    $appcmd = Join-Path $env:windir 'System32\inetsrv\appcmd.exe'
    if (Test-Path $appcmd) {
        foreach ($variable in 'HTTP_X_FORWARDED_FOR', 'HTTP_X_FORWARDED_PROTO', 'HTTP_X_FORWARDED_HOST', 'HTTP_X_REAL_IP') {
            $precedent = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
            & $appcmd set config -section:system.webServer/rewrite/allowedServerVariables "/+[name='$variable']" /commit:apphost 2>&1 | Out-Null
            $ErrorActionPreference = $precedent
        }
        Write-Ok 'IIS : variables serveur autorisées pour URL Rewrite'
    } else {
        Write-Alerte 'IIS non détecté : installez IIS, URL Rewrite et ARR, puis relancez ce script.'
    }
    Write-Host ''
    Write-Host "GEC écoute sur http://127.0.0.1:$Port/ (non exposé au réseau)." -ForegroundColor Green
    Write-Host "Publiez-le avec IIS : deploy\windows\web.config — voir docs\GEC_Deploiement_Windows_Server.md" -ForegroundColor Green
}

Write-Host ''
Write-Host 'Compte initial : sa.gec001 (mot de passe choisi à l''installation)'
Write-Host "Journal        : $(Join-Path $Racine 'logs\gec.log')"
Write-Host "Arrêter        : Stop-ScheduledTask -TaskName GEC"
Write-Host "Démarrer       : Start-ScheduledTask -TaskName GEC"
Write-Host "Mettre à jour  : powershell -ExecutionPolicy Bypass -File deploy\windows\mettre-a-jour-gec.ps1"
