# =====================================================
# GEC Mines - Script d'Installation Automatique Windows
# =====================================================
# Copyright (c) 2025 MOA Digital Agency LLC
# Développé par : AIsance KALONJI wa KALONJI
# Email : moa@myoneart.com | moa.myoneart@gmail.com
# =====================================================

param(
    [string]$InstallPath = "$env:USERPROFILE\gec-mines",
    [switch]$SkipDependencies = $false
)

Write-Host "🚀 Installation de GEC Mines pour Windows" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Vérifier les privilèges administrateur
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "⚠️  ATTENTION: Exécution en tant qu'utilisateur standard" -ForegroundColor Yellow
    Write-Host "   Pour une installation complète, exécutez en tant qu'administrateur" -ForegroundColor Yellow
    Write-Host ""
}

# Fonction pour vérifier si une commande existe
function Test-Command {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

# Étape 1: Installer les dépendances système
if (-not $SkipDependencies) {
    Write-Host "📦 Installation des dépendances système..." -ForegroundColor Blue
    
    # Vérifier si winget est disponible
    if (Test-Command "winget") {
        Write-Host "   ✅ winget détecté"
        
        # Installer Python 3.11
        if (-not (Test-Command "python")) {
            Write-Host "   📥 Installation de Python 3.11..."
            try {
                winget install --id Python.Python.3.11 -e --silent --accept-package-agreements --accept-source-agreements
                Write-Host "   ✅ Python 3.11 installé"
            }
            catch {
                Write-Host "   ❌ Erreur lors de l'installation de Python" -ForegroundColor Red
                Write-Host "   🔗 Veuillez télécharger Python manuellement: https://python.org/downloads/"
                exit 1
            }
        } else {
            Write-Host "   ✅ Python déjà installé"
        }
        
        # Installer Git
        if (-not (Test-Command "git")) {
            Write-Host "   📥 Installation de Git..."
            try {
                winget install --id Git.Git -e --silent --accept-package-agreements --accept-source-agreements
                Write-Host "   ✅ Git installé"
            }
            catch {
                Write-Host "   ❌ Erreur lors de l'installation de Git" -ForegroundColor Red
                Write-Host "   🔗 Veuillez télécharger Git manuellement: https://git-scm.com/downloads"
                exit 1
            }
        } else {
            Write-Host "   ✅ Git déjà installé"
        }
    } else {
        Write-Host "   ❌ winget non disponible. Installation manuelle requise:" -ForegroundColor Red
        Write-Host "   🔗 Python: https://python.org/downloads/" -ForegroundColor Yellow
        Write-Host "   🔗 Git: https://git-scm.com/downloads" -ForegroundColor Yellow
        exit 1
    }
}

# Rafraîchir les variables d'environnement
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Étape 2: Cloner le projet
Write-Host ""
Write-Host "📂 Clonage du projet GEC Mines..." -ForegroundColor Blue

if (Test-Path $InstallPath) {
    Write-Host "   ⚠️  Le dossier $InstallPath existe déjà" -ForegroundColor Yellow
    $response = Read-Host "   Voulez-vous le supprimer et recommencer? (o/N)"
    if ($response -eq "o" -or $response -eq "O") {
        Remove-Item $InstallPath -Recurse -Force
        Write-Host "   🗑️  Dossier supprimé"
    } else {
        Write-Host "   ❌ Installation annulée" -ForegroundColor Red
        exit 1
    }
}

try {
    git clone https://github.com/moa-digitalagency/gec.git $InstallPath
    Set-Location $InstallPath
    Write-Host "   ✅ Projet cloné dans $InstallPath"
}
catch {
    Write-Host "   ❌ Erreur lors du clonage du projet" -ForegroundColor Red
    Write-Host "   Vérifiez votre connexion internet et l'accès à GitHub"
    exit 1
}

# Étape 3: Configurer l'environnement Python
Write-Host ""
Write-Host "🐍 Configuration de l'environnement Python..." -ForegroundColor Blue

# Configurer la politique d'exécution
try {
    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
    Write-Host "   ✅ Politique d'exécution configurée"
}
catch {
    Write-Host "   ⚠️  Impossible de modifier la politique d'exécution" -ForegroundColor Yellow
}

# Créer l'environnement virtuel
try {
    python -m venv .venv
    Write-Host "   ✅ Environnement virtuel créé"
}
catch {
    try {
        py -3.11 -m venv .venv
        Write-Host "   ✅ Environnement virtuel créé (py -3.11)"
    }
    catch {
        Write-Host "   ❌ Erreur lors de la création de l'environnement virtuel" -ForegroundColor Red
        exit 1
    }
}

# Activer l'environnement virtuel
try {
    & ".\.venv\Scripts\Activate.ps1"
    Write-Host "   ✅ Environnement virtuel activé"
}
catch {
    Write-Host "   ❌ Erreur lors de l'activation de l'environnement virtuel" -ForegroundColor Red
    exit 1
}

# Étape 4: Installer les dépendances Python
Write-Host ""
Write-Host "📦 Installation des dépendances Python..." -ForegroundColor Blue

try {
    python -m pip install -U pip wheel
    Write-Host "   ✅ pip et wheel mis à jour"
    
    python -m pip install -r project-dependencies.txt
    Write-Host "   ✅ Dépendances installées"
}
catch {
    Write-Host "   ❌ Erreur lors de l'installation des dépendances" -ForegroundColor Red
    exit 1
}

# Étape 5: Configuration initiale
Write-Host ""
Write-Host "⚙️  Configuration initiale..." -ForegroundColor Blue

$envFile = ".env"
if (-not (Test-Path $envFile)) {
    $envContent = @"
# Configuration GEC Mines
DATABASE_URL=sqlite:///instance/gecmines.db
SESSION_SECRET=$(([char[]]([char]33..[char]126) | Get-Random -Count 32) -join '')
GEC_MASTER_KEY=$(([char[]]([char]65..[char]90) + [char[]]([char]97..[char]122) + [char[]]([char]48..[char]57) | Get-Random -Count 32) -join '')
GEC_PASSWORD_SALT=$(([char[]]([char]65..[char]90) + [char[]]([char]97..[char]122) + [char[]]([char]48..[char]57) | Get-Random -Count 16) -join '')

# Configuration SMTP (optionnel)
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_EMAIL=votre-email@gmail.com
# SMTP_PASSWORD=votre-mot-de-passe-app
# SMTP_USE_TLS=True
"@
    
    $envContent | Out-File -FilePath $envFile -Encoding UTF8
    Write-Host "   ✅ Fichier .env créé avec configuration par défaut"
} else {
    Write-Host "   ✅ Fichier .env existe déjà"
}

# Créer les dossiers nécessaires
$folders = @("instance", "uploads", "backups", "exports")
foreach ($folder in $folders) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder | Out-Null
        Write-Host "   ✅ Dossier '$folder' créé"
    }
}

