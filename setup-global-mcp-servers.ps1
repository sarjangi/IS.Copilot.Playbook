# Global MCP Server Setup Script
# This script finds the IS.Copilot.Playbook repo on your machine and configures
# all MCP servers in your VS Code User Settings (works across ALL repos)

param(
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== Global MCP Server Setup ===" -ForegroundColor Cyan
Write-Host "Configuring MCP servers from IS.Copilot.Playbook for all repositories`n" -ForegroundColor White

# ============================================================================
# Step 1: Find IS.Copilot.Playbook repository
# ============================================================================

Write-Host "Step 1: Searching for IS.Copilot.Playbook repository..." -ForegroundColor Cyan

$playbookRepo = $null

# Strategy 1: Check common source locations
$searchPaths = @(
    "C:\Users\$env:USERNAME\source\repos",
    "C:\source\repos",
    "C:\repos", 
    "C:\dev",
    "C:\Users\$env:USERNAME\Documents\GitHub",
    "C:\Users\$env:USERNAME\git"
)

foreach ($searchPath in $searchPaths) {
    if (Test-Path $searchPath) {
        $found = Get-ChildItem -Path $searchPath -Directory -Filter "IS.Copilot.Playbook" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            $playbookRepo = $found.FullName
            Write-Host "[OK] Found repository at: $playbookRepo" -ForegroundColor Green
            break
        }
    }
}

