# PC-side helpers for working on the theme against the handheld over ssh.
# Usage: . .\tools\dev\dev.ps1   then   Install-DevHelper; Push-Theme theme\art-book-slot; Esdev status; Get-Shot name
# The ssh target comes from $env:SLOT_DEVICE or tools\dev\device.txt (one line, e.g. root@<ip>; not committed).

$script:ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$script:Device = $env:SLOT_DEVICE
if (-not $script:Device -and (Test-Path "$PSScriptRoot\device.txt")) {
    $script:Device = (Get-Content "$PSScriptRoot\device.txt" -TotalCount 1).Trim()
}
if (-not $script:Device) {
    throw 'Set $env:SLOT_DEVICE or write the ssh target (root@<ip>) to tools\dev\device.txt'
}
$script:RemoteHelper = '/userdata/system/slot-dev/esdev.py'

function Invoke-Device([string]$Command) {
    ssh -o BatchMode=yes $script:Device $Command
}

function Install-DevHelper {
    Invoke-Device 'mkdir -p /userdata/system/slot-dev'
    scp -o BatchMode=yes -q "$PSScriptRoot\esdev.py" "$($script:Device):$($script:RemoteHelper)"
}

function Esdev {
    Invoke-Device ("python3 $($script:RemoteHelper) " + ($args -join ' '))
}

# Replaces /userdata/themes/<folder name> with the local theme folder.
function Push-Theme([string]$Source) {
    $path = Resolve-Path (Join-Path $script:ProjectRoot $Source)
    $name = Split-Path -Leaf $path
    Invoke-Device "rm -rf '/userdata/themes/$name'"
    scp -o BatchMode=yes -q -r "$path" "$($script:Device):/userdata/themes/"
}

# Restarts ES with Art Book Slot active, straight into one system's list, and screenshots it.
# Preserve this session's settings, including an already-enabled launch animation.
function Show-Shelf([string]$System, [string]$Name) {
    Esdev stop
    Esdev backup session | Out-Null
    Esdev set ThemeSet art-book-slot
    Esdev set StartupSystem $System
    Esdev set StartupOnGameList true
    Esdev start
    Esdev wait 90 | Out-Null
    Start-Sleep -Seconds 4
    Get-Shot $Name -Folder build\shots
}

function Restore-Device {
    Esdev stop
    Esdev restore session
    Esdev start
    Esdev wait 90 | Out-Null
}

function Get-Shot([string]$Name, [string]$Folder = 'spikes\shots') {
    $dir = Join-Path $script:ProjectRoot $Folder
    New-Item -ItemType Directory -Force $dir | Out-Null
    Esdev shot /tmp/slot-shot.png
    scp -o BatchMode=yes -q "$($script:Device):/tmp/slot-shot.png" (Join-Path $dir "$Name.png")
    Join-Path $dir "$Name.png"
}