# Étape 6: Test de l'installation
Write-Host ""
Write-Host "🧪 Test de l'installation..." -ForegroundColor Blue

try {
    # Test rapide d'importation
    python -c "import flask, sqlalchemy, cryptography; print('✅ Modules principaux importés')"
    Write-Host "   ✅ Test d'importation réussi"
}
catch {
    Write-Host "   ❌ Erreur lors du test d'importation" -ForegroundColor Red
}

# Créer des scripts de démarrage
$startScript = @"
@echo off
cd /d "$InstallPath"
call .venv\Scripts\activate.bat
python main.py
pause
"@

$startScript | Out-File -FilePath "start-gec.bat" -Encoding ASCII
Write-Host "   ✅ Script de démarrage 'start-gec.bat' créé"

# Étape 7: Instructions finales
Write-Host ""
Write-Host "🎉 Installation terminée avec succès!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "📍 Dossier d'installation: $InstallPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 Pour démarrer GEC Mines:" -ForegroundColor Yellow
Write-Host "   1. Double-cliquez sur 'start-gec.bat'"
Write-Host "   2. Ou exécutez manuellement:"
Write-Host "      cd `"$InstallPath`""
Write-Host "      .venv\Scripts\activate"
Write-Host "      python main.py"
Write-Host ""
Write-Host "🌐 L'application sera accessible sur: http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "📧 Support: moa@myoneart.com | moa.myoneart@gmail.com" -ForegroundColor Magenta
Write-Host "🌐 Site web: https://myoneart.com" -ForegroundColor Magenta
Write-Host ""
Write-Host "© 2025 MOA Digital Agency LLC" -ForegroundColor Gray

# Proposer de démarrer l'application
Write-Host ""
$startNow = Read-Host "Voulez-vous démarrer l'application maintenant? (o/N)"
if ($startNow -eq "o" -or $startNow -eq "O") {
    Write-Host ""
    Write-Host "🚀 Démarrage de GEC Mines..." -ForegroundColor Green
    python main.py
}