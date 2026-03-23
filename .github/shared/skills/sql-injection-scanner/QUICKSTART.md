# Quick Start Guide - SQL Injection Scanner

## For Developers (Local Development)

### 1. Install Once
```bash
pip install git+https://dev.azure.com/Vancity/Vancity/_git/IS.Copilot.Playbook#subdirectory=.github/shared/skills/sql-injection-scanner
```

### 2. Scan Your Code
```bash
# Scan current directory
sql-scanner scan-dir .

# Scan specific folder
sql-scanner scan-dir ./src

# Scan single file
sql-scanner scan-file database.py

# Scan remote repo
sql-scanner scan-repo https://dev.azure.com/Vancity/_git/MyRepo
```

### 3. Fix Issues
When vulnerabilities are found, you'll see:
```
[HIGH] database.py:45 - String concatenation in execute()
  Fix: Use parameterized queries
```

**Before (Vulnerable):**
```python
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

**After (Safe):**
```python
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

---

## For DevOps Teams (CI/CD Pipeline)

### 1. Add to Project's azure-pipelines.yml
```yaml
resources:
  repositories:
    - repository: playbook
      type: git
      name: IS.Copilot.Playbook

extends:
  template: .github/shared/skills/sql-injection-scanner/pipeline-template.yml@playbook
```

### 2. Commit and Push
```bash
git add azure-pipelines.yml
git commit -m "Add SQL injection scanner"
git push
```

### 3. Create Pipeline in Azure DevOps
1. Pipelines → New Pipeline
2. Select your repository
3. Existing YAML file → azure-pipelines.yml
4. Save and run

**That's it!** Now every commit gets scanned automatically.

---

## Usage Scenarios

### Before Committing
```bash
# Quick scan before commit
sql-scanner scan-dir .
```

### Code Review
```bash
# Scan specific branch
git checkout feature/new-api
sql-scanner scan-dir ./src
```

### Security Audit
```bash
# Scan with JSON output
sql-scanner scan-dir ./src --json > audit-results.json
```

### Scan Multiple Projects
```powershell
# PowerShell script
$projects = @("ProjectA", "ProjectB", "ProjectC")
foreach ($proj in $projects) {
    Write-Host "Scanning $proj..."
    sql-scanner scan-repo "https://dev.azure.com/Vancity/_git/$proj"
}
```

---

## Help & Options

```bash
# Show all commands
sql-scanner --help

# Show command-specific help
sql-scanner scan-dir --help
sql-scanner scan-repo --help
```

---

## Authentication

### Azure DevOps
**Windows:** Automatic (uses Windows credentials)  
**Linux/Mac:** Use Personal Access Token
```bash
sql-scanner scan-repo https://dev.azure.com/Vancity/_git/Repo --token YOUR_PAT
```

### GitHub
```bash
sql-scanner scan-repo https://github.com/owner/repo --token ghp_yourtoken
```

---

## What Gets Scanned

✅ **Languages:** Python, JavaScript, TypeScript, C#, Java, PHP, SQL  
✅ **Patterns:** String concatenation, f-strings, template literals, format(), %  
✅ **Files:** `.py`, `.js`, `.ts`, `.cs`, `.java`, `.php`, `.sql`  
❌ **Skipped:** `venv`, `node_modules`, `__pycache__`, `.git`

---

## Troubleshooting

**Issue:** `pip install` fails  
**Fix:** Make sure you're authenticated to Azure DevOps:
```bash
git config --global credential.helper manager
git clone https://dev.azure.com/Vancity/Vancity/_git/IS.Copilot.Playbook
# Enter credentials when prompted, then try pip install again
```

**Issue:** Command not found  
**Fix:** Restart terminal or use full path:
```bash
python -m pip show vancity-sql-injection-scanner  # Find install location
```

**Issue:** Too many false positives  
**Fix:** Review MEDIUM/LOW findings manually - only HIGH/CRITICAL are definite issues

---

## Next Steps

- 📖 Read full [README.md](README.md) for advanced usage
- 🔧 Check [USAGE.md](USAGE.md) for all usage methods
- 🎓 See [SKILL.md](SKILL.md) for GitHub Copilot integration
- 🚀 View [azure-pipelines-example.yml](azure-pipelines-example.yml) for pipeline examples

---

**Questions?** Contact Platform Engineering or open an issue in IS.Copilot.Playbook repository.
