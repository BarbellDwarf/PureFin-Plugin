<#
.SYNOPSIS
    End-to-end test for PureFin AI services on AMD GPU (ROCm/HIP).
    Cycles through all three violence model profiles: speed, balanced, quality.

.DESCRIPTION
    1. Verifies AMD GPU prerequisites
    2. Builds containers with the AMD ROCm overlay
    3. Starts all services and waits for health
    4. For each profile (speed, balanced, quality):
       - Updates VIOLENCE_MODEL_PROFILE in .env
       - Restarts just the violence-detector container
       - Waits for it to become ready
       - Calls /health and /ready on all three services
       - Calls /runtime on scene-analyzer to verify active profile
       - Optionally submits a test video for analysis
    5. Prints a summary

.NOTES
    Must be run from the ai-services directory, or pass -AiServicesPath explicitly.
    Requires Docker Desktop with WSL2 backend and AMD ROCm driver support.
#>

[CmdletBinding()]
param(
    [string]$AiServicesPath = (Join-Path $PSScriptRoot ".." "ai-services"),
    [string]$TestVideoPath  = "",   # Optional: full path to a short test video file
    [switch]$SkipBuild,             # Skip docker compose build (use cached images)
    [switch]$SkipPrereqCheck        # Skip AMD GPU prereq verification
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
function Write-Step([string]$msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-OK([string]$msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-WARN([string]$msg) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-FAIL([string]$msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red }

function Invoke-Get {
    param([string]$Url, [int]$TimeoutSec = 15)
    try {
        $resp = Invoke-RestMethod -Uri $Url -Method GET -TimeoutSec $TimeoutSec -ErrorAction Stop
        return $resp
    } catch {
        throw "GET $Url failed: $_"
    }
}

function Wait-ServiceReady {
    param([string]$Name, [string]$HealthUrl, [int]$MaxWaitSec = 120)
    Write-Host "  Waiting for $Name ($HealthUrl)..." -NoNewline
    $deadline = (Get-Date).AddSeconds($MaxWaitSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-RestMethod -Uri $HealthUrl -Method GET -TimeoutSec 5 -ErrorAction Stop
            Write-Host " ready" -ForegroundColor Green
            return $r
        } catch {
            Write-Host "." -NoNewline
            Start-Sleep -Seconds 3
        }
    }
    Write-Host " TIMEOUT" -ForegroundColor Red
    throw "$Name did not become ready within ${MaxWaitSec}s"
}

function Set-EnvProfile {
    param([string]$EnvFile, [string]$Profile)
    $content = Get-Content $EnvFile -Raw
    if ($content -match "(?m)^VIOLENCE_MODEL_PROFILE=.*$") {
        $content = $content -replace "(?m)^VIOLENCE_MODEL_PROFILE=.*$", "VIOLENCE_MODEL_PROFILE=$Profile"
    } else {
        $content += "`nVIOLENCE_MODEL_PROFILE=$Profile`n"
    }
    Set-Content $EnvFile $content -NoNewline
}

# ──────────────────────────────────────────────────────────────────────────────
# Resolve paths
# ──────────────────────────────────────────────────────────────────────────────
$AiServicesPath = Resolve-Path $AiServicesPath
$EnvFile = Join-Path $AiServicesPath ".env"
$ComposeBase = Join-Path $AiServicesPath "docker-compose.yml"
$ComposeAmd  = Join-Path $AiServicesPath "docker-compose.amd.yml"

Write-Host "PureFin AI Services E2E Test — AMD GPU" -ForegroundColor Magenta
Write-Host "Working directory: $AiServicesPath"

# ──────────────────────────────────────────────────────────────────────────────
# Step 1: Prerequisites
# ──────────────────────────────────────────────────────────────────────────────
Write-Step "Checking prerequisites"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-FAIL "docker not found in PATH. Install Docker Desktop."
    exit 1
}
Write-OK "docker found"

try {
    docker info --format "{{.ServerVersion}}" | Out-Null
    Write-OK "Docker daemon is running"
} catch {
    Write-FAIL "Docker daemon is not running. Start Docker Desktop."
    exit 1
}

if (-not $SkipPrereqCheck) {
    # Check if /dev/kfd is accessible inside WSL2 (AMD GPU device)
    $kfdCheck = wsl -e sh -c "[ -e /dev/kfd ] && echo yes || echo no" 2>$null
    if ($kfdCheck -match "yes") {
        Write-OK "/dev/kfd accessible in WSL2 — AMD ROCm device present"
    } else {
        Write-WARN "/dev/kfd not found in WSL2. AMD GPU acceleration may not work."
        Write-WARN "Ensure AMD Adrenalin driver 23.40+ is installed and WSL2 integration is enabled."
        Write-WARN "Continuing anyway (containers will fall back to CPU)..."
    }
}

if (-not (Test-Path $EnvFile)) {
    Write-WARN ".env file not found — copying from .env.example"
    Copy-Item (Join-Path $AiServicesPath ".env.example") $EnvFile
}
Write-OK ".env file present"

# ──────────────────────────────────────────────────────────────────────────────
# Step 2: Build containers
# ──────────────────────────────────────────────────────────────────────────────
Push-Location $AiServicesPath

if (-not $SkipBuild) {
    Write-Step "Building containers with AMD ROCm overlay"
    Write-Host "  This installs ROCm 6.2 PyTorch inside violence-detector — may take several minutes on first build."
    & docker compose -f $ComposeBase -f $ComposeAmd build
    if ($LASTEXITCODE -ne 0) {
        Write-FAIL "docker compose build failed"
        Pop-Location; exit 1
    }
    Write-OK "Build complete"
} else {
    Write-WARN "Skipping build (-SkipBuild)"
}

# ──────────────────────────────────────────────────────────────────────────────
# Step 3: Start services with balanced profile (default)
# ──────────────────────────────────────────────────────────────────────────────
Write-Step "Starting services"
Set-EnvProfile $EnvFile "balanced"
& docker compose -f $ComposeBase -f $ComposeAmd up -d
if ($LASTEXITCODE -ne 0) {
    Write-FAIL "docker compose up failed"
    Pop-Location; exit 1
}

# Health endpoints
$NsfwHealth      = "http://localhost:3001/health"
$AnalyzerHealth  = "http://localhost:3002/health"
$ViolenceHealth  = "http://localhost:3003/health"
$AnalyzerRuntime = "http://localhost:3002/runtime"
$ViolenceReady   = "http://localhost:3003/ready"

$null = Wait-ServiceReady "nsfw-detector"     $NsfwHealth     120
$null = Wait-ServiceReady "violence-detector" $ViolenceHealth 180
$null = Wait-ServiceReady "scene-analyzer"    $AnalyzerHealth 180

# ──────────────────────────────────────────────────────────────────────────────
# Step 4: Cycle through each profile
# ──────────────────────────────────────────────────────────────────────────────
$profiles = @("speed", "balanced", "quality")
$results  = @{}

foreach ($profile in $profiles) {
    Write-Step "Testing profile: $profile"

    # Update .env and restart violence-detector only
    Set-EnvProfile $EnvFile $profile
    Write-Host "  Restarting violence-detector with profile=$profile..."
    & docker compose -f $ComposeBase -f $ComposeAmd stop violence-detector | Out-Null
    & docker compose -f $ComposeBase -f $ComposeAmd up -d violence-detector
    Start-Sleep -Seconds 5  # brief wait before polling

    # Wait for violence-detector to come back
    $null = Wait-ServiceReady "violence-detector ($profile)" $ViolenceHealth 180

    # Check /ready endpoint on violence-detector
    try {
        $rdyResp = Invoke-Get $ViolenceReady 15
        $activeProfile = if ($rdyResp.model_profile) { $rdyResp.model_profile } else { "(unknown)" }
        $deviceUsed    = if ($rdyResp.device)        { $rdyResp.device }        else { "(unknown)" }
        Write-OK "violence-detector ready — profile=$activeProfile device=$deviceUsed"
        if ($activeProfile -ne $profile) {
            Write-WARN "Expected profile '$profile' but service reports '$activeProfile'"
        }
    } catch {
        Write-WARN "Could not read /ready response: $_"
        $activeProfile = "error"; $deviceUsed = "error"
    }

    # Check /runtime on scene-analyzer (picks up downstream violence-detector info)
    try {
        $runtime = Invoke-Get $AnalyzerRuntime 15
        $vModel = $null
        if ($runtime.downstream_services) {
            $vSvc = $runtime.downstream_services | Where-Object { $_.name -eq "violence-detector" }
            if ($vSvc) { $vModel = $vSvc.model_id }
        }
        if (-not $vModel -and $runtime.model_versions) {
            $vModel = $runtime.model_versions.violence
        }
        Write-OK "scene-analyzer /runtime: violence model=$vModel"
    } catch {
        Write-WARN "/runtime call failed: $_"
        $vModel = "error"
    }

    # Optional: submit a test video
    if ($TestVideoPath -and (Test-Path $TestVideoPath)) {
        Write-Host "  Submitting test video: $TestVideoPath"
        $body = @{ video_path = $TestVideoPath } | ConvertTo-Json
        try {
            $analyzeResp = Invoke-RestMethod -Uri "http://localhost:3002/analyze" `
                -Method POST -Body $body -ContentType "application/json" -TimeoutSec 300
            $segCount = if ($analyzeResp.segments) { $analyzeResp.segments.Count } else { 0 }
            Write-OK "Analysis returned $segCount segments (model_versions: $($analyzeResp.model_versions | ConvertTo-Json -Compress))"
        } catch {
            Write-WARN "Analysis failed: $_"
        }
    } elseif ($TestVideoPath) {
        Write-WARN "Test video not found at: $TestVideoPath — skipping analysis"
    } else {
        Write-WARN "No -TestVideoPath provided — skipping live analysis test"
    }

    $results[$profile] = @{
        active_profile = $activeProfile
        device         = $deviceUsed
        violence_model = $vModel
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# Step 5: Summary
# ──────────────────────────────────────────────────────────────────────────────
Write-Step "Summary"
foreach ($p in $profiles) {
    $r = $results[$p]
    $ok = if ($r.active_profile -eq $p) { "[OK]" } else { "[WARN]" }
    $color = if ($r.active_profile -eq $p) { "Green" } else { "Yellow" }
    Write-Host ("  {0,-8} profile={1,-10} device={2,-6} model={3}" -f $ok, $r.active_profile, $r.device, $r.violence_model) -ForegroundColor $color
}

Write-Host "`nE2E test complete." -ForegroundColor Magenta
Write-Host "To reset to balanced profile:  Set-Content (edit .env) VIOLENCE_MODEL_PROFILE=balanced"
Write-Host "To stop services:              docker compose -f docker-compose.yml -f docker-compose.amd.yml down"

Pop-Location
