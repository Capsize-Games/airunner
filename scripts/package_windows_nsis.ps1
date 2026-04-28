param(
    [string]$BundleDir = "build/end-user-bundles/windows/desktop",
    [string]$OutputDir = "dist/windows-installer",
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path "$PSScriptRoot/..").Path
$bundleRoot = Resolve-Path (Join-Path $repoRoot $BundleDir)

if (!(Test-Path $bundleRoot)) {
    throw "Bundle output not found: $bundleRoot"
}

$makensis = Get-Command makensis -ErrorAction SilentlyContinue
if (-not $makensis) {
    throw "makensis not found in PATH. Install NSIS first."
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $versionLine = Select-String \
        -Path (Join-Path $repoRoot "setup.py") \
        -Pattern 'version="([0-9]+\.[0-9]+\.[0-9]+)"'
    if ($versionLine) {
        $Version = $versionLine.Matches[0].Groups[1].Value
    } else {
        $Version = "0.0.0"
    }
}

$outRoot = Join-Path $repoRoot $OutputDir
$stageDir = Join-Path $outRoot "staging"
$scriptPath = Join-Path $repoRoot "packaging/windows/airunner.nsi"

if (Test-Path $outRoot) {
    Remove-Item -Recurse -Force $outRoot
}

New-Item -ItemType Directory -Path $stageDir | Out-Null
Copy-Item -Recurse -Force "$bundleRoot/*" $stageDir

Push-Location $outRoot
try {
    & $makensis.Source "/DSTAGING_DIR=$stageDir" "/DAPP_VERSION=$Version" $scriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "makensis failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

$installer = Join-Path $outRoot ("airunner-" + $Version + "-windows-x64-setup.exe")
if (!(Test-Path $installer)) {
    throw "Installer not produced: $installer"
}

Write-Host "Created installer: $installer"