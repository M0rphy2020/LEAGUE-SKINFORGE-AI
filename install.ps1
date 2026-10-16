$ErrorActionPreference = 'Stop'

Write-Host '=== SkinForge AI setup ===' -ForegroundColor Cyan

$pythonCommand = $null
$pythonPrefix = @()
$launcher = Get-Command py -ErrorAction SilentlyContinue
if ($launcher) {
    & $launcher.Source -3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>$null
    if ($LASTEXITCODE -eq 0) {
        $pythonCommand = $launcher.Source
        $pythonPrefix = @('-3')
    }
}

if (-not $pythonCommand) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        throw 'Python 3.11+ was not found. Install Python 3.11 or newer, enable Add Python to PATH, then rerun this installer.'
    }
    & $python.Source -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'
    if ($LASTEXITCODE -ne 0) {
        throw 'Python 3.11+ is required.'
    }
    $pythonCommand = $python.Source
}

Write-Host '[1/3] Installing SkinForge AI...' -ForegroundColor Cyan
& $pythonCommand @pythonPrefix -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'Could not update pip.' }
& $pythonCommand @pythonPrefix -m pip install -e ".[texture]"
if ($LASTEXITCODE -ne 0) { throw 'SkinForge installation failed.' }

Write-Host '[2/3] Installing optional WAD tools for the current Windows user...' -ForegroundColor Cyan
& $pythonCommand @pythonPrefix -m skinforge.cli setup
if ($LASTEXITCODE -ne 0) {
    Write-Warning 'wadtools could not be installed automatically. The visual app will still work for package inspection, safe extraction and AI planning; WAD extraction needs a successful wadtools setup.'
}

Write-Host '[3/3] Checking installation...' -ForegroundColor Cyan
& $pythonCommand @pythonPrefix -m skinforge.cli doctor
if ($LASTEXITCODE -ne 0) { throw 'Health check failed.' }

Write-Host ''
Write-Host 'Setup complete. Example:' -ForegroundColor Green
Write-Host '  skinforge inspect "C:\path\to\skin.fantome"'
Write-Host '  skinforge validate "C:\path\to\skin.fantome"'
Write-Host '  skinforge wad-extract "C:\path\to\Champion.wad.client" --output .\extracted'
Write-Host ''
Write-Host 'AI planning needs an API endpoint/model in a local .env file. See .env.example.'
Write-Host ''
$startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
New-Item -ItemType Directory -Path $startMenu -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $startMenu 'SkinForge AI.lnk'))
$shortcut.TargetPath = $pythonCommand
$shortcut.Arguments = (@($pythonPrefix) + @('-m', 'skinforge.desktop') | Where-Object { $_ }) -join ' '
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = 'Open the SkinForge AI custom-skin workshop'
$shortcut.Save()

Write-Host 'Created a SkinForge AI shortcut in the Start Menu.' -ForegroundColor Green
Write-Host 'Launching the visual SkinForge workspace...' -ForegroundColor Cyan
& $pythonCommand @pythonPrefix -m skinforge.desktop
