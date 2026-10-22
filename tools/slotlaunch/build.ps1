# Build the ARM64 helper against the SDL libraries installed on the development device.
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\dev\dev.ps1"
$libraryFolder = Join-Path $script:ProjectRoot 'build\native\lib'
New-Item -ItemType Directory -Force $libraryFolder | Out-Null
foreach ($library in @('SDL2', 'SDL2_image')) {
    scp -o BatchMode=yes -q "$($script:Device):/usr/lib/lib$library.so" (Join-Path $libraryFolder "lib$library.so")
    if ($LASTEXITCODE -ne 0) { throw "Could not fetch $library from the device" }
}
$linuxRoot = (& wsl --exec wslpath -a $script:ProjectRoot).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not resolve the WSL project path' }
& wsl --exec sh "$linuxRoot/tools/slotlaunch/build.sh"
if ($LASTEXITCODE -ne 0) { throw 'Native helper build failed' }
Write-Output (Join-Path $script:ProjectRoot 'theme\art-book-slot\_slot\launch\slot-launch')
