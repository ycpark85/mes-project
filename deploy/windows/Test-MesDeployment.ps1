[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ConfigFile,
    [switch]$CheckRunningApi
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'MesDeployment.Common.ps1')

$config = Import-MesDeploymentConfig -ConfigFile $ConfigFile
$failures = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]

function Add-CheckFailure([string]$Message) {
    $script:failures.Add($Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Add-CheckWarning([string]$Message) {
    $script:warnings.Add($Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Add-CheckSuccess([string]$Message) {
    Write-Host "[OK] $Message" -ForegroundColor Green
}

$requiredFiles = @(
    $config.PythonPath,
    $config.EnvFile,
    $config.MonitorEnvFile,
    (Join-Path $config.BackendRoot 'alembic.ini'),
    (Join-Path $config.BackendRoot 'scripts\backup_mes.py'),
    (Join-Path $config.BackendRoot 'scripts\check_mes_operations.py'),
    (Join-Path $config.BackendRoot 'scripts\configure_postgres_monitoring.py'),
    (Join-Path $config.PgBin 'pg_dump.exe'),
    (Join-Path $config.PgBin 'pg_restore.exe')
)
foreach ($path in $requiredFiles) {
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        Add-CheckSuccess "Required file exists: $path"
    }
    else {
        Add-CheckFailure "Required file is missing: $path"
    }
}

$writeProtectedPaths = @(
    $config.BackendRoot,
    $configFile,
    $config.EnvFile,
    $config.MonitorEnvFile,
    $PSScriptRoot
)
foreach ($path in $writeProtectedPaths) {
    if (Test-Path -LiteralPath $path) {
        $unsafeWriters = @(Get-MesBroadAclEntries -Path $path -AccessKind Write)
        if ($unsafeWriters.Count -gt 0) {
            Add-CheckFailure "Broad write access must be removed from $path"
        }
    }
}
foreach ($path in @($config.EnvFile, $config.MonitorEnvFile)) {
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        $unsafeReaders = @(Get-MesBroadAclEntries -Path $path -AccessKind Read)
        if ($unsafeReaders.Count -gt 0) {
            Add-CheckFailure "Broad read access must be removed from protected env file: $path"
        }
    }
}

if ($failures.Count -eq 0) {
    $appEnv = Read-MesEnvFile -Path $config.EnvFile
    $monitorEnv = Read-MesEnvFile -Path $config.MonitorEnvFile
    $requiredAppKeys = @(
        'DATABASE_URL', 'AUTH_SECRET_KEY', 'BACKEND_ALLOWED_HOSTS',
        'DRAWING_STORAGE_ROOT', 'DEFECT_PHOTO_STORAGE_ROOT',
        'PLATE_DATA_STORAGE_ROOT'
    )
    foreach ($key in $requiredAppKeys) {
        if (-not $appEnv.ContainsKey($key) -or [string]::IsNullOrWhiteSpace([string]$appEnv[$key])) {
            Add-CheckFailure "Application env value is missing: $key"
        }
    }
    if (-not $appEnv.ContainsKey('APP_ENV') -or $appEnv['APP_ENV'] -notmatch '^(?i:prod|production)$') {
        Add-CheckFailure 'APP_ENV must be prod or production.'
    }
    if ($appEnv.ContainsKey('AUTH_SECRET_KEY')) {
        $secret = [string]$appEnv['AUTH_SECRET_KEY']
        if ($secret.Length -lt 32 -or $secret -eq 'mes-dev-auth-secret-key-change-me') {
            Add-CheckFailure 'AUTH_SECRET_KEY must be a non-default value of at least 32 characters.'
        }
    }
    if (-not $monitorEnv.ContainsKey('MES_MONITOR_DATABASE_URL') -and -not $monitorEnv.ContainsKey('DATABASE_URL')) {
        Add-CheckFailure 'Monitor env must contain MES_MONITOR_DATABASE_URL or DATABASE_URL.'
    }

    $storagePaths = New-Object System.Collections.Generic.List[string]
    foreach ($key in @('DRAWING_STORAGE_ROOT', 'DEFECT_PHOTO_STORAGE_ROOT', 'PLATE_DATA_STORAGE_ROOT')) {
        if ($appEnv.ContainsKey($key)) {
            $storagePath = [string]$appEnv[$key]
            $storagePaths.Add($storagePath)
            if (-not (Test-Path -LiteralPath $storagePath -PathType Container)) {
                Add-CheckFailure "Storage directory is missing: $key"
            }
            if (Test-MesPathOverlap -First $config.BackupRoot -Second $storagePath) {
                Add-CheckFailure "Backup root and storage root overlap: $key"
            }
        }
    }

    foreach ($directory in @($config.BackupRoot, $config.MonitorHistoryRoot, $config.OperationsLogRoot)) {
        if (Test-Path -LiteralPath $directory -PathType Container) {
            Add-CheckSuccess "Operational directory exists: $directory"
        }
        else {
            Add-CheckWarning "Operational directory will be created during apply: $directory"
        }
    }

    Push-Location $config.BackendRoot
    try {
        $alembicPrefix = @(
            '-m', 'dotenv', '-f', $config.EnvFile, 'run', '--',
            $config.PythonPath, '-m', 'alembic'
        )
        $null = Invoke-MesNativeCommand -Executable $config.PythonPath -Arguments ($alembicPrefix + @('current'))
        Add-CheckSuccess 'Alembic current revision is readable.'
        $null = Invoke-MesNativeCommand -Executable $config.PythonPath -Arguments ($alembicPrefix + @('heads'))
        Add-CheckSuccess 'Alembic migration heads are readable.'

        $checkArguments = @(
            '-m', 'scripts.check_mes_operations',
            '--env-file', $config.EnvFile,
            '--monitor-env-file', $config.MonitorEnvFile,
            '--backup-root', $config.BackupRoot,
            '--restore-record', $config.RestoreRecordPath,
            '--format', 'text'
        )
        $operationsExit = Invoke-MesNativeCommand `
            -Executable $config.PythonPath `
            -Arguments $checkArguments `
            -AllowedExitCodes @(0, 1, 2)
        if ($operationsExit -eq 2) {
            Add-CheckFailure 'Operations check reported a critical condition.'
        }
        elseif ($operationsExit -eq 1) {
            Add-CheckWarning 'Operations check reported one or more warnings.'
        }
        else {
            Add-CheckSuccess 'Operations check is healthy.'
        }
    }
    catch {
        Add-CheckFailure $_.Exception.Message
    }
    finally {
        Pop-Location
    }
}

if ($CheckRunningApi) {
    try {
        $baseUri = [Uri]$config.ApiBaseUrl
        $healthUri = [Uri]::new($baseUri, '/api/v1/health')
        $readyUri = [Uri]::new($baseUri, '/api/v1/ready')
        $health = Invoke-RestMethod -Uri $healthUri -Method Get -TimeoutSec 10
        $ready = Invoke-RestMethod -Uri $readyUri -Method Get -TimeoutSec 10
        if ($health.status -ne 'ok' -or $ready.status -ne 'ready') {
            throw 'Health or readiness response was not healthy.'
        }
        Add-CheckSuccess 'API health and readiness checks passed.'
    }
    catch {
        Add-CheckFailure "API check failed: $($_.Exception.Message)"
    }
}

Write-Host "preflight_warnings=$($warnings.Count)"
Write-Host "preflight_failures=$($failures.Count)"
if ($failures.Count -gt 0) {
    exit 2
}
if ($warnings.Count -gt 0) {
    exit 1
}
exit 0
