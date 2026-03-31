# Quick test script
Write-Host "Testing setup-global-mcp-servers.ps1..." -ForegroundColor Cyan

# Test 1: Script syntax
Write-Host "`n[Test 1] Checking PowerShell syntax..."
$syntaxErrors = $null
$null = [System.Management.Automation.PSParser]::Tokenize((Get-Content .\setup-global-mcp-servers.ps1 -Raw), [ref]$syntaxErrors)
if ($syntaxErrors.Count -eq 0) {
    Write-Host "[PASS] No syntax errors found" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Syntax errors found:" -ForegroundColor Red
    $syntaxErrors | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
}

# Test 2: Find Playbook repo
Write-Host "`n[Test 2] Checking if script can find Playbook repo..."
$gitRoot = git rev-parse --show-toplevel 2>$null
if ($gitRoot -match "IS\.Copilot\.Playbook") {
    Write-Host "[PASS] Running from Playbook repo: $gitRoot" -ForegroundColor Green
} else {
    Write-Host "[INFO] Not in Playbook repo, script will search for it" -ForegroundColor Yellow
}

# Test 3: Find MCP servers
Write-Host "`n[Test 3] Checking for MCP servers..."
$mcpServers = Get-ChildItem -Path $gitRoot -Recurse -Filter "*_mcp_server.py" -File | 
    Where-Object { $_.FullName -notmatch "\\(node_modules|\.venv|venv|__pycache__|\.git)\\" }
if ($mcpServers.Count -gt 0) {
    Write-Host "[PASS] Found $($mcpServers.Count) MCP server(s)" -ForegroundColor Green
    foreach ($server in $mcpServers) {
        Write-Host "  - $($server.Directory.Name)" -ForegroundColor Gray
    }
} else {
    Write-Host "[FAIL] No MCP servers found" -ForegroundColor Red
    exit 1
}

# Test 4: Python check
Write-Host "`n[Test 4] Checking Python..."
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    $version = & python --version 2>&1
    Write-Host "[PASS] $version" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Python not found" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== All Tests Passed ===" -ForegroundColor Green
Write-Host "`nThe script is ready to run!" -ForegroundColor Cyan
Write-Host "Run it with: .\setup-global-mcp-servers.ps1" -ForegroundColor White
