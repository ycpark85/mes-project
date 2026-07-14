[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$ConfigFile,
    [switch]$ApplyPostgresMonitoring,
    [switch]$ApprovePostgresRestart,
    [switch]$ApproveWarnings,
    [switch]$ApplyMigration,
    [switch]$RegisterOperationsTasks,
    [switch]$RunSmokeTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'MesDeployment.Common.ps1')

$config = Import-MesDeploymentConfig -ConfigFile $ConfigFile
$actionRequested = $ApplyPostgresMonitoring -or $ApplyMigration -or $RegisterOperationsTasks

$powershell = Join-Path $PSHOME 'powershell.exe'
& $powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass `
    -File (Join-Path $PSScriptRoot 'Test-MesDeployment.ps1') `
    -ConfigFile $ConfigFile
$preflightExit = $LASTEXITCODE
if ($preflightExit -eq 2) {
    throw 'Deployment preflight failed.'
}
if ($preflightExit -eq 1 -and $actionRequested -and -not $ApproveWarnings) {
    throw 'Deployment preflight has warnings. Review them and re-run with -ApproveWarnings only when accepted.'
}
if (-not $actionRequested) {
    Write-Host 'deployment_plan=validated'
    Write-Host 'No apply switches were supplied; no server state was changed.'
    exit $preflightExit
}
if (-not (Test-MesAdministrator)) {
    throw 'Deployment apply steps require an elevated PowerShell session.'
}

foreach ($directory in @(
    $config.BackupRoot,
    $config.MonitorHistoryRoot,
    $config.OperationsLogRoot,
    ([System.IO.Path]::GetDirectoryName($config.RestoreRecordPath))
)) {
    if ($PSCmdlet.ShouldProcess($directory, 'Create operational directory')) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
}

$requiresMaintenance = $ApplyPostgresMonitoring -or $ApplyMigration
$apiWasRunning = $false
$apiStopped = $false
$maintenanceSucceeded = -not $requiresMaintenance
try {
    if ($requiresMaintenance) {
        $apiService = Get-Service -Name $config.ApiServiceName -ErrorAction Stop
        $apiWasRunning = $apiService.Status -eq 'Running'
        if (-not $apiWasRunning) {
            try {
                $healthUri = [Uri]::new([Uri]$config.ApiBaseUrl, '/api/v1/health')
                $null = Invoke-RestMethod -Uri $healthUri -Method Get -TimeoutSec 3
                throw 'The API responds while its Windows service is stopped. Stop the unmanaged API process before deployment.'
            }
            catch {
                if ($_.Exception.Message -like 'The API responds while*') {
                    throw
                }
            }
        }
        if ($apiWasRunning -and $PSCmdlet.ShouldProcess($config.ApiServiceName, 'Stop API service for maintenance')) {
            Stop-Service -Name $config.ApiServiceName -ErrorAction Stop
            $apiStopped = $true
        }
        if ($apiWasRunning -and -not $apiStopped) {
            throw 'Maintenance cannot continue while the API service is running.'
        }

        Push-Location $config.BackendRoot
        try {
            if ($PSCmdlet.ShouldProcess($config.BackupRoot, 'Create pre-deployment maintenance backup')) {
                $null = Invoke-MesNativeCommand `
                    -Executable $config.PythonPath `
                    -Arguments @(
                        '-m', 'scripts.backup_mes',
                        '--env-file', $config.EnvFile,
                        '--backup-root', $config.BackupRoot,
                        '--pg-bin', $config.PgBin,
                        '--consistency-mode', 'maintenance'
                    )
            }

            if ($ApplyPostgresMonitoring -and $PSCmdlet.ShouldProcess('PostgreSQL monitoring', 'Prepare pg_monitor and pg_stat_statements')) {
                $prepareExit = Invoke-MesNativeCommand `
                    -Executable $config.PythonPath `
                    -Arguments @(
                        '-m', 'scripts.configure_postgres_monitoring',
                        '--env-file', $config.EnvFile,
                        '--monitor-env-file', $config.MonitorEnvFile,
                        '--phase', 'prepare',
                        '--apply'
                    ) `
                    -AllowedExitCodes @(0, 3)
                if ($prepareExit -eq 3) {
                    if (-not $ApprovePostgresRestart) {
                        throw 'PostgreSQL restart is required. Re-run with -ApprovePostgresRestart in the maintenance window.'
                    }
                    if ($PSCmdlet.ShouldProcess($config.PostgresServiceName, 'Restart PostgreSQL')) {
                        Restart-Service -Name $config.PostgresServiceName -Force -ErrorAction Stop
                        (Get-Service -Name $config.PostgresServiceName).WaitForStatus('Running', (New-TimeSpan -Minutes 2))
                    }
                    $null = Invoke-MesNativeCommand `
                        -Executable $config.PythonPath `
                        -Arguments @(
                            '-m', 'scripts.configure_postgres_monitoring',
                            '--env-file', $config.EnvFile,
                            '--monitor-env-file', $config.MonitorEnvFile,
                            '--phase', 'finalize',
                            '--apply'
                        )
                }
            }

            if ($ApplyMigration -and $PSCmdlet.ShouldProcess('MES database', 'Apply Alembic upgrade to head')) {
                $null = Invoke-MesNativeCommand -Executable $config.PythonPath -Arguments @('-m', 'alembic', 'current')
                $null = Invoke-MesNativeCommand -Executable $config.PythonPath -Arguments @('-m', 'alembic', 'heads')
                $null = Invoke-MesNativeCommand -Executable $config.PythonPath -Arguments @('-m', 'alembic', 'upgrade', 'head')
                $null = Invoke-MesNativeCommand -Executable $config.PythonPath -Arguments @('-m', 'alembic', 'current', '--check-heads')
                $null = Invoke-MesNativeCommand -Executable $config.PythonPath -Arguments @('-m', 'alembic', 'check')
            }
        }
        finally {
            Pop-Location
        }
        $maintenanceSucceeded = $true
    }

    if ($RegisterOperationsTasks) {
        & $powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass `
            -File (Join-Path $PSScriptRoot 'Set-MesOperationsScheduledTasks.ps1') `
            -ConfigFile $ConfigFile `
            -Mode Register
        if ($LASTEXITCODE -ne 0) {
            throw 'Scheduled task registration failed.'
        }
    }
}
finally {
    if ($apiWasRunning -and $apiStopped -and $maintenanceSucceeded) {
        Start-Service -Name $config.ApiServiceName -ErrorAction Stop
        (Get-Service -Name $config.ApiServiceName).WaitForStatus('Running', (New-TimeSpan -Minutes 2))
    }
    elseif ($apiWasRunning -and $apiStopped) {
        Write-Warning 'Maintenance failed. The API service remains stopped pending operator review.'
    }
}

if ($RunSmokeTest) {
    & $powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass `
        -File (Join-Path $PSScriptRoot 'Test-MesDeployment.ps1') `
        -ConfigFile $ConfigFile `
        -CheckRunningApi
    if ($LASTEXITCODE -eq 2) {
        throw 'Post-deployment smoke test failed.'
    }
}

Write-Host 'deployment_activation=complete'
