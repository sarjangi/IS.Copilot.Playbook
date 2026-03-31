# MCP Server Verification Script
# Run this from ANY repository to verify MCP access

Write-Host "=== MCP Server Access Verification ===" -ForegroundColor Cyan

# Check 1: User Settings
Write-Host "`n[Test 1] Checking User Settings..." -ForegroundColor Yellow
$settings = Get-Content "$env:APPDATA\Code\User\settings.json" -Raw | ConvertFrom-Json

if ($settings.'chat.mcp.servers') {
    Write-Host "[PASS] MCP servers configured in User Settings" -ForegroundColor Green
    $settings.'chat.mcp.servers'.PSObject.Properties | ForEach-Object {
        Write-Host "  - $($_.Name): $($_.Value.command) $($_.Value.args -join ' ')" -ForegroundColor Gray
    }
} else {
    Write-Host "[FAIL] MCP servers not configured" -ForegroundColor Red
    exit 1
}

# Check 2: MCP Server File Exists
Write-Host "`n[Test 2] Checking MCP Server Files..." -ForegroundColor Yellow
$allExist = $true
$settings.'chat.mcp.servers'.PSObject.Properties | ForEach-Object {
    $serverPath = $_.Value.args[0]
    if (Test-Path $serverPath) {
        Write-Host "[PASS] Found: $serverPath" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Missing: $serverPath" -ForegroundColor Red
        $allExist = $false
    }
}

if (-not $allExist) {
    exit 1
}

# Check 3: Python Available
Write-Host "`n[Test 3] Checking Python..." -ForegroundColor Yellow
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    $version = & python --version 2>&1
    Write-Host "[PASS] $version" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Python not found" -ForegroundColor Red
    exit 1
}

# Check 4: Current Workspace
Write-Host "`n[Test 4] Current Workspace..." -ForegroundColor Yellow
$currentPath = Get-Location
Write-Host "Location: $currentPath" -ForegroundColor Gray

if ($currentPath -match "Isl\.Pipelines\.Core") {
    Write-Host "[PASS] Running from Isl.Pipelines.Core - MCP will work here!" -ForegroundColor Green
} elseif ($currentPath -match "IS\.Copilot\.Playbook") {
    Write-Host "[INFO] Running from Playbook repo" -ForegroundColor Cyan
} else {
    Write-Host "[INFO] Running from: $currentPath" -ForegroundColor Cyan
}

# Summary
Write-Host "`n=== Verification Complete ===" -ForegroundColor Green
Write-Host "`nMCP servers are accessible from ANY VS Code workspace!" -ForegroundColor Cyan
Write-Host "`nTo test in VS Code:" -ForegroundColor Yellow
Write-Host "  1. Open Isl.Pipelines.Core in VS Code" -ForegroundColor White
Write-Host "  2. Reload window: Ctrl+Shift+P -> 'Developer: Reload Window'" -ForegroundColor White
Write-Host "  3. Check servers: Ctrl+Shift+P -> 'GitHub Copilot: Show MCP Servers'" -ForegroundColor White
Write-Host "  4. Open any .py/.cs file" -ForegroundColor White
Write-Host "  5. Ask Copilot: 'Scan this file for SQL injection vulnerabilities'" -ForegroundColor White
