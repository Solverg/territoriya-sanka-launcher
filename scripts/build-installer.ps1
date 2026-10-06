param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
$release = Join-Path $project ("release\\" + $Version)
$isccCandidates = @(
    "$env:LOCALAPPDATA\\Programs\\Inno Setup 6\\ISCC.exe",
    "${env:ProgramFiles(x86)}\\Inno Setup 6\\ISCC.exe",
    "$env:ProgramFiles\\Inno Setup 6\\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not $iscc) {
    throw "Не найден компилятор Inno Setup 6 (ISCC.exe)."
}
if (-not (Test-Path -LiteralPath (Join-Path $release "launcher\\TerritorySanyokLauncher.exe"))) {
    throw "Сначала соберите ZIP-релиз: scripts\\build-release.ps1 -Version $Version"
}

& $iscc "/DAppVersion=$Version" (Join-Path $project "installer\\TerritorySanyokLauncher.iss")
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup завершился с кодом $LASTEXITCODE."
}
Write-Output (Join-Path $release ("TerritorySanyokLauncher-Setup-" + $Version + ".exe"))
