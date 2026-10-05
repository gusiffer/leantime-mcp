# SPDX-FileCopyrightText: 2026 Gus Luong <gus.luong@gmail.com>
# SPDX-License-Identifier: MIT

<#
.SYNOPSIS
Leantime API rate-limit probe (true concurrent burst). Read-only.

.DESCRIPTION
Fires N simultaneous JSON-RPC requests (one curl.exe process per request) to
test burst/rate limiting. Catches instant-burst ceilings that a sequential
burst underestimates. Uses a read-only method (Tickets.Tickets.getStatusLabels).

GOTCHAS baked into this script (each produced fake 401/400s in the past):
- PowerShell 5.1 Start-Process -ArgumentList does NOT auto-quote args; we pass
  one explicitly-quoted command string instead of an arg array.
- curl multi-URL invocations ACCUMULATE -H headers across all URLs; duplicated
  X-API-KEY headers get comma-joined and the server rejects them. Never batch
  requests with distinct headers into a single curl call.
- A 401 {"error":"Unauthorized"} from this probe means the probe mangled the
  key, not that the key expired.

.NOTES
Env loading: searches for a .env file in the script folder or any parent
folder. Keys are never written into this script.

.USAGE
.\parallel-burst.ps1                          # 60 concurrent on hillary.agent key
.\parallel-burst.ps1 -N 150 -QuietSeconds 40  # bigger burst, cool-down first
.\parallel-burst.ps1 -KeyVar LEANTIME_API_KEY # default (gus) key
#>
param(
    [int]$N = 60,
    [string]$KeyVar = "LEANTIME_USER13_API_KEY",
    [int]$QuietSeconds = 45
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
$base = if ($suffix -match '^USER\d+$') { $vars[("LEANTIME_{0}_URL" -f $suffix)] } else { $vars['LEANTIME_URL'] }
$endpoint = $base.TrimEnd('/') + '/api/jsonrpc'
$bodyFile = Join-Path $env:TEMP 'lt-ratelimit-body.json'
'{"jsonrpc":"2.0","method":"leantime.rpc.Tickets.Tickets.getStatusLabels","params":{},"id":1}' |
    Set-Content -Path $bodyFile -Encoding ASCII

$dir = Join-Path $env:TEMP ('lt-burst2-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $dir -Force | Out-Null
if ($QuietSeconds -gt 0) {
    Write-Host "cooling down $QuietSeconds s for a clean window..."
    Start-Sleep -Seconds $QuietSeconds
}
Write-Host "firing $N concurrent curl processes on $KeyVar ..."
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$procs = @()
for ($i = 1; $i -le $N; $i++) {
    $codeOut = Join-Path $dir ("req_{0}.code" -f $i)
    $errOut  = Join-Path $dir ("req_{0}.err"  -f $i)
    # single explicit command string; headers quoted manually for the child process
    $argString = '-s -o NUL -w "%{http_code}" ' +
                 '-H "User-Agent: lt-ratelimit-probe" ' +
                 '-H "Content-Type: application/json" ' +
                 '-H "X-API-KEY: ' + $key + '" ' +
                 '--data "@' + $bodyFile + '" ' + $endpoint
    $procs += Start-Process -FilePath curl.exe -ArgumentList $argString `
        -RedirectStandardOutput $codeOut -RedirectStandardError $errOut `
        -WindowStyle Hidden -PassThru
}
$procs | Wait-Process -Timeout 150 -ErrorAction Ignore
$elapsed = $sw.Elapsed.TotalSeconds

$codes = @(); $badFiles = 0
Get-ChildItem $dir -Filter '*.code' | ForEach-Object {
    $c = (Get-Content $_.FullName -Raw).Trim()
    if ($c -match '^\d{3}$') { $codes += [int]$c } else { $badFiles++ }
}
Write-Host ("{0} cleanly-parsed transfers in {1:N1}s (unparsed files: {2})" -f $codes.Count, $elapsed, $badFiles)
$g = $codes | Group-Object | Sort-Object Name
$g | ForEach-Object { Write-Host ("  HTTP {0,4} : {1}" -f $_.Name, $_.Count) }
if ($badFiles -gt 0) {
    Write-Host "sample of an unparsed .code file:"
    Get-ChildItem $dir -Filter '*.code' | Where-Object { (Get-Content $_.FullName -Raw).Trim() -notmatch '^\d{3}$' } | Select-Object -First 1 | ForEach-Object { Write-Host ("{0}: {1}" -f $_.Name, ((Get-Content $_.FullName -Raw).Trim().Substring(0,80))) }
}
if ($codes -contains 429) {
    Write-Host ""
    Write-Host "429 observed -- follow-up header dump:"
    $hdrFile = Join-Path $dir 'probe429.hdrs.txt'
    & curl.exe -s -o NUL -D $hdrFile -H 'User-Agent: lt-ratelimit-probe' -H 'Content-Type: application/json' -H "X-API-KEY: $key" --data "@$bodyFile" $endpoint | Out-Null
    Get-Content $hdrFile -Raw
}
Write-Host "DONE (results in $dir)"