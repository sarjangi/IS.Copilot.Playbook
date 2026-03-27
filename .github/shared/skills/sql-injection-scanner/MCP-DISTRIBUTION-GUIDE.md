# MCP Server Distribution Options for Teams

## How to Share Your MCP Server with Other Developers

This guide covers all methods to distribute the SQL Scanner MCP server to your team.

---

## ⚡ TL;DR - Quick Setup (2 minutes)

**For individual developers who just want to use it now:**

```powershell
# 1. Run setup script
.\.github\shared\skills\sql-injection-scanner\setup-mcp-server.ps1

# 2. Reload VS Code (Ctrl+Shift+P → "Developer: Reload Window")

# 3. Try it: "Scan this file for SQL injection vulnerabilities"
```

**For team leads planning distribution:** Read the full guide below.

---

## 📊 Quick Comparison

| Method | Setup Time | Maintenance | Best For |
|--------|-----------|-------------|----------|
| **1. Repository-based** ⭐ | 2 min | Low | Team working in same repo |
| **2. Python Package (pip)** | 5 min | Medium | Company-wide distribution |
| **3. VS Code Extension** | 1 week | High | Public/enterprise distribution |
| **4. Shared Network Path** | 5 min | Low | Corporate environments |
| **5. Container/Remote** | 1 day | Medium | Multi-language teams |

---

## Option 1: Repository-Based (⭐ Recommended for You)

### ✅ Advantages:
- Already in your repo
- Version controlled with code
- No additional installation needed
- Team automatically gets updates via git pull

### Setup for Team Members:

**Method A: Automated Script**
```powershell
# Developers run once:
.\.github\shared\skills\sql-injection-scanner\setup-mcp-server.ps1
```

**Method B: Manual**
```json
// Add to .vscode/settings.json (already exists in repo)
{
  "github.copilot.chat.mcp.servers": {
    "sql-scanner": {
      "command": "python",
      "args": ["${workspaceFolder}/.github/shared/skills/sql-injection-scanner/sql_scanner_mcp_server.py"]
    }
  }
}
```

### 📝 Distribution Steps:
1. ✅ **Already done** - MCP server is in repo
2. Share [TEAM-SETUP.md](./TEAM-SETUP.md) with team
3. Developers clone repo → run setup script → done!

---

## Option 2: Python Package (pip install)

### When to Use:
- Multiple repositories need the same scanner
- Want centralized version management
- Enterprise-wide distribution

### Create Package:

```powershell
# Package structure already exists in your repo!
# Located at: .github/shared/skills/sql-injection-scanner/

# Build the package
cd .github/shared/skills/sql-injection-scanner
python setup.py sdist bdist_wheel

# Publish to internal PyPI server or Azure Artifacts
twine upload --repository-url https://pkgs.dev.azure.com/Vancity/_packaging/vancity-pypi/pypi/upload/ dist/*
```

### Team Installation:

```powershell
# One-time install:
pip install --index-url https://pkgs.dev.azure.com/Vancity/_packaging/vancity-pypi/pypi/simple/ vancity-sql-injection-scanner

# Configure VS Code (User settings):
{
  "github.copilot.chat.mcp.servers": {
    "sql-scanner": {
      "command": "python",
      "args": ["-m", "sql_injection_scanner.mcp_server"]
    }
  }
}
```

### 📝 Distribution Steps:
1. Publish to Azure Artifacts/PyPI
2. Share installation command
3. Developers install once globally
4. Works across all their projects!

---

## Option 3: VS Code Extension

### When to Use:
- Want marketplace distribution
- Need automatic updates
- Professional/polished solution

### Create Extension:

```bash
# Install extension scaffolder
npm install -g yo generator-code

# Create extension
yo code

# Add MCP server to extension
# Package and publish to VS Code Marketplace or private gallery
```

### Team Installation:

```
1. Go to VS Code Extensions
2. Search "Vancity SQL Scanner"
3. Click Install
4. Reload VS Code
5. Done! ✅
```

### 📝 Distribution Steps:
1. Create VS Code extension (1 week dev time)
2. Publish to marketplace or private gallery
3. Team installs like any other extension

