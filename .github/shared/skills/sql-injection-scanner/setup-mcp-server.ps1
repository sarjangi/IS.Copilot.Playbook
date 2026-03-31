# SQL Scanner MCP Server - Team Setup Script
# Run this script to configure the SQL Scanner MCP server in your VS Code

Write-Host "`n=== SQL Scanner MCP Server Setup ===" -ForegroundColor Cyan
Write-Host "This will configure the SQL Injection Scanner for GitHub Copilot`n" -ForegroundColor White

# Get the repository root
$repoRoot = git rev-parse --show-toplevel 2>$null
if (-not $repoRoot) {
    $repoRoot = $PSScriptRoot
}

Write-Host "Repository: $repoRoot" -ForegroundColor Gray

# Path to MCP server
$mcpServerPath = Join-Path $repoRoot ".github\shared\skills\sql-injection-scanner\sql_scanner_mcp_server.py"

if (-not (Test-Path $mcpServerPath)) {
    Write-Host "ERROR: MCP server not found at $mcpServerPath" -ForegroundColor Red
    Write-Host "Make sure you're in the IS.Copilot.Playbook repository" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ MCP server found" -ForegroundColor Green

# Check for Python
$pythonVersion = python --version 2>$null
if (-not $pythonVersion) {
    Write-Host "ERROR: Python not found. Please install Python 3.8+" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Python: $pythonVersion" -ForegroundColor Green

# Determine settings.json location
$workspaceSettings = Join-Path $repoRoot ".vscode\settings.json"

if (Test-Path $workspaceSettings) {
    Write-Host "✓ Workspace settings found" -ForegroundColor Green
    $settings = Get-Content $workspaceSettings -Raw | ConvertFrom-Json
} else {
    Write-Host "Creating workspace settings..." -ForegroundColor Yellow
    $settings = @{}
}

# Add MCP server configuration
if (-not $settings.'github.copilot.chat.mcp.servers') {
    $settings | Add-Member -NotePropertyName 'github.copilot.chat.mcp.servers' -NotePropertyValue @{} -Force
}

$settings.'github.copilot.chat.mcp.servers' | Add-Member -NotePropertyName 'sql-scanner' -NotePropertyValue @{
    command = 'python'
    args = @($mcpServerPath)
} -Force

# Save settings
$settingsJson = $settings | ConvertTo-Json -Depth 10
New-Item -Path (Split-Path $workspaceSettings) -ItemType Directory -Force | Out-Null
$settingsJson | Out-File $workspaceSettings -Encoding UTF8

Write-Host "`n✓ MCP server configured!" -ForegroundColor Green
Write-Host "`nConfiguration added to: $workspaceSettings" -ForegroundColor Gray

Write-Host "`n=== Next Steps ===" -ForegroundColor Cyan
Write-Host "1. Reload VS Code: Ctrl+Shift+P → 'Developer: Reload Window'" -ForegroundColor White
Write-Host "2. Open GitHub Copilot Chat" -ForegroundColor White
Write-Host "3. Try: 'Scan this file for SQL injection vulnerabilities'" -ForegroundColor White

Write-Host "`n=== Verify Tools ===" -ForegroundColor Cyan
Write-Host "Check MCP servers: Ctrl+Shift+P → 'GitHub Copilot: Show MCP Servers'" -ForegroundColor White
Write-Host "You should see 'sql-scanner' in the list" -ForegroundColor White

Write-Host "`n✅ Setup Complete!" -ForegroundColor Green
