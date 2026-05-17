#Requires -Version 5.1
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

$ErrorActionPreference = "Stop"

$Repo = "adeptofvoltron/nimble"
$Target = "windows-x64"
$BinaryName = "nimble.exe"

# ── Resolve install directory ─────────────────────────────────────────────────
if ($env:NIMBLE_INSTALL_DIR) {
    $InstallDir = $env:NIMBLE_INSTALL_DIR
    $NeedAdmin = $false
} else {
    $InstallDir = Join-Path $env:ProgramFiles "Nimble"
    $NeedAdmin = $true
}

# ── Admin check ───────────────────────────────────────────────────────────────
if ($NeedAdmin) {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
    if (-not $isAdmin) {
        Write-Host "Nimble installs to '$InstallDir' and requires administrator privileges."
        Write-Host "Please re-run this script as Administrator, or set NIMBLE_INSTALL_DIR to a writable directory."
        exit 1
    }
}

# ── Fetch latest release tag ──────────────────────────────────────────────────
Write-Host "Fetching latest Nimble release..."
try {
    $Release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -UseBasicParsing
    $Tag = $Release.tag_name
} catch {
    Write-Host "Error: Could not reach GitHub Releases — if behind a proxy, set HTTPS_PROXY and retry."
    exit 1
}

if (-not $Tag) {
    Write-Host "Error: Could not determine latest release tag (GitHub API may be rate-limiting — try again in a minute)."
    exit 1
}

Write-Host "Installing Nimble $Tag ($Target)..."

# ── Build download URLs ───────────────────────────────────────────────────────
$BaseUrl = "https://github.com/$Repo/releases/download/$Tag"
$BinaryUrl = "$BaseUrl/nimble-$Target.exe"
$ChecksumUrl = "$BaseUrl/nimble-$Target.exe.sha256"

# ── Download to temp directory ────────────────────────────────────────────────
$TempBase = if ($env:TEMP) { $env:TEMP } elseif ($env:TMP) { $env:TMP } else { [System.IO.Path]::GetTempPath() }
$TmpDir = Join-Path $TempBase "nimble-install-$([System.IO.Path]::GetRandomFileName())"
New-Item -ItemType Directory -Path $TmpDir | Out-Null

$TmpBin = Join-Path $TmpDir $BinaryName
$TmpSum = Join-Path $TmpDir "nimble.sha256"

try {
    try {
        Invoke-WebRequest -Uri $BinaryUrl -OutFile $TmpBin -UseBasicParsing
    } catch {
        Write-Host "Error: Could not reach GitHub Releases — if behind a proxy, set HTTPS_PROXY and retry."
        exit 1
    }

    try {
        Invoke-WebRequest -Uri $ChecksumUrl -OutFile $TmpSum -UseBasicParsing
    } catch {
        Write-Host "Error: Could not reach GitHub Releases — if behind a proxy, set HTTPS_PROXY and retry."
        exit 1
    }

    # ── Verify SHA256 ─────────────────────────────────────────────────────────
    $Expected = (Get-Content $TmpSum -Raw).Trim().ToUpper() -split '\s+' | Select-Object -First 1
    $Actual = (Get-FileHash $TmpBin -Algorithm SHA256).Hash.ToUpper()

    if ($Actual -ne $Expected) {
        Write-Host "Error: Download may be corrupted — retry the install."
        exit 1
    }

    # ── Install ───────────────────────────────────────────────────────────────
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir | Out-Null
    }

    $Destination = Join-Path $InstallDir $BinaryName
    Move-Item -Force $TmpBin $Destination

    # ── Add to PATH if not already present ────────────────────────────────────
    $PathScope = if ($NeedAdmin) { "Machine" } else { "User" }
    $CurrentPath = [Environment]::GetEnvironmentVariable("Path", $PathScope)
    if (-not $CurrentPath) { $CurrentPath = "" }

    $PathEntries = $CurrentPath -split ';' | Where-Object { $_ -ne '' }
    if ($InstallDir -notin $PathEntries) {
        $NewPath = ($PathEntries + $InstallDir) -join ';'
        [Environment]::SetEnvironmentVariable("Path", $NewPath, $PathScope)
        Write-Host "Added '$InstallDir' to system PATH."
    }

} finally {
    Remove-Item -Recurse -Force $TmpDir -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Nimble installed! Open a new terminal to use it."
Write-Host "  Run: nimble --help"
