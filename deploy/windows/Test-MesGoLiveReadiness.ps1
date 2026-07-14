[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PackagePath,
    [Parameter(Mandatory = $true)][string]$ManifestPath,
    [Parameter(Mandatory = $true)][string]$ChecksumPath,
    [Parameter(Mandatory = $true)][string]$ExpectedCommit,
    [Parameter(Mandatory = $true)][string]$ReleaseValidationReport,
    [Parameter(Mandatory = $true)][string]$InstallationRehearsalReport,
    [Parameter(Mandatory = $true)][string]$RuntimeRehearsalReport,
    [Parameter(Mandatory = $true)][string]$ActivationRehearsalReport,
    [Parameter(Mandatory = $true)][string]$OutputReport
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'MesRelease.Installation.Common.ps1')

if ($ExpectedCommit -notmatch '^[0-9a-f]{40}$') { throw 'Expected commit is invalid.' }
$metadata = Get-MesReleasePackageMetadata -PackagePath $PackagePath -ManifestPath $ManifestPath -ChecksumPath $ChecksumPath
if ($metadata.Commit -ne $ExpectedCommit) { throw 'Package commit differs from the expected commit.' }

function Read-Evidence([string]$Path, [string]$Label) {
    try { return Get-Content -Raw -LiteralPath $Path -Encoding UTF8 | ConvertFrom-Json }
    catch { throw "$Label evidence is missing or invalid JSON." }
}
function Assert-Value($Actual, $Expected, [string]$Message) {
    if ($Actual -ne $Expected) { throw $Message }
}

$release = Read-Evidence $ReleaseValidationReport 'Release validation'
$installation = Read-Evidence $InstallationRehearsalReport 'Installation rehearsal'
$runtime = Read-Evidence $RuntimeRehearsalReport 'Runtime rehearsal'
$activation = Read-Evidence $ActivationRehearsalReport 'Activation rehearsal'
Assert-Value $release.overall_status 'OK' 'Release validation is not successful.'
Assert-Value $release.commit $ExpectedCommit 'Release validation commit differs.'
foreach ($evidence in @($installation, $runtime, $activation)) {
    Assert-Value $evidence.status 'OK' 'A rehearsal report is not successful.'
    Assert-Value $evidence.package_commit $ExpectedCommit 'A rehearsal commit differs.'
    Assert-Value $evidence.package_sha256 $metadata.PackageSha256 'A rehearsal package hash differs.'
}
Assert-Value $installation.database_changed $false 'Installation rehearsal changed a database.'
Assert-Value $installation.windows_services_changed $false 'Installation rehearsal changed Windows services.'
Assert-Value $runtime.production_database_used $false 'Runtime rehearsal used a production database.'
Assert-Value $runtime.database_migrated $false 'Runtime rehearsal applied a migration.'
Assert-Value $runtime.windows_services_changed $false 'Runtime rehearsal changed Windows services.'
Assert-Value $activation.successful_activation_observed $true 'Successful activation was not proven.'
Assert-Value $activation.failed_activation_rollback_observed $true 'Failed activation rollback was not proven.'
Assert-Value $activation.production_database_used $false 'Activation rehearsal used a production database.'
Assert-Value $activation.database_migrated $false 'Activation rehearsal applied a migration.'
Assert-Value $activation.windows_services_changed $false 'Activation rehearsal changed Windows services.'

$output = [IO.Path]::GetFullPath($OutputReport)
if (Test-Path -LiteralPath $output) { throw "Go-live readiness report already exists: $output" }
$parent = [IO.Path]::GetDirectoryName($output)
New-Item -ItemType Directory -Path $parent -Force | Out-Null
$report = [ordered]@{
    format_version = 1
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    status = 'READY'
    commit = $ExpectedCommit
    package_sha256 = $metadata.PackageSha256
    alembic_head = $metadata.AlembicHead
    evidence = [ordered]@{
        release_validation = (Resolve-Path $ReleaseValidationReport).Path
        installation_rehearsal = (Resolve-Path $InstallationRehearsalReport).Path
        runtime_rehearsal = (Resolve-Path $RuntimeRehearsalReport).Path
        activation_rehearsal = (Resolve-Path $ActivationRehearsalReport).Path
    }
    production_deployment_performed = $false
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$output.tmp" -Encoding UTF8
Move-Item -LiteralPath "$output.tmp" -Destination $output
Write-Host 'MES go-live readiness evidence: READY'
Write-Host "go_live_readiness_report=$output"
