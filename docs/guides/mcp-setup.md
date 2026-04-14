# MCP Server Setup Guide

This repository includes Model Context Protocol (MCP) servers that extend GitHub Copilot with custom tools.

## Quick Setup (One Command)

### Option A: Global Setup (Works Across All Repos) ⭐

Run this **once** from anywhere on your machine:

```powershell
# Download and run the global setup script
Invoke-WebRequest -Uri "https://dev.azure.com/Vancity/Vancity/_apis/git/repositories/IS.Copilot.Playbook/items?path=/setup-global-mcp-servers.ps1&download=true&api-version=7.0" -OutFile setup-global-mcp-servers.ps1
.\setup-global-mcp-servers.ps1
```

OR if you already have the repo cloned:

```powershell
cd C:\Users\YourName\source\repos\IS.Copilot.Playbook
.\setup-global-mcp-servers.ps1
```

**Benefits:**
- ✅ Works in all your repositories (Isl.Pipelines.Core, IS.Copilot.Playbook, etc.)
- ✅ Automatically finds Playbook repo on your machine
- ✅ Configures VS Code User Settings (global)
- ✅ Run once, use everywhere!

### Option B: Workspace Setup (This Repo Only)

If you only want MCP servers in the Playbook repository:

```powershell
git clone <your-repo-url>
cd IS.Copilot.Playbook
.\setup-all-mcp-servers.ps1
```

That's it! The script will:
- ✅ Automatically discover all MCP servers
- ✅ Install Python dependencies
- ✅ Configure VS Code workspace settings
- ✅ Enable all tools in GitHub Copilot

## Available MCP Servers

### Integration Platform
**Location:** `.github/shared/skills/integration-platform/`

**Module tools provided:**
- `sql_scanner` - SQL scanning and report generation module tool (uses `action` routing)
- `repo_analyzer` - Repository scanning and access module tool (uses `action` routing)
- `scan_security` - Security vulnerability scanning module tool (uses `action` routing)
- `test_generator` - Ecosystem-aware test generation module tool (C# and Python)

**Common `sql_scanner` actions:**
- `scan_sql_injection_file`
- `scan_sql_injection_directory`
- `check_parameterized_query`
- `generate_scan_report`
- `generate_html_report`

**Usage in Copilot Chat:**
```
Scan this file for SQL injection vulnerabilities
```

## Manual Setup (Advanced)

If you need to set up individual servers:

```powershell
# Navigate to the Integration Platform MCP server directory
cd .github/shared/skills/integration-platform

# Install dependencies
pip install -r requirements.txt

# Run MCP server directly (for diagnostics)
python integration_platform_mcp_server.py
```

## Team Distribution

See individual MCP server folders for detailed usage guides:
- [Integration Platform README](.github/shared/skills/integration-platform/README.md)

## Troubleshooting

### MCP servers not showing in VS Code

1. Reload VS Code: `Ctrl+Shift+P` → "Developer: Reload Window"
2. Verify configuration: `Ctrl+Shift+P` → "GitHub Copilot: Show MCP Servers"
3. Check configuration files:
	- Global setup: `%APPDATA%\Code\User\mcp.json` (or `settings.json` under `chat.mcp.servers`)
	- Workspace setup: `.vscode/settings.json` under `github.copilot.chat.mcp.servers`

### Python errors

Ensure Python 3.8+ is installed:
```powershell
python --version
```

### Permission errors

Run PowerShell as Administrator or adjust execution policy:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Adding New MCP Servers

When adding a new MCP server:

1. Create folder: `.github/shared/skills/<server-name>/`
2. Name server file: `<server-name>_mcp_server.py`
3. Add `requirements.txt` with dependencies
4. Run `.\setup-all-mcp-servers.ps1` to auto-configure

The master setup script uses the pattern `*_mcp_server.py` to discover servers automatically.
