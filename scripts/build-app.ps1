$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
$pyInstaller = Join-Path $project ".tools\\pyinstaller"
$dist = Join-Path $project "dist"
$output = Join-Path $project "build\\pyinstaller"

if (-not (Test-Path -LiteralPath (Join-Path $dist "client\\index.html"))) {
    throw "Сначала выполните сборку интерфейса."
}
if (-not (Test-Path -LiteralPath (Join-Path $pyInstaller "PyInstaller\\__main__.py"))) {
    throw "Не найден PyInstaller в .tools\\pyinstaller."
}

$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = $pyInstaller
try {
    python -m PyInstaller --noconfirm --clean --onedir --noconsole `
        --name "TerritorySanyokLauncher" `
        --distpath $output `
        --workpath (Join-Path $project "build\\pyinstaller-work") `
        --specpath (Join-Path $project "build\\pyinstaller-spec") `
        --add-data "$dist;dist" `
        --add-data "$(Join-Path $project 'public');public" `
        (Join-Path $project "launcher.py")
} finally {
    $env:PYTHONPATH = $previousPythonPath
}

Write-Output (Join-Path $output "TerritorySanyokLauncher\\TerritorySanyokLauncher.exe")

