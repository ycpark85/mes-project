[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PackagePath,
    [Parameter(Mandatory = $true)][string]$ManifestPath,
    [Parameter(Mandatory = $true)][string]$ChecksumPath,
    [Parameter(Mandatory = $true)][string]$BootstrapPythonPath,
    [Parameter(Mandatory = $true)][string]$EnvFile,
    [Parameter(Mandatory = $true)][string]$RehearsalRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'MesDeployment.Common.ps1')
. (Join-Path $PSScriptRoot 'MesRelease.Installation.Common.ps1')
. (Join-Path $PSScriptRoot 'MesPythonRuntime.Common.ps1')

$envPath = (Resolve-Path -LiteralPath $EnvFile -ErrorAction Stop).Path
$envValues = Read-MesEnvFile -Path $envPath
if ($envValues.ContainsKey('APP_ENV') -and $envValues['APP_ENV'] -match '^(?i:prod|production)$') {
    throw 'Runtime rehearsal refuses a production environment file.'
}
if (-not $envValues.ContainsKey('DATABASE_URL')) {
    throw 'Runtime rehearsal env file must contain DATABASE_URL.'
}
$databaseUrlValue = ([string]$envValues['DATABASE_URL']).Trim().Trim([char[]]@('"', "'"))
try {
    $databaseUri = [Uri]$databaseUrlValue
}
catch {
    throw 'Runtime rehearsal DATABASE_URL is invalid.'
}
if ($databaseUri.Scheme -notmatch '^postgres(?:ql)?(?:\+psycopg)?$' -or $databaseUri.Host -notin @('localhost', '127.0.0.1', '::1')) {
    throw 'Runtime rehearsal permits only a local PostgreSQL database.'
}

$root = [IO.Path]::GetFullPath($RehearsalRoot)
if (Test-Path -LiteralPath $root) {
    throw "Runtime rehearsal root must not already exist: $root"
}
New-Item -ItemType Directory -Path $root | Out-Null
$serverRoot = Join-Path $root 'server'
$releasesRoot = Join-Path $serverRoot 'releases'
New-Item -ItemType Directory -Path $releasesRoot -Force | Out-Null
$previousCommit = '0000000000000000000000000000000000000000'
$previousRelease = Join-Path $releasesRoot $previousCommit
New-Item -ItemType Directory -Path $previousRelease | Out-Null
Set-Content -LiteralPath (Join-Path $previousRelease 'REHEARSAL-PREVIOUS.txt') -Value 'previous release' -Encoding ASCII
New-Item -ItemType Junction -Path (Join-Path $serverRoot 'current') -Target $previousRelease | Out-Null
$steps = New-Object System.Collections.Generic.List[object]

function Add-RuntimeStep([string]$Name, [string]$Summary) {
    $script:steps.Add([ordered]@{ name = $Name; status = 'OK'; summary = $Summary })
}

$install = Install-MesReleasePackage `
    -PackagePath $PackagePath `
    -ManifestPath $ManifestPath `
    -ChecksumPath $ChecksumPath `
    -ReleaseRoot $serverRoot
Add-RuntimeStep 'verified_package_install' "Package installed as $($install.Commit)"

$runtime = Initialize-MesPythonRuntime `
    -ReleasePath $install.ReleasePath `
    -BootstrapPythonPath $BootstrapPythonPath
Add-RuntimeStep 'offline_python_runtime' "Python $($runtime.PythonVersion), $($runtime.WheelCount) wheels"

