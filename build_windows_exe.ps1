param(
    [string]$Name = "aisv",
    [ValidateSet("onefile", "onedir")]
    [string]$Mode = "onefile",
    [string]$Icon
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

$pyInstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--name", $Name,
    "--console"
)

if ($Mode -eq "onefile") {
    $pyInstallerArgs += "--onefile"
} else {
    $pyInstallerArgs += "--onedir"
}

if ($Icon) {
    $pyInstallerArgs += @("--icon", $Icon)
}

$pyInstallerArgs += "session_viewer.py"

Write-Host "Running: $python $($pyInstallerArgs -join ' ')"
& $python @pyInstallerArgs

Write-Host ""
Write-Host "Build complete."
Write-Host "Output:"
if ($Mode -eq "onefile") {
    Write-Host "  $repoRoot\dist\$Name.exe"
} else {
    Write-Host "  $repoRoot\dist\$Name\$Name.exe"
}
