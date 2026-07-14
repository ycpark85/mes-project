[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$ConfigFile,
    [Parameter(Mandatory = $true)][string]$PackagePath,
    [Parameter(Mandatory = $true)][string]$ManifestPath,
    [Parameter(Mandatory = $true)][string]$ChecksumPath,
    [Parameter(Mandatory = $true)][string]$ReleaseRoot,
    [Parameter(Mandatory = $true)][string]$BootstrapPythonPath,
    [switch]$Apply,
    [switch]$ApplyMigration,
    [switch]$ApproveBackwardCompatibleMigration,
    [switch]$ApproveWarnings
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'MesDeployment.Common.ps1')
. (Join-Path $PSScriptRoot 'MesRelease.Installation.Common.ps1')
. (Join-Path $PSScriptRoot 'MesPythonRuntime.Common.ps1')
. (Join-Path $PSScriptRoot 'MesRelease.Activation.Common.ps1')

if ($ApplyMigration -and -not $Apply) {
    throw '-ApplyMigration requires -Apply.'
}
if ($ApplyMigration -and -not $ApproveBackwardCompatibleMigration) {
    throw 'Migration activation requires -ApproveBackwardCompatibleMigration after reviewing application rollback compatibility.'
}

$config = Import-MesDeploymentConfig -ConfigFile $ConfigFile
$root = [IO.Path]::GetFullPath($ReleaseRoot).TrimEnd('\')
$expectedBackend = [IO.Path]::GetFullPath((Join-Path $root 'current\backend')).TrimEnd('\')
$expectedPython = [IO.Path]::GetFullPath((Join-Path $expectedBackend '.venv\Scripts\python.exe')).TrimEnd('\')
if ([IO.Path]::GetFullPath([string]$config.BackendRoot).TrimEnd('\') -ne $expectedBackend) {
    throw 'Deployment BackendRoot must point to <ReleaseRoot>\current\backend.'
}
if ([IO.Path]::GetFullPath([string]$config.PythonPath).TrimEnd('\') -ne $expectedPython) {
    throw 'Deployment PythonPath must point to the active release .venv.'
}

$metadata = Get-MesReleasePackageMetadata `
    -PackagePath $PackagePath `
    -ManifestPath $ManifestPath `
    -ChecksumPath $ChecksumPath
$current = Join-Path $root 'current'
$previousRelease = Get-MesReleaseJunctionTarget -CurrentPath $current
if ((Split-Path -Leaf $previousRelease) -eq $metadata.Commit) {
    throw 'The approved package commit is already active.'
}

$powershell = Join-Path $PSHOME 'powershell.exe'
& $powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass `
    -File (Join-Path $PSScriptRoot 'Test-MesDeployment.ps1') `
    -ConfigFile $ConfigFile `
    -CheckRunningApi
$preflightExit = $LASTEXITCODE
if ($preflightExit -eq 2) {
    throw 'Deployment preflight failed.'
}
if ($preflightExit -eq 1 -and $Apply -and -not $ApproveWarnings) {
    throw 'Deployment preflight has warnings. Review them and re-run with -ApproveWarnings only when accepted.'
}
if (-not $Apply) {
    Write-Host 'release_activation_plan=validated'
    Write-Host "candidate_commit=$($metadata.Commit)"
    Write-Host "candidate_package_sha256=$($metadata.PackageSha256)"
    Write-Host 'No -Apply switch was supplied; the package was not installed and server state was not changed.'
    exit $preflightExit
}
if (-not $PSCmdlet.ShouldProcess($metadata.Commit, 'Install and activate MES release')) {
    Write-Host 'release_activation=cancelled'
    exit 0
}
if (-not (Test-MesAdministrator)) {
    throw 'Release activation requires an elevated PowerShell session.'
}

$install = Install-MesReleasePackage `
    -PackagePath $PackagePath `
    -ManifestPath $ManifestPath `
    -ChecksumPath $ChecksumPath `
    -ReleaseRoot $root
$runtime = Initialize-MesPythonRuntime `
    -ReleasePath $install.ReleasePath `
    -BootstrapPythonPath $BootstrapPythonPath
$candidateBackend = Join-Path $install.ReleasePath 'backend'
$null = Test-MesInstalledRelease -ReleasePath $install.ReleasePath -Metadata $metadata
$unsafeWriters = @(Get-MesBroadAclEntries -Path $install.ReleasePath -AccessKind Write)
if ($unsafeWriters.Count -gt 0) {
    throw 'Candidate release has broad write access. Correct its ACL before activation.'
}

$service = Get-Service -Name $config.ApiServiceName -ErrorAction Stop
if ($service.Status -ne 'Running') {
    throw 'The currently active API service must be running before release activation.'
}

$reportRoot = Join-Path $config.OperationsLogRoot 'deployments'
New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null
$reportPath = Join-Path $reportRoot ("activation-{0}-{1}.json" -f ([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')), $metadata.Commit.Substring(0, 8))
$backupCreated = $false
$migrationApplied = $false
$activationStatus = 'CRITICAL'
$activationSummary = 'Release activation did not complete.'

$stopApi = {
    $currentService = Get-Service -Name $config.ApiServiceName -ErrorAction Stop
    if ($currentService.Status -ne 'Stopped') {
        Stop-Service -Name $config.ApiServiceName -ErrorAction Stop
        (Get-Service -Name $config.ApiServiceName).WaitForStatus('Stopped', (New-TimeSpan -Minutes 2))
    }
}
$startApi = {
    $currentService = Get-Service -Name $config.ApiServiceName -ErrorAction Stop
    if ($currentService.Status -ne 'Running') {
        Start-Service -Name $config.ApiServiceName -ErrorAction Stop
        (Get-Service -Name $config.ApiServiceName).WaitForStatus('Running', (New-TimeSpan -Minutes 2))
    }
}
$testApi = {
    $baseUri = [Uri]$config.ApiBaseUrl
    $deadline = [DateTime]::UtcNow.AddSeconds(60)
    $lastFailure = $null
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $health = Invoke-RestMethod -Uri ([Uri]::new($baseUri, '/api/v1/health')) -TimeoutSec 5
            $ready = Invoke-RestMethod -Uri ([Uri]::new($baseUri, '/api/v1/ready')) -TimeoutSec 5
            if ($health.status -eq 'ok' -and $ready.status -eq 'ready') { return $true }
        }
        catch { $lastFailure = $_ }
        Start-Sleep -Milliseconds 500
    }
    if ($null -ne $lastFailure) {
        throw [InvalidOperationException]::new('API health/readiness did not succeed before the activation deadline.', $lastFailure.Exception)
    }
    throw 'API health/readiness did not succeed before the activation deadline.'
}

try {
    $null = & $stopApi

    Push-Location $config.BackendRoot
    try {
        $null = Invoke-MesNativeCommand `
            -Executable $config.PythonPath `
            -Arguments @(
                '-m', 'scripts.backup_mes',
                '--env-file', $config.EnvFile,
                '--backup-root', $config.BackupRoot,
                '--pg-bin', $config.PgBin,
                '--consistency-mode', 'maintenance'
            )
        $backupCreated = $true
    }
    finally { Pop-Location }

    Push-Location $candidateBackend
    try {
        $alembicPrefix = @(
            '-m', 'dotenv', '-f', $config.EnvFile, 'run', '--',
            $runtime.PythonPath, '-m', 'alembic'
        )
        $null = Invoke-MesNativeCommand -Executable $runtime.PythonPath -Arguments ($alembicPrefix + @('current'))
        $null = Invoke-MesNativeCommand -Executable $runtime.PythonPath -Arguments ($alembicPrefix + @('heads'))
        if ($ApplyMigration) {
            $null = Invoke-MesNativeCommand -Executable $runtime.PythonPath -Arguments ($alembicPrefix + @('upgrade', 'head'))
            $migrationApplied = $true
        }
        $null = Invoke-MesNativeCommand -Executable $runtime.PythonPath -Arguments ($alembicPrefix + @('current', '--check-heads'))
        $null = Invoke-MesNativeCommand -Executable $runtime.PythonPath -Arguments ($alembicPrefix + @('check'))
    }
    finally { Pop-Location }

    $activation = Invoke-MesReleaseActivationSwitch `
        -ReleaseRoot $root `
        -CandidateReleasePath $install.ReleasePath `
        -StopApi $stopApi `
        -StartCandidateApi $startApi `
        -TestCandidateApi $testApi `
        -StartPreviousApi $startApi `
        -TestPreviousApi $testApi
    $activationStatus = 'OK'
    $activationSummary = 'Candidate release activated and passed health/readiness checks.'
}
catch {
    $activeTarget = Get-MesReleaseJunctionTarget -CurrentPath $current
    if ($activeTarget -eq $previousRelease) {
        try { $null = & $startApi } catch { Write-Warning 'The previous API service could not be restarted automatically.' }
    }
    $activationSummary = "Release activation failed: $($_.Exception.GetType().Name)"
    throw
}
finally {
    $activeTarget = Get-MesReleaseJunctionTarget -CurrentPath $current
    $report = [ordered]@{
        format_version = 1
        generated_at_utc = [DateTime]::UtcNow.ToString('o')
        status = $activationStatus
        summary = $activationSummary
        package_commit = $metadata.Commit
        package_sha256 = $metadata.PackageSha256
        previous_release = $previousRelease
        final_active_release = $activeTarget
        backup_created = $backupCreated
        migration_applied = $migrationApplied
        backward_compatible_migration_approved = [bool]$ApproveBackwardCompatibleMigration
    }
    $temporaryReport = "$reportPath.tmp"
    $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $temporaryReport -Encoding UTF8
    Move-Item -LiteralPath $temporaryReport -Destination $reportPath
    Write-Host "release_activation_report=$reportPath"
}

Write-Host 'release_activation=complete'
