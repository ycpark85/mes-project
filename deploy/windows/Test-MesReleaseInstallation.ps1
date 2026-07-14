[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PackagePath,
    [Parameter(Mandatory = $true)][string]$ManifestPath,
    [Parameter(Mandatory = $true)][string]$ChecksumPath,
    [Parameter(Mandatory = $true)][string]$RehearsalRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'MesRelease.Installation.Common.ps1')

$root = [IO.Path]::GetFullPath($RehearsalRoot)
if (Test-Path -LiteralPath $root) {
    throw "Rehearsal root must not already exist: $root"
}
New-Item -ItemType Directory -Path $root | Out-Null
$serverRoot = Join-Path $root 'server'
$releasesRoot = Join-Path $serverRoot 'releases'
New-Item -ItemType Directory -Path $releasesRoot -Force | Out-Null
$steps = New-Object System.Collections.Generic.List[object]

function Add-RehearsalStep([string]$Name, [string]$Status, [string]$Summary) {
    $script:steps.Add([ordered]@{
        name = $Name
        status = $Status
        summary = $Summary
    })
}

$previousCommit = '0000000000000000000000000000000000000000'
$previousRelease = Join-Path $releasesRoot $previousCommit
New-Item -ItemType Directory -Path $previousRelease | Out-Null
Set-Content -LiteralPath (Join-Path $previousRelease 'REHEARSAL-PREVIOUS.txt') -Value 'previous release' -Encoding ASCII
New-Item -ItemType Junction -Path (Join-Path $serverRoot 'current') -Target $previousRelease | Out-Null
if ((Get-MesReleaseJunctionTarget -CurrentPath (Join-Path $serverRoot 'current')) -ne [IO.Path]::GetFullPath($previousRelease)) {
    throw 'Unable to establish the rehearsal previous release.'
}
Add-RehearsalStep 'baseline_previous_release' 'OK' 'Previous release junction is active'

$install = Install-MesReleasePackage `
    -PackagePath $PackagePath `
    -ManifestPath $ManifestPath `
    -ChecksumPath $ChecksumPath `
    -ReleaseRoot $serverRoot
Add-RehearsalStep 'verified_package_install' 'OK' "Package installed as $($install.Commit)"

$current = Join-Path $serverRoot 'current'
$newTarget = [IO.Path]::GetFullPath($install.ReleasePath).TrimEnd('\')
$activated = Set-MesReleaseJunction -ReleaseRoot $serverRoot -TargetReleasePath $install.ReleasePath
if ($activated -ne $newTarget) {
    throw 'Rehearsal activation did not select the staged release.'
}
Add-RehearsalStep 'activate_new_release' 'OK' 'Current junction switched to the staged release'

$rolledBack = Set-MesReleaseJunction -ReleaseRoot $serverRoot -TargetReleasePath $previousRelease
if ($rolledBack -ne [IO.Path]::GetFullPath($previousRelease).TrimEnd('\')) {
    throw 'Rehearsal rollback did not restore the previous release.'
}
Add-RehearsalStep 'explicit_rollback' 'OK' 'Current junction returned to the previous release'

$failureObserved = $false
try {
    $null = Set-MesReleaseJunction `
        -ReleaseRoot $serverRoot `
        -TargetReleasePath $install.ReleasePath `
        -InjectFailureAfterCurrentMove
}
catch {
    if ($_.Exception.Message -notlike 'Injected release-switch failure*') {
        throw
    }
    $failureObserved = $true
}
if (-not $failureObserved) {
    throw 'The injected release-switch failure did not occur.'
}
$restoredTarget = Get-MesReleaseJunctionTarget -CurrentPath $current
if ($restoredTarget -ne [IO.Path]::GetFullPath($previousRelease).TrimEnd('\')) {
    throw 'Automatic pointer recovery did not restore the previous release.'
}
$residue = @(Get-ChildItem -LiteralPath $serverRoot -Force | Where-Object { $_.Name -like '.current-*' })
if ($residue.Count -gt 0) {
    throw 'Release-switch recovery left temporary junctions behind.'
}
Add-RehearsalStep 'injected_failure_recovery' 'OK' 'Failed switch automatically restored the previous release'

$report = [ordered]@{
    format_version = 1
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    status = 'OK'
    rehearsal_root = $root
    package_sha256 = $install.PackageSha256
    package_commit = $install.Commit
    alembic_head = $install.AlembicHead
    final_active_commit = $previousCommit
    database_changed = $false
    windows_services_changed = $false
    production_configuration_changed = $false
    steps = $steps
}
$reportPath = Join-Path $root 'release-installation-rehearsal.json'
$temporaryReport = "$reportPath.tmp"
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $temporaryReport -Encoding UTF8
Move-Item -LiteralPath $temporaryReport -Destination $reportPath

Write-Host 'MES release installation rehearsal: OK'
foreach ($step in $steps) {
    Write-Host ("[{0}] {1}: {2}" -f $step.status, $step.name, $step.summary)
}
Write-Host "rehearsal_report=$reportPath"