$current = Join-Path $serverRoot 'current'
$previousFull = [IO.Path]::GetFullPath($previousRelease).TrimEnd('\')
if ((Get-MesReleaseJunctionTarget -CurrentPath $current) -ne $previousFull) {
    throw 'Runtime preparation changed the active release pointer.'
}

$listener = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, 0)
$listener.Start()
$port = ([Net.IPEndPoint]$listener.LocalEndpoint).Port
$listener.Stop()
$stdoutLog = Join-Path $root 'candidate-api.stdout.log'
$stderrLog = Join-Path $root 'candidate-api.stderr.log'
$oldAppEnv = $env:APP_ENV
$oldAllowedHosts = $env:BACKEND_ALLOWED_HOSTS
$hadAppEnv = Test-Path Env:APP_ENV
$hadAllowedHosts = Test-Path Env:BACKEND_ALLOWED_HOSTS
$env:APP_ENV = 'dev'
$env:BACKEND_ALLOWED_HOSTS = '["127.0.0.1","localhost"]'
$candidate = $null
try {
    $arguments = @(
        '-m', 'uvicorn', 'app.main:app',
        '--host', '127.0.0.1',
        '--port', [string]$port,
        '--lifespan', 'off',
        '--env-file', ('"' + $envPath + '"'),
        '--log-level', 'warning'
    )
    $candidate = Start-Process `
        -FilePath $runtime.PythonPath `
        -ArgumentList $arguments `
        -WorkingDirectory (Join-Path $install.ReleasePath 'backend') `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -WindowStyle Hidden `
        -PassThru
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    $health = $null
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($candidate.HasExited) {
            throw "Candidate API exited before health check with code $($candidate.ExitCode)."
        }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/v1/health" -TimeoutSec 2
            break
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    }
    if ($null -eq $health -or $health.status -ne 'ok') {
        throw 'Candidate API health check did not become ready.'
    }
    $ready = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/v1/ready" -TimeoutSec 10
    if ($ready.status -ne 'ready') {
        throw 'Candidate API readiness check failed.'
    }
    Add-RuntimeStep 'candidate_health_readiness' 'Candidate API returned healthy and ready'
}
finally {
    if ($null -ne $candidate -and -not $candidate.HasExited) {
        Stop-Process -Id $candidate.Id -Force
        $candidate.WaitForExit(10000) | Out-Null
    }
    if ($hadAppEnv) { $env:APP_ENV = $oldAppEnv } else { Remove-Item Env:APP_ENV -ErrorAction SilentlyContinue }
    if ($hadAllowedHosts) { $env:BACKEND_ALLOWED_HOSTS = $oldAllowedHosts } else { Remove-Item Env:BACKEND_ALLOWED_HOSTS -ErrorAction SilentlyContinue }
}

$failureListener = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, 0)
$failureListener.Start()
$failurePort = ([Net.IPEndPoint]$failureListener.LocalEndpoint).Port
$failureListener.Stop()
$failureStdout = Join-Path $root 'failed-api.stdout.log'
$failureStderr = Join-Path $root 'failed-api.stderr.log'
$failedProcess = Start-Process `
    -FilePath $runtime.PythonPath `
    -ArgumentList @('-m', 'uvicorn', 'app.module_that_does_not_exist:app', '--host', '127.0.0.1', '--port', [string]$failurePort, '--lifespan', 'off') `
    -WorkingDirectory (Join-Path $install.ReleasePath 'backend') `
    -RedirectStandardOutput $failureStdout `
    -RedirectStandardError $failureStderr `
    -WindowStyle Hidden `
    -PassThru
if (-not $failedProcess.WaitForExit(10000)) {
    Stop-Process -Id $failedProcess.Id -Force
    throw 'Injected API startup failure did not exit.'
}
if ($failedProcess.ExitCode -eq 0) {
    throw 'Injected API startup failure returned success.'
}
if ((Get-MesReleaseJunctionTarget -CurrentPath $current) -ne $previousFull) {
    throw 'Candidate startup failure changed the active release pointer.'
}
Add-RuntimeStep 'startup_failure_isolation' 'Failed candidate left the previous release active'

$report = [ordered]@{
    format_version = 1
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    status = 'OK'
    rehearsal_root = $root
    package_commit = $install.Commit
    package_sha256 = $install.PackageSha256
    python_version = $runtime.PythonVersion
    wheel_count = $runtime.WheelCount
    final_active_commit = $previousCommit
    production_database_used = $false
    database_migrated = $false
    application_lifespan_enabled = $false
    windows_services_changed = $false
    production_configuration_changed = $false
    steps = $steps
}
$reportPath = Join-Path $root 'runtime-rehearsal.json'
$temporaryReport = "$reportPath.tmp"
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $temporaryReport -Encoding UTF8
Move-Item -LiteralPath $temporaryReport -Destination $reportPath
Write-Host 'MES runtime rehearsal: OK'
foreach ($step in $steps) {
    Write-Host ("[{0}] {1}: {2}" -f $step.status, $step.name, $step.summary)
}
Write-Host "runtime_rehearsal_report=$reportPath"
