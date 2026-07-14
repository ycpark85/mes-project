Set-StrictMode -Version Latest

function Get-MesPythonRuntimeMetadata {
    param([Parameter(Mandatory = $true)][string]$ReleasePath)

    $release = (Resolve-Path -LiteralPath $ReleasePath -ErrorAction Stop).Path
    $backend = Join-Path $release 'backend'
    $requirements = Join-Path $backend 'requirements.txt'
    $wheelhouse = Join-Path $backend 'wheelhouse'
    $manifestPath = Join-Path $wheelhouse 'wheelhouse-manifest.json'
    foreach ($path in @($requirements, $manifestPath)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Python runtime input is missing: $path"
        }
    }
    try {
        $manifest = Get-Content -Raw -LiteralPath $manifestPath -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        throw 'Wheelhouse manifest is invalid JSON.'
    }
    if (
        $manifest.format_version -ne 1 -or
        $manifest.python.implementation -ne 'CPython' -or
        $manifest.python.system -ne 'Windows' -or
        [string]$manifest.python.major_minor -notmatch '^\d+\.\d+$' -or
        [string]::IsNullOrWhiteSpace([string]$manifest.python.machine)
    ) {
        throw 'Wheelhouse manifest runtime target is invalid.'
    }
    $requirementsHash = (Get-FileHash -LiteralPath $requirements -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($requirementsHash -ne [string]$manifest.requirements_sha256) {
        throw 'Wheelhouse requirements hash does not match.'
    }
    $requirementLines = @(
        Get-Content -LiteralPath $requirements |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ -and -not $_.StartsWith('#') }
    )
    if ($requirementLines.Count -ne [int]$manifest.requirement_count) {
        throw 'Wheelhouse requirement count does not match.'
    }
    foreach ($line in $requirementLines) {
        if ($line -notmatch '^[A-Za-z0-9_.-]+==[^\s;]+$') {
            throw 'Runtime requirements must use exact versions.'
        }
    }
    $expectedWheels = @{}
    $manifestWheels = @($manifest.wheels)
    if ($manifestWheels.Count -eq 0 -or $manifestWheels.Count -ne [int]$manifest.wheel_count) {
        throw 'Wheelhouse manifest file count is invalid.'
    }
    foreach ($entry in $manifestWheels) {
        $filename = [string]$entry.filename
        if ([IO.Path]::GetFileName($filename) -ne $filename -or $filename -notlike '*.whl' -or $expectedWheels.ContainsKey($filename)) {
            throw 'Wheelhouse manifest contains an unsafe or duplicate filename.'
        }
        $expectedWheels[$filename] = $entry
    }
    $wheelhouseItems = @(Get-ChildItem -LiteralPath $wheelhouse -Force)
    foreach ($item in $wheelhouseItems) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $item.PSIsContainer) {
            throw "Wheelhouse contains an unsafe entry: $($item.Name)"
        }
        if ($item.Name -ne 'wheelhouse-manifest.json' -and -not $expectedWheels.ContainsKey($item.Name)) {
            throw "Wheelhouse contains an unlisted file: $($item.Name)"
        }
    }
    $actualWheels = @($wheelhouseItems | Where-Object { $_.Name -like '*.whl' })
    if ($actualWheels.Count -ne $expectedWheels.Count) {
        throw 'Wheelhouse file count differs from its manifest.'
    }
    foreach ($wheel in $actualWheels) {
        if (-not $expectedWheels.ContainsKey($wheel.Name)) {
            throw "Wheelhouse contains an unlisted file: $($wheel.Name)"
        }
        $entry = $expectedWheels[$wheel.Name]
        $hash = (Get-FileHash -LiteralPath $wheel.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        if ([long]$wheel.Length -ne [long]$entry.size -or $hash -ne [string]$entry.sha256) {
            throw "Wheelhouse file differs from its manifest: $($wheel.Name)"
        }
    }
    return [pscustomobject]@{
        ReleasePath = $release
        BackendPath = $backend
        RequirementsPath = $requirements
        WheelhousePath = $wheelhouse
        PythonImplementation = [string]$manifest.python.implementation
        PythonVersion = [string]$manifest.python.version
        PythonMajorMinor = [string]$manifest.python.major_minor
        PythonMachine = [string]$manifest.python.machine
        WheelCount = $actualWheels.Count
    }
}

