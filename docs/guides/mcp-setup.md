# MCP Server Setup Guide

This repository includes Model Context Protocol (MCP) servers that extend GitHub Copilot with custom tools.

## Quick Setup (One Command)

Clone the repo and run the master setup script:

```powershell
git clone <your-repo-url>
cd IS.Copilot.Playbook
.\setup-all-mcp-servers.ps1
```

That's it! The script will:
- ✅ Automatically discover all MCP servers
- ✅ Install Python dependencies
- ✅ Configure VS Code settings
- ✅ Enable all tools in GitHub Copilot

## Available MCP Servers

### SQL Injection Scanner
**Location:** `.github/shared/skills/sql-injection-scanner/`

**Tools provided:**
- `scan_file` - Scan a single file for SQL injection vulnerabilities
- `scan_directory` - Recursively scan a directory

**Usage in Copilot Chat:**
```
Scan this file for SQL injection vulnerabilities
```

## Manual Setup (Advanced)

If you need to set up individual servers:

```powershell
# Navigate to a specific MCP server directory
cd .github/shared/skills/sql-injection-scanner

# Run its setup script
.\setup-mcp-server.ps1
```

## Team Distribution

See individual MCP server folders for detailed distribution guides:
- [SQL Injection Scanner Distribution](.github/shared/skills/sql-injection-scanner/MCP-DISTRIBUTION-GUIDE.md)

## Troubleshooting

### MCP servers not showing in VS Code

1. Reload VS Code: `Ctrl+Shift+P` → "Developer: Reload Window"
2. Verify configuration: `Ctrl+Shift+P` → "GitHub Copilot: Show MCP Servers"
3. Check settings file: `.vscode/settings.json` should contain `github.copilot.chat.mcp.servers`

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
