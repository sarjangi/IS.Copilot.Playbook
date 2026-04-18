# Global MCP Server Setup Script
# This script finds the IS.Copilot.Playbook repo on your machine and configures
# all MCP servers in your VS Code User Settings (works across ALL repos)

param(
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

# Ensure Unicode characters render correctly in all PowerShell consoles
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

# Helper function to convert folder names to user-friendly display names
function ConvertTo-DisplayName {
    param([string]$folderName)
    
    # Convert hyphens to spaces and title case each word
    # Example: "integration-platform" -> "Integration Platform"
    $words = $folderName -split '-'
    $titleCaseWords = $words | ForEach-Object { 
        $_.Substring(0,1).ToUpper() + $_.Substring(1).ToLower() 
    }
    return $titleCaseWords -join ' '
}

# Helper function to derive VS Code's internal MCP tool prefix from a server display name.
# VS Code slugifies "Integration Platform" -> "mcp_integration_p"
# Formula: mcp_ + first-word-lowercase + _ + first-letter-of-each-remaining-word
function ConvertTo-McpToolPrefix {
    param([string]$serverName)
    $words = $serverName.ToLower() -split '\s+'
    if ($words.Count -eq 1) {
        return "mcp_$($words[0])"
    }
    $initials = ($words[1..($words.Count - 1)] | ForEach-Object { $_[0] }) -join '_'
    return "mcp_$($words[0])_$initials"
}

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

# Resolve full Python path once — used for both pip installs and mcp.json
$pythonPath = (Get-Command python).Source.Replace("\\", "/")
Write-Host "   Python path: $pythonPath" -ForegroundColor Gray

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
            $null = & $pythonPath -m pip install -q -r $requirementsFile 2>&1
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
# $pythonPath already resolved above in Step 3
Write-Host "   Python executable: $pythonPath" -ForegroundColor Gray

# Track registered server names for agent patching
$registeredServerNames = @()

# Build server configurations
foreach ($server in $mcpServers) {
    # Use forward slashes for cross-platform compatibility
    $serverPath = $server.FullName.Replace("\\", "/")
    $folderName = $server.Directory.Name
    
    # Convert folder name to user-friendly display name
    # Example: "integration-platform" -> "Integration Platform"
    $serverName = ConvertTo-DisplayName -folderName $folderName
    $registeredServerNames += $serverName
    
    Write-Host "   Configuring: $serverName (from $folderName folder)" -ForegroundColor Gray
    
    # Add or update server configuration with FULL Python path
    $serverConfig = [PSCustomObject]@{
        type = "stdio"
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
if ($verification.servers) {
    foreach ($prop in ($verification.servers | Get-Member -MemberType NoteProperty)) {
        $serverName = $prop.Name
        Write-Host "   [OK] $serverName" -ForegroundColor Gray
        
        # Add recommendation for Integration Platform
        if ($serverName -eq "Integration Platform") {
            Write-Host "      -> RECOMMENDED: Unified server with SQL scanning + repository analysis" -ForegroundColor Green
        } elseif ($serverName -eq "Sql Injection Scanner") {
            Write-Host "      -> Legacy: Use Integration Platform for new projects" -ForegroundColor DarkGray
        }
    }
}

Write-Host "`nThese servers are now available in ALL your VS Code workspaces!" -ForegroundColor Green

# ============================================================================
# Step 6: Install agents to VS Code user prompts folder (global, all workspaces)
# ============================================================================

Write-Host "`nStep 6: Installing Copilot agents..." -ForegroundColor Cyan

$userPromptsDir = "$env:APPDATA\Code\User\prompts"
if (-not (Test-Path $userPromptsDir)) {
    New-Item -ItemType Directory -Force -Path $userPromptsDir | Out-Null
    Write-Host "   Created prompts directory: $userPromptsDir" -ForegroundColor Gray
}

$agentFiles = Get-ChildItem -Path $playbookRepo -Recurse -Filter "*.agent.md" -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "\\(node_modules|\.venv|venv|__pycache__|\.git)\\" }

if ($agentFiles.Count -eq 0) {
    Write-Host "   [INFO] No agent files found" -ForegroundColor DarkGray
} else {
    # Build explicit tool IDs from all registered servers.
    # VS Code slugifies server names: "Integration Platform" -> mcp_integration_p_<toolname>
    $allToolIds = @()
    foreach ($serverName in $registeredServerNames) {
        $prefix = ConvertTo-McpToolPrefix -serverName $serverName
        # Find the server's Python file and extract tool names from the self.tools dict
        $serverFile = ($mcpServers | Where-Object {
            (ConvertTo-DisplayName -folderName $_.Directory.Name) -eq $serverName
        }).FullName
        if ($serverFile -and (Test-Path $serverFile)) {
            # Match only top-level tool keys: lines like            "tool_name": {
            # followed by a "description" key (distinguishes tools from schema properties)
            $serverText = [System.IO.File]::ReadAllText($serverFile)
            $toolNames = [regex]::Matches($serverText, '"(\w+)":\s*\{\s*[\r\n]+\s*"description"') |
                ForEach-Object { $_.Groups[1].Value }
            foreach ($toolName in $toolNames) {
                $allToolIds += "${prefix}_${toolName}"
            }
        }
    }

    foreach ($agentFile in $agentFiles) {
        $dest = Join-Path $userPromptsDir $agentFile.Name
        $agentContent = [System.IO.File]::ReadAllText($agentFile.FullName, [System.Text.UTF8Encoding]::new($false))

        # Strip workspace-only flag so the deployed copy is visible in the agent picker
        $agentContent = $agentContent -replace '(?m)^user-invocable:\s*false\r?\n', ''

        if ($allToolIds.Count -gt 0) {
            $toolsLines = $allToolIds | ForEach-Object { "  - $_" }
            $toolsBlock = "tools:`n" + ($toolsLines -join "`n") + "`n"
            # Replace only the tools: block; stop before any line that isn't a list item
            $agentContent = $agentContent -replace '(?m)^tools:\r?\n(  - [^\r\n]+\r?\n)+', $toolsBlock
        }

        [System.IO.File]::WriteAllText($dest, $agentContent, [System.Text.UTF8Encoding]::new($false))
        Write-Host "   [OK] $($agentFile.BaseName) -> $dest" -ForegroundColor Green
        if ($allToolIds.Count -gt 0) {
            Write-Host "      tools: $($allToolIds -join ', ')" -ForegroundColor DarkGray
        }
    }
    Write-Host "[OK] $($agentFiles.Count) agent(s) installed globally" -ForegroundColor Green
}

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "   1. Reload VS Code: Ctrl+Shift+P -> 'Developer: Reload Window'" -ForegroundColor White
Write-Host "   2. Verify setup: Check MCP status in GitHub Copilot" -ForegroundColor White
Write-Host "   3. Test Integration Platform: 'Scan this file for SQL injection vulnerabilities'" -ForegroundColor White
Write-Host "   4. Use security-pipeline agent: select it from the agent picker in Copilot Chat" -ForegroundColor White
Write-Host "   5. View README: .github/shared/skills/integration-platform/README.md" -ForegroundColor White

Write-Host "`nRecommendation:" -ForegroundColor Cyan
Write-Host "   Use 'Integration Platform' for all new work - it includes:" -ForegroundColor White
Write-Host "   - All SQL injection scanning features" -ForegroundColor Gray
Write-Host "   - Repository cloning and analysis" -ForegroundColor Gray
Write-Host "   - HTML report generation" -ForegroundColor Gray
Write-Host "   - Parameterized query validation" -ForegroundColor Gray
Write-Host "   - Broad security scanning and C# test generation" -ForegroundColor Gray
Write-Host "   - End-to-end security pipeline with PR creation" -ForegroundColor Gray

Write-Host "`nTip: When you pull updates to IS.Copilot.Playbook, run this script" -ForegroundColor Cyan
Write-Host "again to pick up new MCP servers automatically!" -ForegroundColor Cyan
