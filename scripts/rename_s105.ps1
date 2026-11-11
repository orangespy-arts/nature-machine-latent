param([Parameter(Mandatory = $true)][string]$Root, [switch]$Apply)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $Root).Path
$repo = Split-Path $PSScriptRoot -Parent
$manifest = Join-Path $repo 'datasets/manifests/s105-v001.csv'
$queuePath = Join-Path $repo 'datasets/manifests/s105-listening-queue-v001.csv'
$mapPath = Join-Path $repo 'datasets/manifests/s105-v001-renames.json'
if (Test-Path -LiteralPath $mapPath) { throw 'Rename map already exists; do not rerun.' }
$rows = @(Import-Csv -LiteralPath $manifest)
$queue = @(Import-Csv -LiteralPath $queuePath)
$counts = @{}
$used = @{}
$plan = @()
foreach ($row in $rows) {
    $stem = [IO.Path]::GetFileNameWithoutExtension($row.relative_path).ToLowerInvariant()
    $stem = $stem -replace '^meck\s+', '' -replace '\bb3\b', '' -replace '\d+', '' -replace '\bmachien\b', 'machine'
    $stem = ($stem -replace '[^a-z]+', '_').Trim('_')
    if (-not $stem) { throw 'Empty filename' }
    if (-not $counts.ContainsKey($stem)) { $counts[$stem] = 0 }
    $counts[$stem]++
    $plan += [pscustomobject]@{asset_id=$row.asset_id; original_relative_path=$row.relative_path; relative_path=''; sha256=$row.sha256; stem=$stem}
}
foreach ($item in $plan) {
    $stem = $item.stem
    if (-not $used.ContainsKey($stem)) { $used[$stem] = 0 }
    $suffix = ''
    if ($counts[$stem] -gt 1) {
        if ($counts[$stem] -gt 26) { throw 'Too many variants' }
        $suffix = '_' + [char](97 + $used[$stem])
    }
    $used[$stem]++
    $name = $stem + $suffix + '.wav'
    $parent = [IO.Path]::GetDirectoryName($item.original_relative_path).Replace('\','/')
    $item.relative_path = $parent + '/' + $name
    $old = [IO.Path]::GetFullPath((Join-Path $root $item.original_relative_path))
    $new = [IO.Path]::GetFullPath((Join-Path $root $item.relative_path))
    foreach ($path in @($old, $new)) {
        if (-not $path.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Path outside source root' }
    }
    if (-not (Test-Path -LiteralPath $old -PathType Leaf)) { throw "Missing: $old" }
    if ($old -ne $new -and (Test-Path -LiteralPath $new)) { throw "Collision: $new" }
}
if (($plan.relative_path | Sort-Object -Unique).Count -ne $rows.Count) { throw 'Duplicate target paths' }
$lookup = @{}
foreach ($item in $plan) { $lookup[$item.asset_id] = $item }
foreach ($row in $queue) {
    if (-not $lookup.ContainsKey($row.asset_id) -or $lookup[$row.asset_id].original_relative_path -ne $row.relative_path) { throw 'Queue mismatch' }
}
if (-not $Apply) {
    $plan | Select-Object -First 12 asset_id,original_relative_path,relative_path | Format-List
    Write-Output "Validated rename plan: $($plan.Count) files. Use -Apply to execute."
    exit
}
# Persist the recovery mapping before changing filenames.
$plan | Select-Object asset_id,original_relative_path,relative_path,sha256 | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $mapPath -Encoding utf8
foreach ($item in $plan) {
    Rename-Item -LiteralPath (Join-Path $root $item.original_relative_path) -NewName ([IO.Path]::GetFileName($item.relative_path))
}
foreach ($row in $rows) { $row.relative_path = $lookup[$row.asset_id].relative_path }
foreach ($row in $queue) { $row.relative_path = $lookup[$row.asset_id].relative_path }
$rows | Export-Csv -LiteralPath $manifest -NoTypeInformation -Encoding utf8BOM
$queue | Export-Csv -LiteralPath $queuePath -NoTypeInformation -Encoding utf8BOM
foreach ($item in $plan) {
    if ((Get-FileHash -LiteralPath (Join-Path $root $item.relative_path) -Algorithm SHA256).Hash -ne $item.sha256) { throw "Hash mismatch: $($item.asset_id)" }
}
Write-Output "Renamed and SHA-256 verified $($plan.Count) files; manifest and listening queue updated."