---

## Option 4: Shared Network Path (Corporate Networks)

### When to Use:
- Corporate file server available
- Want centralized control
- No package management infrastructure

### Setup:

```powershell
# Copy MCP server to shared location
\\vancity-fileserver\shared\tools\sql-scanner\mcp_server.py

# Team configuration (User settings):
{
  "github.copilot.chat.mcp.servers": {
    "sql-scanner": {
      "command": "python",
      "args": ["\\\\vancity-fileserver\\shared\\tools\\sql-scanner\\mcp_server.py"]
    }
  }
}
```

### 📝 Distribution Steps:
1. Copy files to shared network path
2. Share configuration snippet
3. Developers add to their VS Code settings

---

## Option 5: Remote MCP Server (Advanced)

### When to Use:
- Multi-language teams (not just Python)
- Want centralized processing
- Need audit/logging of all scans

### Architecture:

```
Developer's VS Code
    ↓ (WebSocket/HTTP)
Remote MCP Server (docker container on internal server)
    ↓
SQL Scanner Engine
```

### Setup:

```dockerfile
# Dockerfile
FROM python:3.11-slim
COPY mcp_server.py /app/
EXPOSE 8080
CMD ["python", "/app/mcp_server_http.py"]
```

### Team Configuration:

```json
{
  "github.copilot.chat.mcp.servers": {
    "sql-scanner": {
      "url": "https://mcp-sql-scanner.vancity.internal",
      "type": "http"
    }
  }
}
```

### 📝 Distribution Steps:
1. Deploy MCP server to internal k8s/docker host
2. Share connection URL
3. Developers configure once

---

## 🎯 Recommendation for Vancity

### **Phase 1 (Now) - Repository-Based** ⭐

Use Option 1:
- Already implemented ✅
- Share [TEAM-SETUP.md](./TEAM-SETUP.md)
- Team runs setup script
- **Estimated rollout: 1 day**

### **Phase 2 (Q2 2026) - Python Package**

When usage grows:
- Publish to Azure Artifacts
- Enterprise-wide availability
- Centralized version management
- **Estimated effort: 2 days**

### **Phase 3 (Future) - VS Code Extension**

If becomes critical tool:
- Professional distribution
- Automatic updates
- Marketplace presence
- **Estimated effort: 1-2 weeks**

---

## 📋 Team Rollout Checklist

### For Repository Method:
- [ ] Commit setup script to repo
- [ ] Add [TEAM-SETUP.md](./TEAM-SETUP.md) documentation
- [ ] Announce in team chat
- [ ] Run setup script yourself (verify it works)
- [ ] Help 1-2 team members set up
- [ ] Add to onboarding documentation
- [ ] Demo in team meeting

### Success Metrics:
- ✅ All developers have MCP server configured
- ✅ Can ask Copilot to scan code naturally
- ✅ Scans run successfully
- ✅ Team finds it useful

---

## 🐛 Common Issues & Solutions

### "Works on my machine, not on teammate's"

**Problem**: Absolute paths differ
**Solution**: Use `${workspaceFolder}` variable in settings.json

### "Python not found"

**Problem**: Python not in PATH
**Solution**: Provide Python installation guide or use absolute path to python.exe

### "Need to set up for multiple repos"

**Problem**: Repository-based approach needs setup per repo
**Solution**: Move to Option 2 (Python package with user-level settings)

---

## 💡 Quick Start for Your Team

**Send this message:**

> Hey team! 👋
>
> We now have SQL injection scanning built into GitHub Copilot!
>
> **Setup (2 minutes):**
> 1. Pull latest from main
> 2. Run: `.\.github\shared\skills\sql-injection-scanner\setup-mcp-server.ps1`
> 3. Reload VS Code
>
> **Use it:**
> Just ask Copilot: "Scan this file for SQL vulnerabilities"
>
> Docs: .github/shared/skills/sql-injection-scanner/TEAM-SETUP.md

---

**Questions about distribution?** Let me know and I can help implement any of these options!