function Get-MesBootstrapPythonMetadata {
    param([Parameter(Mandatory = $true)][string]$PythonPath)

    $python = (Resolve-Path -LiteralPath $PythonPath -ErrorAction Stop).Path
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = & $python -c 'import json, platform; print(json.dumps({"implementation": platform.python_implementation(), "version": platform.python_version(), "major_minor": ".".join(platform.python_version_tuple()[:2]), "machine": platform.machine()}))' 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($exitCode -ne 0) {
        throw 'Unable to inspect the bootstrap Python runtime.'
    }
    try {
        $metadata = ($output -join "`n") | ConvertFrom-Json
    }
    catch {
        throw 'Bootstrap Python returned invalid runtime metadata.'
    }
    return [pscustomobject]@{
        Path = $python
        Implementation = [string]$metadata.implementation
        Version = [string]$metadata.version
        MajorMinor = [string]$metadata.major_minor
        Machine = [string]$metadata.machine
    }
}

function Test-MesPythonRuntime {
    param(
        [Parameter(Mandatory = $true)][string]$PythonPath,
        [Parameter(Mandatory = $true)]$Metadata
    )

    $python = (Resolve-Path -LiteralPath $PythonPath -ErrorAction Stop).Path
    Push-Location $Metadata.BackendPath
    try {
        $null = Invoke-MesNativeCommand `
            -Executable $python `
            -Arguments @('-m', 'pip', 'check', '--disable-pip-version-check')
        $null = Invoke-MesNativeCommand `
            -Executable $python `
            -Arguments @(
                '-m', 'scripts.verify_python_runtime',
                '--requirements', $Metadata.RequirementsPath
            )
    }
    finally {
        Pop-Location
    }
    return $true
}

function Initialize-MesPythonRuntime {
    param(
        [Parameter(Mandatory = $true)][string]$ReleasePath,
        [Parameter(Mandatory = $true)][string]$BootstrapPythonPath
    )

    $metadata = Get-MesPythonRuntimeMetadata -ReleasePath $ReleasePath
    $bootstrap = Get-MesBootstrapPythonMetadata -PythonPath $BootstrapPythonPath
    if (
        $bootstrap.Implementation -ne $metadata.PythonImplementation -or
        $bootstrap.MajorMinor -ne $metadata.PythonMajorMinor -or
        $bootstrap.Machine -ne $metadata.PythonMachine
    ) {
        throw 'Bootstrap Python does not match the packaged wheelhouse target.'
    }
    $runtime = Join-Path $metadata.BackendPath '.venv'
    $runtimePython = Join-Path $runtime 'Scripts\python.exe'
    if (Test-Path -LiteralPath $runtime) {
        $runtimeItem = Get-Item -LiteralPath $runtime -Force
        if (($runtimeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'Existing Python runtime must not be a reparse point.'
        }
        $null = Test-MesPythonRuntime -PythonPath $runtimePython -Metadata $metadata
        return [pscustomobject]@{
            Status = 'ALREADY_PREPARED'
            PythonPath = $runtimePython
            PythonVersion = $metadata.PythonVersion
            WheelCount = $metadata.WheelCount
        }
    }

    $temporary = Join-Path $metadata.BackendPath ('.venv-installing-{0}' -f $PID)
    if (Test-Path -LiteralPath $temporary) {
        throw "Unexpected Python runtime staging path already exists: $temporary"
    }
    try {
        $null = Invoke-MesNativeCommand `
            -Executable $bootstrap.Path `
            -Arguments @('-m', 'venv', $temporary)
        $temporaryPython = Join-Path $temporary 'Scripts\python.exe'
        $null = Invoke-MesNativeCommand `
            -Executable $temporaryPython `
            -Arguments @(
                '-m', 'pip', 'install',
                '--no-index',
                '--find-links', $metadata.WheelhousePath,
                '--requirement', $metadata.RequirementsPath,
                '--disable-pip-version-check'
            )
        $null = Test-MesPythonRuntime -PythonPath $temporaryPython -Metadata $metadata
        Move-Item -LiteralPath $temporary -Destination $runtime
    }
    finally {
        if (Test-Path -LiteralPath $temporary -PathType Container) {
            $temporaryFull = [IO.Path]::GetFullPath($temporary).TrimEnd('\') + '\'
            $backendFull = [IO.Path]::GetFullPath($metadata.BackendPath).TrimEnd('\') + '\'
            if (-not $temporaryFull.StartsWith($backendFull, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Refusing to remove a runtime staging path outside the backend root.'
            }
            Remove-Item -LiteralPath $temporary -Recurse -Force
        }
    }
    return [pscustomobject]@{
        Status = 'PREPARED'
        PythonPath = $runtimePython
        PythonVersion = $metadata.PythonVersion
        WheelCount = $metadata.WheelCount
    }
}
