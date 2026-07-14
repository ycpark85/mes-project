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
. (Join-Path $PSScriptRoot 'MesRelease.Activation.Common.ps1')

$envPath = (Resolve-Path -LiteralPath $EnvFile -ErrorAction Stop).Path
$envValues = Read-MesEnvFile -Path $envPath
if ($envValues.ContainsKey('APP_ENV') -and $envValues['APP_ENV'] -match '^(?i:prod|production)$') {
    throw 'Activation rehearsal refuses a production environment file.'
}
if (-not $envValues.ContainsKey('DATABASE_URL')) {
    throw 'Activation rehearsal env file must contain DATABASE_URL.'
}
$databaseUrlValue = ([string]$envValues['DATABASE_URL']).Trim().Trim([char[]]@('"', "'"))
$databaseUri = [Uri]$databaseUrlValue
if ($databaseUri.Scheme -notmatch '^postgres(?:ql)?(?:\+psycopg)?$' -or $databaseUri.Host -notin @('localhost', '127.0.0.1', '::1')) {
    throw 'Activation rehearsal permits only a local PostgreSQL database.'
}

$root = [IO.Path]::GetFullPath($RehearsalRoot)
if (Test-Path -LiteralPath $root) { throw "Activation rehearsal root must not already exist: $root" }
New-Item -ItemType Directory -Path $root | Out-Null
$serverRoot = Join-Path $root 'server'
$previousCommit = '0000000000000000000000000000000000000000'
$previousRelease = Join-Path $serverRoot "releases\$previousCommit"
New-Item -ItemType Directory -Path $previousRelease -Force | Out-Null
Set-Content -LiteralPath (Join-Path $previousRelease 'REHEARSAL-PREVIOUS.txt') -Value 'previous release' -Encoding ASCII
New-Item -ItemType Junction -Path (Join-Path $serverRoot 'current') -Target $previousRelease | Out-Null

$install = Install-MesReleasePackage -PackagePath $PackagePath -ManifestPath $ManifestPath -ChecksumPath $ChecksumPath -ReleaseRoot $serverRoot
$runtime = Initialize-MesPythonRuntime -ReleasePath $install.ReleasePath -BootstrapPythonPath $BootstrapPythonPath
$listener = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, 0)
$listener.Start(); $port = ([Net.IPEndPoint]$listener.LocalEndpoint).Port; $listener.Stop()
$stdoutLog = Join-Path $root 'candidate.stdout.log'
$stderrLog = Join-Path $root 'candidate.stderr.log'
$script:apiProcess = $null
$script:activationMode = 'valid'
$script:previousStarted = $false
$oldAppEnv = $env:APP_ENV
$oldAllowedHosts = $env:BACKEND_ALLOWED_HOSTS
$hadAppEnv = Test-Path Env:APP_ENV
$hadAllowedHosts = Test-Path Env:BACKEND_ALLOWED_HOSTS
$env:APP_ENV = 'dev'
$env:BACKEND_ALLOWED_HOSTS = '["127.0.0.1","localhost"]'

$stopApi = {
    if ($null -ne $script:apiProcess -and -not $script:apiProcess.HasExited) {
        Stop-Process -Id $script:apiProcess.Id -Force
        $script:apiProcess.WaitForExit(10000) | Out-Null
    }
    $script:apiProcess = $null
}
$startCandidate = {
    $module = if ($script:activationMode -eq 'valid') { 'app.main:app' } else { 'app.missing_activation_module:app' }
    $script:apiProcess = Start-Process `
        -FilePath $runtime.PythonPath `
        -ArgumentList @('-m', 'uvicorn', $module, '--host', '127.0.0.1', '--port', [string]$port, '--lifespan', 'off', '--env-file', ('"' + $envPath + '"'), '--log-level', 'warning') `
        -WorkingDirectory (Join-Path $install.ReleasePath 'backend') `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -WindowStyle Hidden `
        -PassThru
}
$testCandidate = {
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($script:apiProcess.HasExited) { throw 'Candidate API exited before readiness.' }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/v1/health" -TimeoutSec 2
            $ready = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/v1/ready" -TimeoutSec 5
            if ($health.status -eq 'ok' -and $ready.status -eq 'ready') { return $true }
        }
        catch { Start-Sleep -Milliseconds 250 }
    }
    throw 'Candidate API did not become ready.'
}
$startPrevious = { $script:previousStarted = $true }
$testPrevious = { if (-not $script:previousStarted) { throw 'Previous release restart was not observed.' }; return $true }

$successObserved = $false
$failureRollbackObserved = $false
try {
    $success = Invoke-MesReleaseActivationSwitch -ReleaseRoot $serverRoot -CandidateReleasePath $install.ReleasePath -StopApi $stopApi -StartCandidateApi $startCandidate -TestCandidateApi $testCandidate -StartPreviousApi $startPrevious -TestPreviousApi $testPrevious
    if ($success.Status -ne 'ACTIVATED') { throw 'Successful activation did not complete.' }
    $successObserved = $true
    $null = & $stopApi
    $null = Set-MesReleaseJunction -ReleaseRoot $serverRoot -TargetReleasePath $previousRelease

    $script:activationMode = 'invalid'
    $script:previousStarted = $false
    try {
        $null = Invoke-MesReleaseActivationSwitch -ReleaseRoot $serverRoot -CandidateReleasePath $install.ReleasePath -StopApi $stopApi -StartCandidateApi $startCandidate -TestCandidateApi $testCandidate -StartPreviousApi $startPrevious -TestPreviousApi $testPrevious
        throw 'Injected candidate failure unexpectedly succeeded.'
    }
    catch {
        if ($_.Exception.Message -notlike 'Candidate activation failed;*') { throw }
    }
    if ((Get-MesReleaseJunctionTarget -CurrentPath (Join-Path $serverRoot 'current')) -ne [IO.Path]::GetFullPath($previousRelease).TrimEnd('\')) {
        throw 'Failed activation did not restore the previous release.'
    }
    if (-not $script:previousStarted) { throw 'Failed activation did not restart the previous release.' }
    $failureRollbackObserved = $true
}
finally {
    $null = & $stopApi
    if ($hadAppEnv) { $env:APP_ENV = $oldAppEnv } else { Remove-Item Env:APP_ENV -ErrorAction SilentlyContinue }
    if ($hadAllowedHosts) { $env:BACKEND_ALLOWED_HOSTS = $oldAllowedHosts } else { Remove-Item Env:BACKEND_ALLOWED_HOSTS -ErrorAction SilentlyContinue }
}

$report = [ordered]@{
    format_version = 1
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    status = 'OK'
    package_commit = $install.Commit
    package_sha256 = $install.PackageSha256
    python_version = $runtime.PythonVersion
    wheel_count = $runtime.WheelCount
    successful_activation_observed = $successObserved
    failed_activation_rollback_observed = $failureRollbackObserved
    final_active_commit = $previousCommit
    production_database_used = $false
    database_migrated = $false
    application_lifespan_enabled = $false
    windows_services_changed = $false
    production_configuration_changed = $false
}
$reportPath = Join-Path $root 'release-activation-rehearsal.json'
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$reportPath.tmp" -Encoding UTF8
Move-Item -LiteralPath "$reportPath.tmp" -Destination $reportPath
Write-Host 'MES release activation rehearsal: OK'
Write-Host "activation_rehearsal_report=$reportPath"
