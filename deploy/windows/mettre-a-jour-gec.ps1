<#
.SYNOPSIS
    Met GEC à jour sur Windows Server, avec ou sans git.

.DESCRIPTION
    Arrête GEC, récupère la nouvelle version, met à jour les dépendances et
    redémarre GEC. Les migrations de la base s'appliquent au redémarrage.

    Avec git        : le dossier est un clone, le script fait « git pull ».
    Sans git        : téléchargez l'archive ZIP depuis GitHub et passez-la avec -Archive.
                      Ne sont jamais écrasés : .env, .venv, logs, uploads,
                      static\uploads, backups, exports, security\temp.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File deploy\windows\mettre-a-jour-gec.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File deploy\windows\mettre-a-jour-gec.ps1 -Archive C:\Temp\gec-main.zip
#>
[CmdletBinding()]
param(
    [string]$Archive = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'commun-gec.ps1')

$Racine = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$PythonVenv = Join-Path $Racine '.venv\Scripts\python.exe'
$CheminEnv = Join-Path $Racine '.env'

if (-not (Test-Administrateur)) {
    Stop-Installation "ouvrez PowerShell en tant qu'administrateur."
}
if (-not (Test-Path $PythonVenv) -or -not (Test-Path $CheminEnv)) {
    Stop-Installation "GEC n'est pas installé dans $Racine : lancez d'abord installer-gec.ps1."
}
$Port = [int](Read-ValeurEnv -CheminEnv $CheminEnv -Cle 'GEC_PORT' -Defaut '5004')

Write-Host ''
Write-Host "Mise à jour de GEC — $Racine" -ForegroundColor White

# ─── 1. Arrêt ─────────────────────────────────────────────────────────────────
Write-Etape '1/4' 'Arrêt de GEC'
Stop-TacheGEC -Port $Port
Write-Ok 'GEC arrêté'

# ─── 2. Nouvelle version ──────────────────────────────────────────────────────
Write-Etape '2/4' 'Récupération de la nouvelle version'
if ($Archive) {
    if (-not (Test-Path $Archive)) { Stop-Installation "archive introuvable : $Archive" }
    $extraction = Join-Path ([IO.Path]::GetTempPath()) ("gec-maj-" + [guid]::NewGuid().ToString('N'))
    Expand-Archive -Path $Archive -DestinationPath $extraction -Force
    # L'archive GitHub contient un dossier racine (gec-main\...) : on le retrouve.
    $source = Get-ChildItem -Path $extraction -Recurse -Filter 'run_waitress.py' -File |
        Select-Object -First 1 | ForEach-Object { $_.DirectoryName }
    if (-not $source) { Stop-Installation "l'archive ne contient pas GEC (run_waitress.py absent)." }

    $precedent = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $exclusDossiers = @('.venv', '.git', 'logs', 'uploads', 'backups', 'exports', 'instance') |
        ForEach-Object { Join-Path $source $_ }
    $exclusDossiers += (Join-Path $source 'static\uploads'), (Join-Path $source 'security\temp')
    & robocopy $source $Racine /E /NFL /NDL /NJH /NJS /NP /XF '.env' /XD @exclusDossiers | Out-Null
    $codeCopie = $LASTEXITCODE
    $ErrorActionPreference = $precedent
    Remove-Item -Recurse -Force $extraction -ErrorAction SilentlyContinue
    # robocopy : 0 à 7 = succès (1 = fichiers copiés), 8 et plus = échec.
    if ($codeCopie -ge 8) { Stop-Installation "copie des fichiers impossible (robocopy code $codeCopie)" }
    Write-Ok "fichiers mis à jour depuis $Archive"
} elseif (Test-Path (Join-Path $Racine '.git')) {
    Push-Location $Racine
    try {
        Invoke-Natif 'git' @('pull', '--ff-only', 'origin', 'main') 'git pull impossible (modifications locales ?)'
    } finally {
        Pop-Location
    }
    Write-Ok 'dépôt git à jour'
} else {
    Stop-Installation "pas de dépôt git ici : téléchargez l'archive ZIP de GEC et relancez avec -Archive <chemin du zip>."
}

# ─── 3. Dépendances ───────────────────────────────────────────────────────────
Write-Etape '3/4' 'Dépendances Python'
Invoke-Natif $PythonVenv @('-m', 'pip', 'install', '--disable-pip-version-check', '-q', '-r', (Join-Path $Racine 'requirements.txt')) 'mise à jour des dépendances impossible' -Silencieux | Out-Null
Write-Ok 'dépendances à jour'

# ─── 4. Redémarrage ───────────────────────────────────────────────────────────
Write-Etape '4/4' 'Redémarrage'
if (Get-ScheduledTask -TaskName $script:NomTache -ErrorAction SilentlyContinue) {
    Start-ScheduledTask -TaskName $script:NomTache
    if (-not (Wait-GEC -Port $Port -DelaiSecondes 180)) {
        Show-JournalGEC -Racine $Racine
        Stop-Installation "GEC ne répond pas après la mise à jour."
    }
    Write-Ok "GEC redémarré et répond sur le port $Port"
} else {
    Write-Alerte "tâche « $script:NomTache » absente : relancez installer-gec.ps1 pour l'installer."
}
