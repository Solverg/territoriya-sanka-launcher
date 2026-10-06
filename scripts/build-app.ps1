$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
$pyInstaller = Join-Path $project ".tools\\pyinstaller"
$pyWebView = Join-Path $project ".tools\\pywebview"
$dist = Join-Path $project "dist"
$output = Join-Path $project "build\\pyinstaller"

if (-not (Test-Path -LiteralPath (Join-Path $dist "client\\index.html"))) {
    throw "Сначала выполните сборку интерфейса."
}
if (-not (Test-Path -LiteralPath (Join-Path $pyInstaller "PyInstaller\\__main__.py"))) {
    throw "Не найден PyInstaller в .tools\\pyinstaller."
}
if (-not (Test-Path -LiteralPath (Join-Path $pyWebView "webview\\__init__.py"))) {
    throw "Не найден pywebview в .tools\\pywebview. Установите его командой: python -m pip install --target .tools\\pywebview pywebview"
}

$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = "$pyInstaller$([IO.Path]::PathSeparator)$pyWebView"
try {
    python -m PyInstaller --noconfirm --clean --onedir --noconsole `
        --name "TerritorySanyokLauncher" `
        --distpath $output `
        --workpath (Join-Path $project "build\\pyinstaller-work") `
        --specpath (Join-Path $project "build\\pyinstaller-spec") `
        --add-data "$dist;dist" `
        --add-data "$(Join-Path $project 'public');public" `
        --icon "$(Join-Path $project 'public\\assets\\launcher-icon.ico')" `
        --collect-all webview `
        (Join-Path $project "launcher.py")
} finally {
    $env:PYTHONPATH = $previousPythonPath
}

Write-Output (Join-Path $output "TerritorySanyokLauncher\\TerritorySanyokLauncher.exe")
