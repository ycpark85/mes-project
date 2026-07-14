Set-StrictMode -Version Latest

function Invoke-MesReleaseActivationSwitch {
    param(
        [Parameter(Mandatory = $true)][string]$ReleaseRoot,
        [Parameter(Mandatory = $true)][string]$CandidateReleasePath,
        [Parameter(Mandatory = $true)][scriptblock]$StopApi,
        [Parameter(Mandatory = $true)][scriptblock]$StartCandidateApi,
        [Parameter(Mandatory = $true)][scriptblock]$TestCandidateApi,
        [Parameter(Mandatory = $true)][scriptblock]$StartPreviousApi,
        [Parameter(Mandatory = $true)][scriptblock]$TestPreviousApi
    )

    $root = [IO.Path]::GetFullPath($ReleaseRoot).TrimEnd('\')
    $current = Join-Path $root 'current'
    $previous = Get-MesReleaseJunctionTarget -CurrentPath $current
    $candidate = (Resolve-Path -LiteralPath $CandidateReleasePath -ErrorAction Stop).Path.TrimEnd('\')
    if ($candidate -eq $previous) {
        throw 'Candidate release is already active.'
    }

    $null = & $StopApi
    $activationError = $null
    try {
        $selected = Set-MesReleaseJunction -ReleaseRoot $root -TargetReleasePath $candidate
        if ($selected -ne $candidate) {
            throw 'Candidate release pointer verification failed.'
        }
        $null = & $StartCandidateApi
        $null = & $TestCandidateApi
        return [pscustomobject]@{
            Status = 'ACTIVATED'
            PreviousReleasePath = $previous
            ActiveReleasePath = $candidate
            RollbackPerformed = $false
        }
    }
    catch {
        $activationError = $_
    }

    $rollbackFailures = New-Object System.Collections.Generic.List[string]
    try { $null = & $StopApi } catch { $rollbackFailures.Add('stop_candidate') }
    try {
        $restored = Set-MesReleaseJunction -ReleaseRoot $root -TargetReleasePath $previous
        if ($restored -ne $previous) {
            throw 'Previous release pointer verification failed.'
        }
    }
    catch { $rollbackFailures.Add('restore_pointer') }
    if ($rollbackFailures.Count -eq 0) {
        try { $null = & $StartPreviousApi } catch { $rollbackFailures.Add('start_previous') }
    }
    if ($rollbackFailures.Count -eq 0) {
        try { $null = & $TestPreviousApi } catch { $rollbackFailures.Add('test_previous') }
    }
    if ($rollbackFailures.Count -gt 0) {
        throw [InvalidOperationException]::new(
            'Candidate activation failed and automatic rollback was incomplete: ' +
            ($rollbackFailures -join ', '),
            $activationError.Exception
        )
    }
    throw [InvalidOperationException]::new(
        'Candidate activation failed; the previous release was restored.',
        $activationError.Exception
    )
}
