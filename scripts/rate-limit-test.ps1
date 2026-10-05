# SPDX-FileCopyrightText: 2026 Gus Luong <gus.luong@gmail.com>
# SPDX-License-Identifier: MIT

<#
.SYNOPSIS
Leantime API rate-limit probe (sequential burst). Read-only.

.DESCRIPTION
Fires N fast sequential JSON-RPC calls (no pacing) at the Leantime /api/jsonrpc
endpoint using an API key from leantime-mcp .env, counts status codes, reports
when the first 429 occurred, captures its headers (Retry-After etc.), and then
polls until HTTP 200 returns to measure the actual reset window.

Only read-only method is used (Tickets.Tickets.getStatusLabels) - safe to run.

.NOTES
Env loading: searches for a .env file in the script folder or any parent
folder (works both at repo root and from scripts/). Keys are never written
into this script.

.USAGE
.\rate-limit-test.ps1                      # burst of 80 on hillary.agent key
.\rate-limit-test.ps1 -Count 50 -KeyVar LEANTIME_USER9_API_KEY
.\rate-limit-test.ps1 -Sustained           # adds a 60s paced (~1 req/s) phase
#>
param(
    [int]$Count = 80,
    [string]$KeyVar = "LEANTIME_USER13_API_KEY",   # default: hillary.agent
    [switch]$Sustained,                            # after burst: 60 reqs paced
    [double]$Rate = 1.0
)

$ErrorActionPreference = 'Stop'

# --- load env: find .env here or in any parent ---
$searchDir = $PSScriptRoot
while ($searchDir -and -not (Test-Path (Join-Path $searchDir '.env'))) {
    $parent = Split-Path $searchDir -Parent
    if ($parent -eq $searchDir) { $searchDir = $null; break }
    $searchDir = $parent
}
if (-not $searchDir) { throw ".env (with Leantime vars) not found in $PSScriptRoot or any parent" }
$envPath = Join-Path $searchDir '.env'
$vars = @{}
foreach ($l in Get-Content $envPath) {
    if ($l -match '^\s*([A-Za-z0-9_]+)=(.*\S)\s*$') { $vars[$matches[1]] = $matches[2] }
}

$key = $vars[$KeyVar]
if (-not $key) { throw "Key var $KeyVar not found in .env" }
$suffix = $KeyVar -replace '^LEANTIME_', '' -replace '_API_KEY$', ''
$url = if ($suffix -match '^USER\d+$') { $vars[("LEANTIME_{0}_URL" -f $suffix)] } else { $vars['LEANTIME_URL'] }
$endpoint = $url.TrimEnd('/') + '/api/jsonrpc'

$bodyFile = Join-Path $env:TEMP 'lt-ratelimit-body.json'
$hdrFile  = Join-Path $env:TEMP 'lt-ratelimit-hdrs.txt'
$outFile  = Join-Path $env:TEMP 'lt-ratelimit-body-out.txt'
'{"jsonrpc":"2.0","method":"leantime.rpc.Tickets.Tickets.getStatusLabels","params":{},"id":1}' |
    Set-Content -Path $bodyFile -Encoding ASCII

Write-Host "Endpoint : $endpoint"
Write-Host "Key set  : $KeyVar ($($key.Substring(0,11))...)"
Write-Host ""

function FireOnce {
    & curl.exe -s -o $outFile -D $hdrFile -w '%{http_code}' `
        -X POST -H 'Content-Type: application/json' -H "X-API-KEY: $key" `
        --data "@$bodyFile" --max-time 30 $endpoint
}

# Phase 0: single request, show response headers (may expose X-RateLimit-*)
$code = FireOnce
Write-Host "--- baseline single request: HTTP $code ---"
Get-Content $hdrFile -Raw
Write-Host ""

# Phase 1: burst, no sleep. Early-stop after 3 consecutive 429s (avoid ban-extension).
$results = New-Object System.Collections.Generic.List[string]
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$first429 = $null; $consec429 = 0; $hdr429 = ""
for ($i = 1; $i -le $Count; $i++) {
    $t = $sw.Elapsed.TotalMilliseconds
    $code = FireOnce
    if ($code -eq '429') {
        $consec429++
        if (-not $first429) { $first429 = $i; $hdr429 = Get-Content $hdrFile -Raw }
    } else { $consec429 = 0 }
    $results.Add("$i`t$([math]::Round($t))`t$code")
    $raw = (Get-Content $outFile -Raw).Trim()
    Write-Host ("{0,3}  {1,8} ms  {2}  body={3}" -f $i, [math]::Round($t), $code, $raw.Substring(0, [Math]::Min(120, $raw.Length)))
    if ($consec429 -ge 3) { Write-Host "... 3 consecutive 429s, stopping burst."; break }
}

$ok   = ($results | Where-Object { $_ -match "`t200$" }).Count
$r429 = ($results | Where-Object { $_ -match "`t429$" }).Count
$other = $results.Count - $ok - $r429
Write-Host ""
Write-Host "--- BURST SUMMARY ---"
Write-Host "attempted: $($results.Count)   200s: $ok   429s: $r429   other: $other"
if ($first429) {
    $t429 = ($results[$first429 - 1] -split "`t")[1]
    Write-Host "first 429 at attempt #$first429 (~$t429 ms after burst start)"
    Write-Host "429 headers:"
    $hdr429
    Write-Host "429 body: $(Get-Content $outFile -Raw)"
}

# Phase 2: poll until a 200 comes back (max 120s)
if ($r429 -gt 0) {
    Write-Host ""
    Write-Host "--- RECOVERY POLL (every 5s, max 120s) ---"
    for ($j = 1; $j -le 24; $j++) {
        Start-Sleep -Seconds 5
        $code = FireOnce
        Write-Host ("poll {0,2}  {1,6} s  HTTP {2}" -f $j, ($j * 5), $code)
        if ($code -eq '200') { break }
    }
}

# Phase 3: optional sustained test (pacing, catches per-minute windows a burst misses)
if ($Sustained) {
    Write-Host ""
    Write-Host "--- SUSTAINED: $Rate req/s for 60 s ---"
    $ok2 = 0; $lim2 = 0; $other2 = 0
    $sw2 = [System.Diagnostics.Stopwatch]::StartNew()
    for ($k = 1; $k -le 60; $k++) {
        $target = $sw2.Elapsed.TotalSeconds + ($k / $Rate)
        $sleep = $target - $sw2.Elapsed.TotalSeconds
        if ($sleep -gt 0) { Start-Sleep -Seconds $sleep }
        $code = FireOnce
        switch ($code) { '200' { $ok2++ } '429' { $lim2++ } default { $other2++ } }
        Write-Host "$k  HTTP $code"
    }
    Write-Host "sustained summary: 200=$ok2 429=$lim2 other=$other2"
}
Write-Host ""
Write-Host "DONE"