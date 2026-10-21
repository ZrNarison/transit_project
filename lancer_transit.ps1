```powershell
$ErrorActionPreference = "Stop"

# ============================================================
# CONFIGURATION
# ============================================================
$Projet = "D:\transit_project"
$PythonVenv = Join-Path $Projet ".venv\Scripts\python.exe"
$ManagePy = Join-Path $Projet "manage.py"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DEMARRAGE DE TRANSIT_PROJECT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier le dossier du projet
if (-not (Test-Path $ManagePy)) {
    Write-Host "ERREUR : manage.py introuvable dans $Projet" -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

# Vérifier l'environnement virtuel
if (-not (Test-Path $PythonVenv)) {
    Write-Host "ERREUR : Python du venv introuvable :" -ForegroundColor Red
    Write-Host $PythonVenv
    Write-Host "Verifiez le dossier .venv du projet." -ForegroundColor Yellow
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

Write-Host "Projet : $Projet" -ForegroundColor Green
Write-Host "Python : $PythonVenv" -ForegroundColor Green
Write-Host ""

Set-Location $Projet

Write-Host "Verification de Django..." -ForegroundColor Yellow
& $PythonVenv manage.py check

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERREUR : la verification Django a echoue." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

Write-Host ""
Write-Host "Lancement du serveur sur le port 8000..." -ForegroundColor Green
Write-Host "Acces local : http://127.0.0.1:8000/" -ForegroundColor Cyan
Write-Host "Pour les autres PC : http://ADRESSE-IP-DU-PC:8000/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Gardez cette fenetre ouverte pendant l'utilisation." -ForegroundColor Yellow
Write-Host ""

& $PythonVenv manage.py runserver 0.0.0.0:8000

Read-Host "Le serveur est arrete. Appuyez sur Entree pour fermer"
```