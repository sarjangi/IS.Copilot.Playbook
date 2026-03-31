# Master MCP Server Setup Script
# Automatically discovers and configures ALL MCP servers in this repository

param(
    [switch]$WorkspaceSettings = $false  # Add to workspace settings (team-shared)
)

Write-Host "🔍 Discovering MCP servers in repository..." -ForegroundColor Cyan

# Find the git root directory
$gitRoot = git rev-parse --show-toplevel 2>$null
if (-not $gitRoot) {
    Write-Host "❌ Not in a git repository" -ForegroundColor Red
    exit 1
}

# Discover all MCP server Python files
$mcpServers = Get-ChildItem -Path $gitRoot -Recurse -Filter "*_mcp_server.py" -File | 
    Where-Object { $_.FullName -notmatch "\\(node_modules|\.venv|venv|__pycache__|\.git)\\" }

if ($mcpServers.Count -eq 0) {
    Write-Host "❌ No MCP servers found (looking for *_mcp_server.py files)" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Found $($mcpServers.Count) MCP server(s):" -ForegroundColor Green
foreach ($server in $mcpServers) {
    $relativePath = $server.FullName.Replace("$gitRoot\", "").Replace("\", "/")
    Write-Host "   - $relativePath" -ForegroundColor Gray
}

# Check Python
Write-Host "`n🐍 Checking Python installation..." -ForegroundColor Cyan
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "❌ Python not found. Please install Python 3.8+." -ForegroundColor Red
    exit 1
}

$pythonVersion = & python --version 2>&1
Write-Host "✅ $pythonVersion" -ForegroundColor Green

# Install dependencies for each MCP server
Write-Host "`n📦 Installing dependencies..." -ForegroundColor Cyan
$installedCount = 0
foreach ($server in $mcpServers) {
    $serverDir = $server.Directory.FullName
    $requirementsFile = Join-Path $serverDir "requirements.txt"
    
    if (Test-Path $requirementsFile) {
        $serverName = $server.Directory.Name
        Write-Host "   Installing for $serverName..." -ForegroundColor Gray
        & python -m pip install -q -r $requirementsFile
        if ($LASTEXITCODE -eq 0) {
            $installedCount++
        }
    }
}
Write-Host "✅ Installed dependencies for $installedCount server(s)" -ForegroundColor Green

# Configure VS Code settings
Write-Host "`n⚙️  Configuring VS Code MCP settings..." -ForegroundColor Cyan

$vscodePath = Join-Path $gitRoot ".vscode"
if (-not (Test-Path $vscodePath)) {
    New-Item -ItemType Directory -Path $vscodePath | Out-Null
}

$settingsFile = if ($WorkspaceSettings) {
    Join-Path $vscodePath "settings.json"
} else {
    # User settings - need to find VS Code user data directory
    $userSettingsPath = "$env:APPDATA\Code\User\settings.json"
    if (Test-Path $userSettingsPath) {
        $userSettingsPath
    } else {
        # Fallback to workspace
        Write-Host "⚠️  User settings not found, using workspace settings" -ForegroundColor Yellow
        Join-Path $vscodePath "settings.json"
    }
}

# Build MCP configuration
$mcpConfig = @{}
foreach ($server in $mcpServers) {
    $serverPath = $server.FullName.Replace("\", "/")
    $serverDir = $server.Directory.FullName.Replace("\", "/")
    
    # Generate server name from directory
    $serverName = $server.Directory.Name
    
    $mcpConfig[$serverName] = @{
        command = "python"
        args = @($serverPath)
        env = @{}
    }
}

# Read existing settings
$settings = @{}
if (Test-Path $settingsFile) {
    $existingJson = Get-Content $settingsFile -Raw | ConvertFrom-Json
    $settings = @{}
    foreach ($prop in $existingJson.PSObject.Properties) {
        $settings[$prop.Name] = $prop.Value
    }
}

# Merge MCP configuration
if (-not $settings.ContainsKey("github.copilot.chat.mcp.servers")) {
    $settings["github.copilot.chat.mcp.servers"] = @{}
}

foreach ($key in $mcpConfig.Keys) {
    $settings["github.copilot.chat.mcp.servers"][$key] = $mcpConfig[$key]
}

# Write settings
$settings | ConvertTo-Json -Depth 10 | Set-Content $settingsFile -Encoding UTF8
Write-Host "✅ Updated $settingsFile" -ForegroundColor Green

# Summary
Write-Host "`n✨ MCP Server Setup Complete!" -ForegroundColor Green
Write-Host "`nConfigured servers:" -ForegroundColor Cyan
foreach ($key in $mcpConfig.Keys) {
    Write-Host "   - $key" -ForegroundColor Gray
}

Write-Host "`n📋 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Reload VS Code window (Ctrl+Shift+P → 'Developer: Reload Window')" -ForegroundColor White
Write-Host "   2. Verify servers: Ctrl+Shift+P → 'GitHub Copilot: Show MCP Servers'" -ForegroundColor White
Write-Host "   3. Test in Copilot Chat!" -ForegroundColor White
