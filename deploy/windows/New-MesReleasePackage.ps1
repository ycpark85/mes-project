[CmdletBinding()]
param(
    [string]$RepositoryRoot,
    [Parameter(Mandatory = $true)][string]$OutputRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'MesDeployment.Common.ps1')

if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    $RepositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
}
else {
    $RepositoryRoot = (Resolve-Path -LiteralPath $RepositoryRoot -ErrorAction Stop).Path
}
$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
if (Test-MesPathOverlap -First $RepositoryRoot -Second $OutputRoot) {
    throw 'Release packages must be created outside the Git repository.'
}

$backendRoot = Join-Path $RepositoryRoot 'backend'
$python = Join-Path $backendRoot '.venv\Scripts\python.exe'
$internalProject = Join-Path $RepositoryRoot 'frontend-wpf\Mes.WpfClean\Mes.Wpf\Mes.Wpf\Mes.Wpf.csproj'
$vendorProject = Join-Path $RepositoryRoot 'frontend-wpf\Mes.WpfClean\Mes.Wpf\Mes.Vendor.Wpf\Mes.Vendor.Wpf.csproj'
$releaseGate = Join-Path $PSScriptRoot 'Test-MesRelease.ps1'
foreach ($path in @($python, $internalProject, $vendorProject, $releaseGate)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required package input is missing: $path"
    }
}

$commit = (& git -C $RepositoryRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $commit -notmatch '^[0-9a-f]{40}$') {
    throw 'Unable to read the release Git commit.'
}
$branch = (& git -C $RepositoryRoot branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($branch)) {
    throw 'A named Git branch is required for release packaging.'
}
$commitTimestamp = (& git -C $RepositoryRoot show -s --format=%cI HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to read the release commit timestamp.'
}
$shortCommit = $commit.Substring(0, 8)
$packagePath = Join-Path $OutputRoot "mes-v2-$shortCommit.zip"
$manifestPath = [System.IO.Path]::ChangeExtension($packagePath, 'manifest.json')
$checksumPath = [System.IO.Path]::ChangeExtension($packagePath, 'sha256')
foreach ($path in @($packagePath, $manifestPath, $checksumPath)) {
    if (Test-Path -LiteralPath $path) {
        throw "Release output already exists: $path"
    }
}

New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
$stagingRoot = Join-Path $OutputRoot (".staging-{0}-{1}" -f $shortCommit, $PID)
if (Test-Path -LiteralPath $stagingRoot) {
    throw "Unexpected staging path already exists: $stagingRoot"
}
New-Item -ItemType Directory -Path $stagingRoot | Out-Null
$completed = $false

try {
    $validationRoot = Join-Path $OutputRoot 'validation'
    & $releaseGate `
        -RepositoryRoot $RepositoryRoot `
        -ReportRoot $validationRoot `
        -RequireCleanWorktree
    if ($LASTEXITCODE -ne 0) {
        throw "Release quality gate failed with exit code $LASTEXITCODE."
    }
    $validationReport = Get-ChildItem `
        -LiteralPath $validationRoot `
        -Filter 'release-validation.json' `
        -Recurse `
        -File | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    if ($null -eq $validationReport) {
        throw 'Release quality gate did not produce a validation report.'
    }

    Push-Location $backendRoot
    try {
        $null = Invoke-MesNativeCommand `
            -Executable $python `
            -Arguments @(
                '-m', 'scripts.release_package', 'stage-source',
                '--repository-root', $RepositoryRoot,
                '--staging-root', $stagingRoot,
                '--commit', $commit
            )
    }
    finally {
        Pop-Location
    }

    $internalOutput = Join-Path $stagingRoot 'clients\internal'
    $vendorOutput = Join-Path $stagingRoot 'clients\vendor'
    $null = Invoke-MesNativeCommand `
        -Executable 'dotnet' `
        -Arguments @(
            'publish', $internalProject, '-c', 'Release', '--no-restore',
            '--framework', 'net8.0-windows', '--output', $internalOutput, '--nologo'
        )
    $null = Invoke-MesNativeCommand `
        -Executable 'dotnet' `
        -Arguments @(
            'publish', $vendorProject, '-c', 'Release', '--no-restore',
            '--framework', 'net8.0-windows', '--output', $vendorOutput, '--nologo'
        )

    foreach ($clientRoot in @($internalOutput, $vendorOutput)) {
        foreach ($name in @('appsettings.json', 'appsettings.Development.json')) {
            $path = Join-Path $clientRoot $name
            if (Test-Path -LiteralPath $path -PathType Leaf) {
                Remove-Item -LiteralPath $path -Force
            }
        }
        Get-ChildItem -LiteralPath $clientRoot -Filter '*.pdb' -File | Remove-Item -Force
    }

    $wheelhouse = Join-Path $stagingRoot 'backend\wheelhouse'
    New-Item -ItemType Directory -Path $wheelhouse | Out-Null
    $null = Invoke-MesNativeCommand `
        -Executable $python `
        -Arguments @(
            '-m', 'pip', 'download',
            '--requirement', (Join-Path $stagingRoot 'backend\requirements.txt'),
            '--dest', $wheelhouse,
            '--only-binary=:all:',
            '--disable-pip-version-check'
        )
    Push-Location $backendRoot
    try {
        $null = Invoke-MesNativeCommand `
            -Executable $python `
            -Arguments @(
                '-m', 'scripts.release_package', 'prepare-wheelhouse',
                '--requirements', (Join-Path $stagingRoot 'backend\requirements.txt'),
                '--wheelhouse', $wheelhouse
            )
    }
    finally {
        Pop-Location
    }

    Push-Location $backendRoot
    try {
        $headOutput = & $python -m alembic heads
        if ($LASTEXITCODE -ne 0) {
            throw 'Unable to read the Alembic release head.'
        }
        $headMatches = @($headOutput | Where-Object { $_ -match '^([0-9a-f]+)\s+\(head\)$' })
        if ($headMatches.Count -ne 1) {
            throw 'Release packaging requires exactly one Alembic head.'
        }
        $null = $headMatches[0] -match '^([0-9a-f]+)'
        $alembicHead = $matches[1]

        $null = Invoke-MesNativeCommand `
            -Executable $python `
            -Arguments @(
                '-m', 'scripts.release_package', 'finalize',
                '--staging-root', $stagingRoot,
                '--output-zip', $packagePath,
                '--commit', $commit,
                '--branch', $branch,
                '--commit-timestamp', $commitTimestamp,
                '--alembic-head', $alembicHead,
                '--validation-report', $validationReport.FullName
            )
    }
    finally {
        Pop-Location
    }
    $completed = $true
}
finally {
    if ($completed -and (Test-Path -LiteralPath $stagingRoot -PathType Container)) {
        $stagingFull = [System.IO.Path]::GetFullPath($stagingRoot).TrimEnd('\') + '\'
        $outputFull = [System.IO.Path]::GetFullPath($OutputRoot).TrimEnd('\') + '\'
        if (-not $stagingFull.StartsWith($outputFull, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Refusing to remove a staging path outside the release output root.'
        }
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
}

if (-not $completed) {
    Write-Warning "Incomplete staging files were retained for diagnosis: $stagingRoot"
    exit 2
}

Write-Host "release_package=$packagePath"
Write-Host "release_manifest=$manifestPath"
Write-Host "release_checksum=$checksumPath"
Write-Host "release_validation_report=$($validationReport.FullName)"
