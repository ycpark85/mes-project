[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateSet('Backup', 'Monitor')][string]$Operation,
    [Parameter(Mandatory = $true)][string]$ConfigFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'MesDeployment.Common.ps1')

$config = Import-MesDeploymentConfig -ConfigFile $ConfigFile
$logRoot = [System.IO.Path]::GetFullPath([string]$config.OperationsLogRoot)
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$timestamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$logPath = Join-Path $logRoot ("mes-{0}-{1}.log" -f $Operation.ToLowerInvariant(), $timestamp)
$temporaryLog = "$logPath.tmp"

Push-Location $config.BackendRoot
try {
    if ($Operation -eq 'Backup') {
        $arguments = @(
            '-m', 'scripts.backup_mes',
            '--env-file', $config.EnvFile,
            '--backup-root', $config.BackupRoot,
            '--pg-bin', $config.PgBin,
            '--consistency-mode', 'online'
        )
    }
    else {
        $arguments = @(
            '-m', 'scripts.check_mes_operations',
            '--env-file', $config.EnvFile,
            '--monitor-env-file', $config.MonitorEnvFile,
            '--backup-root', $config.BackupRoot,
            '--restore-record', $config.RestoreRecordPath,
            '--history-root', $config.MonitorHistoryRoot,
            '--format', 'text'
        )
    }

    & $config.PythonPath @arguments *> $temporaryLog
    $exitCode = $LASTEXITCODE
    Move-Item -LiteralPath $temporaryLog -Destination $logPath -Force
    exit $exitCode
}
catch {
    $_ | Out-String | Set-Content -LiteralPath $temporaryLog -Encoding UTF8
    Move-Item -LiteralPath $temporaryLog -Destination $logPath -Force
    exit 2
}
finally {
    Pop-Location
}
