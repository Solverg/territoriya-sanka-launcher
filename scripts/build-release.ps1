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

if (Test-Path -LiteralPath $output) {
    throw "Папка выпуска уже существует: $output"
}

New-Item -ItemType Directory -Path $stage | Out-Null
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

Compress-Archive -LiteralPath $stage -DestinationPath $archive
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant()
Set-Content -LiteralPath (Join-Path $output "SHA256SUMS.txt") -Value "$hash *$archiveName" -NoNewline
Write-Output $archive

