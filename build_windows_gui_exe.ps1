param(
    [string]$Name = "AI-Session-Viewer"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$venvPath = Join-Path $repoRoot ".venv-win-build"
if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
}

$python = Join-Path $venvPath "Scripts\python.exe"
& $python -m pip install --upgrade pip pyinstaller
& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --name $Name `
    --windowed `
    --onefile `
    session_viewer_gui.py

Write-Host ""
Write-Host "Build complete."
Write-Host "Output:"
Write-Host "  $repoRoot\dist\$Name.exe"
