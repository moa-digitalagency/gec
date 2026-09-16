# Fonctions partagées par installer-gec.ps1 et mettre-a-jour-gec.ps1.
# Compatible PowerShell 5.1 (Windows Server 2016).

$script:NomTache = 'GEC'

function Write-Etape([string]$Numero, [string]$Texte) {
    Write-Host ''
    Write-Host "[$Numero] $Texte" -ForegroundColor Cyan
}

function Write-Ok([string]$Texte) { Write-Host "    OK  $Texte" -ForegroundColor Green }
function Write-Info([string]$Texte) { Write-Host "        $Texte" }
function Write-Alerte([string]$Texte) { Write-Host "    /!\ $Texte" -ForegroundColor Yellow }

function Stop-Installation([string]$Texte) {
    Write-Host ''
    Write-Host "ÉCHEC : $Texte" -ForegroundColor Red
    throw $Texte
}

function Invoke-Natif {
    <#
    Lance un programme externe et échoue proprement s'il renvoie un code d'erreur.
    Sous PowerShell 5.1 avec $ErrorActionPreference = 'Stop', la moindre ligne écrite
    sur stderr (un simple avertissement de pip) interromprait le script : on repasse
    en 'Continue' le temps de l'appel et on juge sur le code de sortie.
    #>
    param([string]$Programme, [string[]]$Arguments, [string]$Echec, [switch]$Silencieux)
    $precedent = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    # Sortie redirigée, Python écrit en cp1252 ; la console de Windows Server la
    # décode en OEM (cp850) : les accents arrivent brouillés. On impose l'UTF-8
    # des deux côtés le temps de l'appel.
    $encodagePython = $env:PYTHONIOENCODING
    $env:PYTHONIOENCODING = 'utf-8'
    $encodageConsole = $null
    try { $encodageConsole = [Console]::OutputEncoding; [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }
    try {
        $sortie = & $Programme @Arguments 2>&1 | ForEach-Object { "$_" }
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $precedent
        $env:PYTHONIOENCODING = $encodagePython
        if ($encodageConsole) { try { [Console]::OutputEncoding = $encodageConsole } catch { } }
    }
    if (-not $Silencieux -or $code -ne 0) {
        $sortie | ForEach-Object { Write-Info $_ }
    }
    if ($code -ne 0) { Stop-Installation "$Echec (code $code)" }
    # La sortie n'est renvoyée qu'en mode silencieux : sinon elle serait affichée deux fois.
    if ($Silencieux) { return $sortie }
}

function Test-Administrateur {
    $identite = [Security.Principal.WindowsIdentity]::GetCurrent()
    return (New-Object Security.Principal.WindowsPrincipal $identite).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Read-ValeurEnv([string]$CheminEnv, [string]$Cle, [string]$Defaut = '') {
    if (-not (Test-Path $CheminEnv)) { return $Defaut }
    foreach ($ligne in [IO.File]::ReadAllLines($CheminEnv, [Text.Encoding]::UTF8)) {
        $l = $ligne.Trim().TrimStart([char]0xFEFF)
        if ($l -and -not $l.StartsWith('#') -and $l.Contains('=')) {
            $parts = $l.Split('=', 2)
            if ($parts[0].Trim() -eq $Cle) { return $parts[1].Trim() }
        }
    }
    return $Defaut
}

function Wait-GEC([int]$Port, [int]$DelaiSecondes = 120) {
    <# Attend que GEC réponde 200 sur /login. Renvoie $true ou $false. #>
    $limite = (Get-Date).AddSeconds($DelaiSecondes)
    while ((Get-Date) -lt $limite) {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/login" -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -eq 200) { return $true }
        } catch { }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Wait-PortLibre([int]$Port, [int]$DelaiSecondes = 30) {
    $limite = (Get-Date).AddSeconds($DelaiSecondes)
    while ((Get-Date) -lt $limite) {
        if (-not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Stop-TacheGEC([int]$Port) {
    $tache = Get-ScheduledTask -TaskName $script:NomTache -ErrorAction SilentlyContinue
    if ($tache) {
        Stop-ScheduledTask -TaskName $script:NomTache -ErrorAction SilentlyContinue
        if (-not (Wait-PortLibre -Port $Port)) {
            Write-Alerte "le port $Port est toujours occupé 30 s après l'arrêt de la tâche GEC."
        }
    }
}

function Show-JournalGEC([string]$Racine, [int]$Lignes = 40) {
    $journal = Join-Path $Racine 'logs\gec.log'
    if (Test-Path $journal) {
        Write-Info "--- dernières lignes de $journal ---"
        Get-Content $journal -Tail $Lignes -Encoding UTF8 | ForEach-Object { Write-Info $_ }
    }
}
