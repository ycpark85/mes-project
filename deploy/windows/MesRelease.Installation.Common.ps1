Set-StrictMode -Version Latest

$script:MesReleaseManifestName = 'release-manifest.json'
$script:MesReleaseMaxFiles = 10000
$script:MesReleaseMaxBytes = 1GB

function Get-MesStreamSha256 {
    param([Parameter(Mandatory = $true)][System.IO.Stream]$Stream)

    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha.ComputeHash($Stream)
        return -join ($hash | ForEach-Object { $_.ToString('x2') })
    }
    finally {
        $sha.Dispose()
    }
}

function Assert-MesReleaseRelativePath {
    param([Parameter(Mandatory = $true)][string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path) -or $Path.Contains('\') -or $Path.StartsWith('/')) {
        throw "Unsafe release package path: $Path"
    }
    $parts = $Path.Split('/')
    if ($parts | Where-Object { $_ -in @('', '.', '..') -or $_.Contains(':') }) {
        throw "Unsafe release package path: $Path"
    }
}

function Get-MesReleaseManifestMap {
    param([Parameter(Mandatory = $true)]$Manifest)

    if ($Manifest.format_version -ne 1 -or $Manifest.release_type -ne 'mes-v2-windows') {
        throw 'Unsupported MES release manifest format.'
    }
    $commit = [string]$Manifest.git.commit
    if ($commit -notmatch '^[0-9a-f]{40}$') {
        throw 'Release manifest contains an invalid Git commit.'
    }
    if ($Manifest.validation.overall_status -ne 'OK') {
        throw 'Release manifest does not contain successful validation evidence.'
    }
    $map = @{}
    foreach ($entry in @($Manifest.files)) {
        $relative = [string]$entry.path
        Assert-MesReleaseRelativePath -Path $relative
        if ($relative -eq $script:MesReleaseManifestName -or $map.ContainsKey($relative)) {
            throw "Release manifest contains a duplicate file: $relative"
        }
        $size = 0L
        if (-not [long]::TryParse([string]$entry.size, [ref]$size) -or $size -lt 0) {
            throw "Release manifest contains an invalid file size: $relative"
        }
        $hash = [string]$entry.sha256
        if ($hash -notmatch '^[0-9a-f]{64}$') {
            throw "Release manifest contains an invalid file hash: $relative"
        }
        $map[$relative] = [pscustomobject]@{
            Size = $size
            Sha256 = $hash.ToLowerInvariant()
        }
    }
    return $map
}

function Get-MesReleasePackageMetadata {
    param(
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [Parameter(Mandatory = $true)][string]$ManifestPath,
        [Parameter(Mandatory = $true)][string]$ChecksumPath
    )

    $package = (Resolve-Path -LiteralPath $PackagePath -ErrorAction Stop).Path
    $manifestFile = (Resolve-Path -LiteralPath $ManifestPath -ErrorAction Stop).Path
    $checksumFile = (Resolve-Path -LiteralPath $ChecksumPath -ErrorAction Stop).Path
    foreach ($path in @($package, $manifestFile, $checksumFile)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Release input is not a file: $path"
        }
    }

    $checksumLines = @(Get-Content -LiteralPath $checksumFile | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($checksumLines.Count -ne 1 -or $checksumLines[0] -notmatch '^([0-9a-fA-F]{64})\s{2}(.+)$') {
        throw 'Release checksum sidecar is invalid.'
    }
    $expectedPackageHash = $matches[1].ToLowerInvariant()
    if ($matches[2] -ne [IO.Path]::GetFileName($package)) {
        throw 'Release checksum sidecar names a different package.'
    }
    $actualPackageHash = (Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualPackageHash -ne $expectedPackageHash) {
        throw 'Release package SHA-256 does not match its checksum sidecar.'
    }

    try {
        $manifest = Get-Content -Raw -LiteralPath $manifestFile -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        throw 'Release manifest sidecar is invalid JSON.'
    }
    $manifestMap = Get-MesReleaseManifestMap -Manifest $manifest
    $sidecarManifestHash = (Get-FileHash -LiteralPath $manifestFile -Algorithm SHA256).Hash.ToLowerInvariant()

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($package)
    try {
        $entries = @($archive.Entries)
        if ($entries.Count -gt $script:MesReleaseMaxFiles) {
            throw 'Release package contains too many entries.'
        }
        $entryMap = @{}
        $totalBytes = 0L
        foreach ($entry in $entries) {
            $relative = [string]$entry.FullName
            Assert-MesReleaseRelativePath -Path $relative
            if ($entryMap.ContainsKey($relative)) {
                throw "Release package contains a duplicate entry: $relative"
            }
            $totalBytes += [long]$entry.Length
            if ($totalBytes -gt $script:MesReleaseMaxBytes) {
                throw 'Release package expands beyond the permitted size.'
            }
            $entryMap[$relative] = $entry
        }
        if (-not $entryMap.ContainsKey($script:MesReleaseManifestName)) {
            throw 'Release package does not contain its manifest.'
        }
        $embeddedManifestStream = $entryMap[$script:MesReleaseManifestName].Open()
        try {
            $embeddedManifestHash = Get-MesStreamSha256 -Stream $embeddedManifestStream
        }
        finally {
            $embeddedManifestStream.Dispose()
        }
        if ($embeddedManifestHash -ne $sidecarManifestHash) {
            throw 'Embedded release manifest differs from the sidecar manifest.'
        }

        $actualPaths = @($entryMap.Keys | Where-Object { $_ -ne $script:MesReleaseManifestName })
        if ($actualPaths.Count -ne $manifestMap.Count) {
            throw 'Release package file count differs from its manifest.'
        }
        foreach ($relative in $actualPaths) {
            if (-not $manifestMap.ContainsKey($relative)) {
                throw "Release package contains an unlisted file: $relative"
            }
            $entry = $entryMap[$relative]
            $expected = $manifestMap[$relative]
            if ([long]$entry.Length -ne $expected.Size) {
                throw "Release package file size differs from its manifest: $relative"
            }
            $stream = $entry.Open()
            try {
                $actualHash = Get-MesStreamSha256 -Stream $stream
            }
            finally {
                $stream.Dispose()
            }
            if ($actualHash -ne $expected.Sha256) {
                throw "Release package file hash differs from its manifest: $relative"
            }
        }
    }
    finally {
        $archive.Dispose()
    }

    foreach ($required in @(
        'backend/app/main.py',
        'backend/migrations/env.py',
        'deploy/windows/Test-MesDeployment.ps1',
        'clients/internal/Mes.Wpf.exe',
        'clients/vendor/Mes.Vendor.Wpf.exe'
    )) {
        if (-not $manifestMap.ContainsKey($required)) {
            throw "Release package is missing a required runtime file: $required"
        }
    }

    return [pscustomobject]@{
        PackagePath = $package
        ManifestPath = $manifestFile
        ChecksumPath = $checksumFile
        PackageSha256 = $actualPackageHash
        Commit = [string]$manifest.git.commit
        AlembicHead = [string]$manifest.database.alembic_head
        FileCount = $manifestMap.Count + 1
        Manifest = $manifest
        ManifestMap = $manifestMap
    }
}

function Test-MesInstalledRelease {
    param(
        [Parameter(Mandatory = $true)][string]$ReleasePath,
        [Parameter(Mandatory = $true)]$Metadata
    )

    $root = (Resolve-Path -LiteralPath $ReleasePath -ErrorAction Stop).Path
    $files = @{}
    foreach ($item in Get-ChildItem -LiteralPath $root -Recurse -Force) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Installed release contains a reparse point: $($item.FullName)"
        }
        if (-not $item.PSIsContainer) {
            $relative = $item.FullName.Substring($root.Length).TrimStart('\').Replace('\', '/')
            Assert-MesReleaseRelativePath -Path $relative
            $files[$relative] = $item
        }
    }
    if (-not $files.ContainsKey($script:MesReleaseManifestName)) {
        throw 'Installed release manifest is missing.'
    }
    $installedManifestHash = (Get-FileHash -LiteralPath $files[$script:MesReleaseManifestName].FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $sidecarManifestHash = (Get-FileHash -LiteralPath $Metadata.ManifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($installedManifestHash -ne $sidecarManifestHash) {
        throw 'Installed release manifest differs from the approved manifest.'
    }
    $actualPaths = @($files.Keys | Where-Object { $_ -ne $script:MesReleaseManifestName })
    if ($actualPaths.Count -ne $Metadata.ManifestMap.Count) {
        throw 'Installed release file count differs from the approved manifest.'
    }
    foreach ($relative in $actualPaths) {
        if (-not $Metadata.ManifestMap.ContainsKey($relative)) {
            throw "Installed release contains an unlisted file: $relative"
        }
        $expected = $Metadata.ManifestMap[$relative]
        $item = $files[$relative]
        if ([long]$item.Length -ne $expected.Size) {
            throw "Installed release file size differs: $relative"
        }
        $actualHash = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -ne $expected.Sha256) {
            throw "Installed release file hash differs: $relative"
        }
    }
    return $true
}

function Expand-MesReleasePackage {
    param(
        [Parameter(Mandatory = $true)]$Metadata,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $destinationFull = [IO.Path]::GetFullPath($Destination).TrimEnd('\')
    if (Test-Path -LiteralPath $destinationFull) {
        throw "Release extraction destination already exists: $destinationFull"
    }
    New-Item -ItemType Directory -Path $destinationFull | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($Metadata.PackagePath)
    try {
        foreach ($entry in $archive.Entries) {
            $relative = [string]$entry.FullName
            Assert-MesReleaseRelativePath -Path $relative
            $target = [IO.Path]::GetFullPath((Join-Path $destinationFull $relative.Replace('/', '\')))
            if (-not $target.StartsWith($destinationFull + '\', [StringComparison]::OrdinalIgnoreCase)) {
                throw "Release entry escapes the extraction root: $relative"
            }
            $parent = [IO.Path]::GetDirectoryName($target)
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
            $source = $entry.Open()
            try {
                $output = New-Object IO.FileStream(
                    $target,
                    [IO.FileMode]::CreateNew,
                    [IO.FileAccess]::Write,
                    [IO.FileShare]::None
                )
                try {
                    $source.CopyTo($output)
                }
                finally {
                    $output.Dispose()
                }
            }
            finally {
                $source.Dispose()
            }
        }
    }
    finally {
        $archive.Dispose()
    }
}

function Install-MesReleasePackage {
    param(
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [Parameter(Mandatory = $true)][string]$ManifestPath,
        [Parameter(Mandatory = $true)][string]$ChecksumPath,
        [Parameter(Mandatory = $true)][string]$ReleaseRoot
    )

    $metadata = Get-MesReleasePackageMetadata `
        -PackagePath $PackagePath `
        -ManifestPath $ManifestPath `
        -ChecksumPath $ChecksumPath
    $root = [IO.Path]::GetFullPath($ReleaseRoot)
    $releasesRoot = Join-Path $root 'releases'
    New-Item -ItemType Directory -Path $releasesRoot -Force | Out-Null
    $target = Join-Path $releasesRoot $metadata.Commit
    if (Test-Path -LiteralPath $target) {
        $null = Test-MesInstalledRelease -ReleasePath $target -Metadata $metadata
        return [pscustomobject]@{
            Status = 'ALREADY_STAGED'
            Commit = $metadata.Commit
            ReleasePath = $target
            PackageSha256 = $metadata.PackageSha256
            AlembicHead = $metadata.AlembicHead
        }
    }

    $temporary = Join-Path $releasesRoot ('.installing-{0}-{1}' -f $metadata.Commit, $PID)
    if (Test-Path -LiteralPath $temporary) {
        throw "Unexpected release staging path already exists: $temporary"
    }
    try {
        Expand-MesReleasePackage -Metadata $metadata -Destination $temporary
        $null = Test-MesInstalledRelease -ReleasePath $temporary -Metadata $metadata
        Move-Item -LiteralPath $temporary -Destination $target
    }
    finally {
        if (Test-Path -LiteralPath $temporary -PathType Container) {
            $temporaryFull = [IO.Path]::GetFullPath($temporary).TrimEnd('\') + '\'
            $releasesFull = [IO.Path]::GetFullPath($releasesRoot).TrimEnd('\') + '\'
            if (-not $temporaryFull.StartsWith($releasesFull, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Refusing to remove a staging path outside the releases root.'
            }
            Remove-Item -LiteralPath $temporary -Recurse -Force
        }
    }
    return [pscustomobject]@{
        Status = 'STAGED'
        Commit = $metadata.Commit
        ReleasePath = $target
        PackageSha256 = $metadata.PackageSha256
        AlembicHead = $metadata.AlembicHead
    }
}

function Get-MesReleaseJunctionTarget {
    param([Parameter(Mandatory = $true)][string]$CurrentPath)

    $item = Get-Item -LiteralPath $CurrentPath -Force -ErrorAction Stop
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) {
        throw "Active release path is not a junction: $CurrentPath"
    }
    $targetValue = [string]@($item.Target)[0]
    if ([string]::IsNullOrWhiteSpace($targetValue)) {
        throw "Active release junction target is unreadable: $CurrentPath"
    }
    if (-not [IO.Path]::IsPathRooted($targetValue)) {
        $targetValue = Join-Path $item.Parent.FullName $targetValue
    }
    return [IO.Path]::GetFullPath($targetValue).TrimEnd('\')
}

function Remove-MesReleaseJunction {
    param([Parameter(Mandatory = $true)][string]$Path)

    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) {
        throw "Refusing to remove a non-junction path: $Path"
    }
    [IO.Directory]::Delete($item.FullName)
}

function Set-MesReleaseJunction {
    param(
        [Parameter(Mandatory = $true)][string]$ReleaseRoot,
        [Parameter(Mandatory = $true)][string]$TargetReleasePath,
        [switch]$InjectFailureAfterCurrentMove
    )

    $root = [IO.Path]::GetFullPath($ReleaseRoot).TrimEnd('\')
    $releasesRoot = [IO.Path]::GetFullPath((Join-Path $root 'releases')).TrimEnd('\') + '\'
    $target = (Resolve-Path -LiteralPath $TargetReleasePath -ErrorAction Stop).Path.TrimEnd('\')
    if (-not ($target + '\').StartsWith($releasesRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Active release target must be under the releases root.'
    }
    $current = Join-Path $root 'current'
    if (Test-Path -LiteralPath $current) {
        $existingTarget = Get-MesReleaseJunctionTarget -CurrentPath $current
        if ($existingTarget -eq $target) {
            return $target
        }
    }
    $token = [Guid]::NewGuid().ToString('N')
    $candidate = Join-Path $root ".current-candidate-$token"
    $previous = Join-Path $root ".current-previous-$token"
    $movedCurrent = $false
    New-Item -ItemType Junction -Path $candidate -Target $target | Out-Null
    try {
        if (Test-Path -LiteralPath $current) {
            Move-Item -LiteralPath $current -Destination $previous
            $movedCurrent = $true
        }
        if ($InjectFailureAfterCurrentMove) {
            throw 'Injected release-switch failure for rollback rehearsal.'
        }
        Move-Item -LiteralPath $candidate -Destination $current
    }
    catch {
        if ($movedCurrent -and -not (Test-Path -LiteralPath $current) -and (Test-Path -LiteralPath $previous)) {
            Move-Item -LiteralPath $previous -Destination $current
        }
        if (Test-Path -LiteralPath $candidate) {
            Remove-MesReleaseJunction -Path $candidate
        }
        throw
    }
    if (Test-Path -LiteralPath $previous) {
        Remove-MesReleaseJunction -Path $previous
    }
    return Get-MesReleaseJunctionTarget -CurrentPath $current
}
