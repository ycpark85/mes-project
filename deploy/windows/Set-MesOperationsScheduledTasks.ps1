[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$ConfigFile,
    [Parameter(Mandatory = $true)][ValidateSet('Register', 'Unregister')][string]$Mode
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'MesDeployment.Common.ps1')

if (-not (Test-MesAdministrator)) {
    throw 'Scheduled task changes require an elevated PowerShell session.'
}

$config = Import-MesDeploymentConfig -ConfigFile $ConfigFile
$taskPath = '\MES\'
$backupTaskName = 'MES Daily Verified Backup'
$monitorTaskName = 'MES Daily Operations Check'
$taskNames = @($backupTaskName, $monitorTaskName)

if ($Mode -eq 'Unregister') {
    foreach ($taskName in $taskNames) {
        $existing = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction SilentlyContinue
        if ($null -ne $existing -and $PSCmdlet.ShouldProcess("$taskPath$taskName", 'Unregister')) {
            Unregister-ScheduledTask -TaskPath $taskPath -TaskName $taskName -Confirm:$false
        }
    }
    return
}

if ([string]$config.BackupRoot -like '\\*' -and [string]$config.TaskPrincipal -eq 'NT AUTHORITY\SYSTEM') {
    throw 'SYSTEM must not be used for a network backup path. Configure a service account with share access.'
}

$configPath = (Resolve-Path -LiteralPath $ConfigFile).Path
$runner = Join-Path $PSScriptRoot 'Invoke-MesScheduledOperation.ps1'
$powershell = Join-Path $PSHOME 'powershell.exe'
$principal = New-ScheduledTaskPrincipal `
    -UserId $config.TaskPrincipal `
    -LogonType ServiceAccount `
    -RunLevel Highest

function New-MesTaskAction([string]$Operation) {
    $argument = @(
        '-NoProfile',
        '-NonInteractive',
        '-ExecutionPolicy', 'Bypass',
        '-File', (Quote-MesTaskArgument $runner),
        '-Operation', $Operation,
        '-ConfigFile', (Quote-MesTaskArgument $configPath)
    ) -join ' '
    return New-ScheduledTaskAction `
        -Execute $powershell `
        -Argument $argument `
        -WorkingDirectory $PSScriptRoot
}

$backupTrigger = New-ScheduledTaskTrigger -Daily -At ([DateTime]::ParseExact($config.BackupTime, 'HH:mm', $null))
$monitorTrigger = New-ScheduledTaskTrigger -Daily -At ([DateTime]::ParseExact($config.MonitorTime, 'HH:mm', $null))
$backupSettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4)
$monitorSettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

$definitions = @(
    @{
        Name = $backupTaskName
        Action = New-MesTaskAction -Operation 'Backup'
        Trigger = $backupTrigger
        Settings = $backupSettings
        Description = 'Creates the daily MES PostgreSQL and file-storage backup.'
    },
    @{
        Name = $monitorTaskName
        Action = New-MesTaskAction -Operation 'Monitor'
        Trigger = $monitorTrigger
        Settings = $monitorSettings
        Description = 'Runs read-only MES database, disk, backup, and restore-age checks.'
    }
)

foreach ($definition in $definitions) {
    if ($PSCmdlet.ShouldProcess("$taskPath$($definition.Name)", 'Register or update')) {
        Register-ScheduledTask `
            -TaskPath $taskPath `
            -TaskName $definition.Name `
            -Action $definition.Action `
            -Trigger $definition.Trigger `
            -Settings $definition.Settings `
            -Principal $principal `
            -Description $definition.Description `
            -Force | Out-Null
    }
}
