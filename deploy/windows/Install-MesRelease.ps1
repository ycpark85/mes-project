[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PackagePath,
    [Parameter(Mandatory = $true)][string]$ManifestPath,
    [Parameter(Mandatory = $true)][string]$ChecksumPath,
    [Parameter(Mandatory = $true)][string]$ReleaseRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'MesRelease.Installation.Common.ps1')

$result = Install-MesReleasePackage `
    -PackagePath $PackagePath `
    -ManifestPath $ManifestPath `
    -ChecksumPath $ChecksumPath `
    -ReleaseRoot $ReleaseRoot

$result | ConvertTo-Json -Depth 4
