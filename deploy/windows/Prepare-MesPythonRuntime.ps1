[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ReleasePath,
    [Parameter(Mandatory = $true)][string]$BootstrapPythonPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'MesDeployment.Common.ps1')
. (Join-Path $PSScriptRoot 'MesPythonRuntime.Common.ps1')

$result = Initialize-MesPythonRuntime `
    -ReleasePath $ReleasePath `
    -BootstrapPythonPath $BootstrapPythonPath
$result | ConvertTo-Json -Depth 4