# Strategy 2: If running from the Playbook repo itself
if (-not $playbookRepo) {
    $currentGitRoot = git rev-parse --show-toplevel 2>$null
    if ($currentGitRoot -and $currentGitRoot -match "IS\.Copilot\.Playbook") {
        $playbookRepo = $currentGitRoot.Replace("/", "\")
        Write-Host "[OK] Found repository (current location): $playbookRepo" -ForegroundColor Green
    }
}

# Strategy 3: Ask user for location
if (-not $playbookRepo) {
    Write-Host "[ERROR] Could not find IS.Copilot.Playbook repository automatically" -ForegroundColor Red
    Write-Host "`nPlease enter the full path to IS.Copilot.Playbook repository:" -ForegroundColor Yellow
    Write-Host "Example: C:\Users\sararja\source\repos\IS.Copilot.Playbook" -ForegroundColor Gray
    $userPath = Read-Host "Path"
    
    if (Test-Path $userPath) {
        $playbookRepo = $userPath
        Write-Host "[OK] Using repository at: $playbookRepo" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Path not found: $userPath" -ForegroundColor Red
        Write-Host "`nPlease clone IS.Copilot.Playbook first:" -ForegroundColor Yellow
        Write-Host "git clone https://dev.azure.com/Vancity/Vancity/_git/IS.Copilot.Playbook" -ForegroundColor Gray
        exit 1
    }
}

# ============================================================================
# Step 2: Discover all MCP servers
# ============================================================================

Write-Host "`nStep 2: Discovering MCP servers..." -ForegroundColor Cyan

$mcpServers = Get-ChildItem -Path $playbookRepo -Recurse -Filter "*_mcp_server.py" -File -ErrorAction SilentlyContinue | 
    Where-Object { $_.FullName -notmatch "\\(node_modules|\.venv|venv|__pycache__|\.git)\\" }

if ($mcpServers.Count -eq 0) {
    Write-Host "[ERROR] No MCP servers found in repository" -ForegroundColor Red
    Write-Host "Looking for files matching pattern: *_mcp_server.py" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Found $($mcpServers.Count) MCP server(s):" -ForegroundColor Green
foreach ($server in $mcpServers) {
    $serverName = $server.Directory.Name
    Write-Host "   - $serverName" -ForegroundColor Gray
    if ($Verbose) {
        Write-Host "     Path: $($server.FullName)" -ForegroundColor DarkGray
    }
}

# ============================================================================
# Step 3: Check Python
# ============================================================================

Write-Host "`nStep 3: Checking Python installation..." -ForegroundColor Cyan

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python not found. Please install Python 3.8+." -ForegroundColor Red
    Write-Host "Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

$pythonVersion = & python --version 2>&1
Write-Host "[OK] $pythonVersion" -ForegroundColor Green

# ============================================================================
# Step 4: Install dependencies
# ============================================================================

Write-Host "`nStep 4: Installing dependencies..." -ForegroundColor Cyan

$installedCount = 0
foreach ($server in $mcpServers) {
    $serverDir = $server.Directory.FullName
    $serverName = $server.Directory.Name
    $requirementsFile = Join-Path $serverDir "requirements.txt"
    
    if (Test-Path $requirementsFile) {
        Write-Host "   Installing for $serverName..." -ForegroundColor Gray
        try {
            $ErrorActionPreference = "Continue"
            $null = & python -m pip install -q -r $requirementsFile 2>&1
            $ErrorActionPreference = "Stop"
            if ($LASTEXITCODE -eq 0) {
                $installedCount++
            } else {
                Write-Host "   [WARN] pip install returned exit code $LASTEXITCODE (may already be installed)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "   [WARN] Error installing dependencies: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   [INFO] No requirements.txt for $serverName" -ForegroundColor DarkGray
    }
}

if ($installedCount -gt 0) {
    Write-Host "[OK] Installed dependencies for $installedCount server(s)" -ForegroundColor Green
}

# ============================================================================
# Step 5: Configure MCP Gateway (global mcp.json)
# ============================================================================

Write-Host "`nStep 5: Configuring MCP Gateway (global mcp.json)..." -ForegroundColor Cyan

$mcpJsonPath = "$env:APPDATA\Code\User\mcp.json"
$vscodeUserDir = "$env:APPDATA\Code\User"

if (-not (Test-Path $vscodeUserDir)) {
    Write-Host "[ERROR] VS Code User directory not found at: $vscodeUserDir" -ForegroundColor Red
    Write-Host "Please ensure VS Code is installed" -ForegroundColor Yellow
    exit 1
}

Write-Host "   MCP config: $mcpJsonPath" -ForegroundColor Gray

# Read existing mcp.json or create new one
$mcpData = $null
if (Test-Path $mcpJsonPath) {
    Write-Host "   Reading existing mcp.json..." -ForegroundColor Gray
    try {
        $mcpContent = [System.IO.File]::ReadAllText($mcpJsonPath, [System.Text.UTF8Encoding]::new($false))
        $mcpData = $mcpContent | ConvertFrom-Json
    } catch {
        Write-Host "   [WARN] Failed to read existing mcp.json: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "   Creating new configuration..." -ForegroundColor Gray
        $mcpData = [PSCustomObject]@{}
    }
} else {
    Write-Host "   Creating new mcp.json..." -ForegroundColor Gray
    $mcpData = [PSCustomObject]@{}
}

# Initialize servers object if it doesn't exist
if (-not $mcpData.PSObject.Properties['servers']) {
    Write-Host "   Creating servers property..." -ForegroundColor Gray
    $mcpData | Add-Member -MemberType NoteProperty -Name 'servers' -Value ([PSCustomObject]@{}) -Force
}

# Get full Python path (not just "python")
$pythonPath = (Get-Command python).Source.Replace("\", "/")
Write-Host "   Python executable: $pythonPath" -ForegroundColor Gray

# Build server configurations
foreach ($server in $mcpServers) {
    # Use forward slashes for cross-platform compatibility
    $serverPath = $server.FullName.Replace("\", "/")
    $serverName = $server.Directory.Name
    
    Write-Host "   Configuring: $serverName" -ForegroundColor Gray
    
    # Add or update server configuration with FULL Python path
    $serverConfig = [PSCustomObject]@{
        command = $pythonPath
        args = @($serverPath)
        env = [PSCustomObject]@{}
    }
    
    $mcpData.servers | Add-Member -MemberType NoteProperty -Name $serverName -Value $serverConfig -Force
}

# Backup existing mcp.json if it exists
if (Test-Path $mcpJsonPath) {
    $backupPath = "$mcpJsonPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $mcpJsonPath $backupPath
    Write-Host "   Backup created: $(Split-Path $backupPath -Leaf)" -ForegroundColor DarkGray
}

# Write updated mcp.json
try {
    # Use proper JSON serialization
    $jsonOutput = $mcpData | ConvertTo-Json -Depth 20 -Compress:$false
    [System.IO.File]::WriteAllText($mcpJsonPath, $jsonOutput, [System.Text.UTF8Encoding]::new($false))
    Write-Host "[OK] Updated global mcp.json" -ForegroundColor Green
    
    # Verify
    $verification = [System.IO.File]::ReadAllText($mcpJsonPath) | ConvertFrom-Json
    
    if ($verification.servers) {
        $serverCount = ($verification.servers | Get-Member -MemberType NoteProperty).Count
        Write-Host "[OK] Verified: $serverCount MCP server(s) configured" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Verification failed - servers property not found after write" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] Failed to write mcp.json: $($_.Exception.Message)" -ForegroundColor Red
    if (Test-Path $backupPath) {
        Write-Host "Backup preserved at: $backupPath" -ForegroundColor Yellow
    }
    exit 1
}

# ============================================================================
# Summary
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host "`nConfigured MCP Servers:" -ForegroundColor Cyan
foreach ($prop in $mcpConfig.PSObject.Properties) {
    Write-Host "   [OK] $($prop.Name)" -ForegroundColor Gray
}

Write-Host "`nThese servers are now available in ALL your VS Code workspaces!" -ForegroundColor Green

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "   1. Reload VS Code: Ctrl+Shift+P -> 'Developer: Reload Window'" -ForegroundColor White
Write-Host "   2. Verify setup: Ctrl+Shift+P -> 'MCP: list'" -ForegroundColor White
Write-Host "   3. Check Output: Ctrl+Shift+U -> Select 'MCP Gateway'" -ForegroundColor White
Write-Host "   4. Test in Copilot Chat: 'Scan this file for SQL injection vulnerabilities'" -ForegroundColor White

Write-Host "`nTip: When you pull updates to IS.Copilot.Playbook, run this script" -ForegroundColor Cyan
Write-Host "again to pick up new MCP servers automatically!" -ForegroundColor Cyan
