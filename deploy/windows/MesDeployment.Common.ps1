Set-StrictMode -Version Latest

function Import-MesDeploymentConfig {
    param([Parameter(Mandatory = $true)][string]$ConfigFile)

    $resolved = (Resolve-Path -LiteralPath $ConfigFile -ErrorAction Stop).Path
    $config = Import-PowerShellDataFile -LiteralPath $resolved
    $required = @(
        'BackendRoot',
        'PythonPath',
        'EnvFile',
        'MonitorEnvFile',
        'BackupRoot',
        'MonitorHistoryRoot',
        'RestoreRecordPath',
        'OperationsLogRoot',
        'PgBin',
        'ApiBaseUrl',
        'ApiServiceName',
        'PostgresServiceName',
        'TaskPrincipal',
        'BackupTime',
        'MonitorTime'
    )
    foreach ($key in $required) {
        if (-not $config.ContainsKey($key) -or [string]::IsNullOrWhiteSpace([string]$config[$key])) {
            throw "Deployment config is missing: $key"
        }
    }

    foreach ($key in $config.Keys) {
        if ([string]$key -match '(?i)password|secret|databaseurl|token') {
            throw "Secrets and database URLs are not allowed in the deployment config: $key"
        }
    }

    $pathKeys = @(
        'BackendRoot', 'PythonPath', 'EnvFile', 'MonitorEnvFile',
        'BackupRoot', 'MonitorHistoryRoot', 'RestoreRecordPath',
        'OperationsLogRoot', 'PgBin'
    )
    foreach ($key in $pathKeys) {
        if (-not [System.IO.Path]::IsPathRooted([string]$config[$key])) {
            throw "Deployment path must be absolute: $key"
        }
        if ([string]$config[$key] -match '"') {
            throw "Deployment paths cannot contain quote characters: $key"
        }
    }
    return $config
}

function Read-MesEnvFile {
    param([Parameter(Mandatory = $true)][string]$Path)

    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path -ErrorAction Stop) {
        if ($line -match '^\s*#' -or [string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        if ($line -match '^\s*([^=]+?)\s*=\s*(.*)\s*$') {
            $values[$matches[1].Trim().ToUpperInvariant()] = $matches[2].Trim()
        }
    }
    return $values
}

function Quote-MesTaskArgument {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value -match '"') {
        throw 'Task arguments cannot contain quote characters.'
    }
    return '"' + $Value + '"'
}

function Invoke-MesNativeCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [int[]]$AllowedExitCodes = @(0)
    )

    $commandOutput = & $Executable @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    foreach ($line in $commandOutput) {
        Write-Host $line
    }
    if ($AllowedExitCodes -notcontains $exitCode) {
        throw "Command failed with exit code ${exitCode}: $([System.IO.Path]::GetFileName($Executable))"
    }
    return [int]$exitCode
}

function Test-MesAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-MesPathOverlap {
    param(
        [Parameter(Mandatory = $true)][string]$First,
        [Parameter(Mandatory = $true)][string]$Second
    )

    $firstFull = [System.IO.Path]::GetFullPath($First).TrimEnd('\') + '\'
    $secondFull = [System.IO.Path]::GetFullPath($Second).TrimEnd('\') + '\'
    return $firstFull.StartsWith($secondFull, [StringComparison]::OrdinalIgnoreCase) -or
        $secondFull.StartsWith($firstFull, [StringComparison]::OrdinalIgnoreCase)
}

function Get-MesBroadAclEntries {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][ValidateSet('Read', 'Write')][string]$AccessKind
    )

    $broadSids = @('S-1-1-0', 'S-1-5-11', 'S-1-5-32-545')
    $writeMask = [Security.AccessControl.FileSystemRights]::WriteData -bor
        [Security.AccessControl.FileSystemRights]::AppendData -bor
        [Security.AccessControl.FileSystemRights]::WriteAttributes -bor
        [Security.AccessControl.FileSystemRights]::WriteExtendedAttributes -bor
        [Security.AccessControl.FileSystemRights]::Delete -bor
        [Security.AccessControl.FileSystemRights]::ChangePermissions -bor
        [Security.AccessControl.FileSystemRights]::TakeOwnership
    $readMask = [Security.AccessControl.FileSystemRights]::ReadData -bor
        [Security.AccessControl.FileSystemRights]::ReadAttributes -bor
        [Security.AccessControl.FileSystemRights]::ReadExtendedAttributes
    $mask = if ($AccessKind -eq 'Write') { $writeMask } else { $readMask }
    $unsafe = New-Object System.Collections.Generic.List[string]
    $acl = Get-Acl -LiteralPath $Path -ErrorAction Stop
    foreach ($entry in $acl.Access) {
        if ($entry.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow) {
            continue
        }
        try {
            $sid = $entry.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
        }
        catch {
            continue
        }
        if ($broadSids -contains $sid -and (($entry.FileSystemRights -band $mask) -ne 0)) {
            $unsafe.Add([string]$entry.IdentityReference)
        }
    }
    return $unsafe | Sort-Object -Unique
}
