param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
$output = Join-Path $project ("release\\" + $Version)
$stage = Join-Path $output "launcher"
$archiveName = "territoriya-sanka-launcher.zip"
$archive = Join-Path $output $archiveName
$application = Join-Path $project "build\\pyinstaller\\TerritorySanyokLauncher"

if (Test-Path -LiteralPath $output) {
    throw "Папка выпуска уже существует: $output"
}

New-Item -ItemType Directory -Path $stage | Out-Null
& (Join-Path $PSScriptRoot "build-app.ps1")
$items = @(
    ".gitignore",
    "README.md",
    "launcher.py",
    "updater.py",
    "run-launcher.cmd",
    "launcher.config.example.json",
    "package.json",
    "pnpm-lock.yaml",
    "public",
    "src",
    "scripts",
    "dist"
)

foreach ($item in $items) {
    Copy-Item -LiteralPath (Join-Path $project $item) -Destination $stage -Recurse -Force
}
# First-time installs need the public GitHub updater route, but the updater
# itself never overwrites this user-owned file after installation.
Copy-Item -LiteralPath (Join-Path $project "launcher.config.example.json") -Destination (Join-Path $stage "launcher.config.json") -Force
Copy-Item -Path (Join-Path $application "*") -Destination $stage -Recurse -Force

Compress-Archive -LiteralPath $stage -DestinationPath $archive
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant()
Set-Content -LiteralPath (Join-Path $output "SHA256SUMS.txt") -Value "$hash *$archiveName" -NoNewline
Write-Output $archive

