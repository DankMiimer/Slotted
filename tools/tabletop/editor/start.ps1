param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$editorBuild = Join-Path $projectRoot 'build\tabletop'
$editorUrl = 'http://127.0.0.1:8765'
New-Item -ItemType Directory -Force -Path $editorBuild | Out-Null
$missingAssets = @('table/scene.txt', 'table/scene.json', 'tv-stand/scene.txt', 'wooden-table/scene.txt', 'panasonic/scene.txt', 'panasonic/scene.json', 'pvm/scene.txt', 'oldtv/scene.txt') | Where-Object { -not (Test-Path -LiteralPath (Join-Path "$editorBuild/assets" $_)) }
if ($missingAssets) {
    $linuxProject = (& wsl.exe -- wslpath -a $projectRoot).Trim()
    & wsl.exe -- bash -lc 'cd "$1" && /home/mads1/slot-tooling/blender-4.5.0-linux-x64/blender -b --factory-startup --disable-autoexec --python-exit-code 1 -t 1 --python tools/tabletop/prepare_assets.py -- "$PWD/build/tabletop/assets"' slot-editor $linuxProject
    if ($LASTEXITCODE -ne 0) { throw 'Could not rebuild scene assets from the preserved original models. See docs/TABLETOP_HANDOFF.md.' }
}
foreach ($console in @('snes', 'snes-us', 'n64', 'nes')) {
    if (-not (Test-Path -LiteralPath (Join-Path $editorBuild "assets/$console/power.control"))) {
        & python (Join-Path $PSScriptRoot '../prepare_controls.py') --model $console
        if ($LASTEXITCODE -ne 0) { throw "Could not register the preserved $console console controls." }
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $editorBuild 'editor-default.scene'))) {
    $linuxProject = (& wsl.exe -- wslpath -a $projectRoot).Trim()
    & wsl.exe -- bash -lc 'cd "$1" && sh tools/tabletop/build_probe.sh && SLOT_SCENE_IGNORE_LAYOUT=1 SLOT_SCENE_EXPORT=build/tabletop/editor-default.scene sh tools/frontend/tests/run_probe.sh build/tabletop/probe theme/art-book-slot/_slot build/tabletop/assets build/tabletop/editor-default.bmp snes panasonic' slot-editor $linuxProject
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare the scene editor. See docs/TABLETOP_HANDOFF.md.' }
}
if (-not (Test-Path -LiteralPath (Join-Path $editorBuild 'assets/surfaces/library.json'))) {
    & python (Join-Path $PSScriptRoot '../make_surfaces.py')
    if ($LASTEXITCODE -ne 0) { throw 'Could not generate the built-in room surface textures.' }
}
$editorReady = $false
try { $session = Invoke-RestMethod "$editorUrl/api/manifest" -TimeoutSec 2; $editorReady = $session.project -eq $projectRoot } catch {}
if ($editorReady -and $session.editorRevision -ne 12) {
    $serverPidFile = Join-Path $editorBuild 'editor-server.pid'
    if (Test-Path -LiteralPath $serverPidFile) {
        $staleEditorPid = [int](Get-Content -LiteralPath $serverPidFile)
        $staleEditorProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $staleEditorPid"
        $expectedEditorScript = Join-Path $PSScriptRoot 'server.py'
        if ($staleEditorProcess.CommandLine -like "*$expectedEditorScript*") { Stop-Process -Id $staleEditorPid }
    }
    $editorReady = $false
}
if (-not $editorReady) {
    $pythonBinary = (Get-Command python).Source
    $serverScript = Join-Path $PSScriptRoot 'server.py'
    $serverProcess = Start-Process -FilePath $pythonBinary -ArgumentList @('-u', ('"' + $serverScript + '"')) -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $editorBuild 'editor-server.log') -RedirectStandardError (Join-Path $editorBuild 'editor-server-error.log')
    Set-Content -LiteralPath (Join-Path $editorBuild 'editor-server.pid') -Value $serverProcess.Id
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Milliseconds 500
        try { $session = Invoke-RestMethod "$editorUrl/api/manifest" -TimeoutSec 1; $editorReady = $session.project -eq $projectRoot; if ($editorReady) { break } } catch {}
    }
}
if (-not $editorReady) { throw 'Scene editor did not start; check build/tabletop/editor-server-error.log.' }
if (-not $NoBrowser) { Start-Process $editorUrl }
Write-Output "Scene editor ready: $editorUrl"
