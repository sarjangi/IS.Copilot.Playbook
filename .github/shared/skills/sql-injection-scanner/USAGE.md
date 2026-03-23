# SQL Injection Scanner - Quick Usage Guide

Choose the method that fits your workflow:

## 🚀 For DevOps Teams (Recommended)

### ✅ Add to Azure DevOps Pipeline

**Step 1:** Create `azure-pipelines.yml` in your project:

```yaml
resources:
  repositories:
    - repository: playbook
      type: git
      name: Vancity/IS.Copilot.Playbook

extends:
  template: .github/shared/skills/sql-injection-scanner/pipeline-template.yml@playbook
```

**Step 2:** Create pipeline in Azure DevOps:
1. Pipelines → New Pipeline
2. Select your repository
3. Choose "Existing Azure Pipelines YAML file"
4. Point to `azure-pipelines.yml`
5. Save and run

**Result:** Automatic security scanning on every commit! 🎉

---

## 👨‍💻 For Developers (Interactive)

### Option A: Command Line (One-time Setup)

**1. Clone playbook:**
```powershell
cd C:\repos
git clone https://dev.azure.com/Vancity/Vancity/_git/IS.Copilot.Playbook
```

**2. Install dependencies:**
```powershell
cd IS.Copilot.Playbook\.github\shared\skills\sql-injection-scanner
pip install -r requirements.txt
```

**3. Scan any project:**
```powershell
# Scan local directory
python cli.py scan-dir C:\repos\YourProject\src

# Scan remote Azure DevOps repo
python cli.py scan-repo https://dev.azure.com/Vancity/Project/_git/Repo

# Scan specific file
python cli.py scan-file C:\repos\YourProject\database.py
```

### Option B: GitHub Copilot Chat

**1. Open multi-root workspace:**
```json
// workspace.code-workspace
{
  "folders": [
    {"path": "C:\\repos\\YourProject"},
    {"path": "C:\\repos\\IS.Copilot.Playbook"}
  ]
}
```

**2. Ask Copilot:**
```
@workspace Scan this file for SQL injection vulnerabilities

@workspace Check if this query is safe from SQL injection:
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

**Result:** Copilot uses the skill to guide you! 🤖

---

## 📊 Comparison

| Method | Setup Time | Best For | Automation |
|--------|-----------|----------|------------|
| **Azure Pipeline** | 5 min | Teams, CI/CD | ✅ Automatic |
| **Command Line** | 10 min | Ad-hoc scans, Testing | ❌ Manual |
| **Copilot Chat** | 15 min | Learning, Code review | ❌ On-demand |

---

## 🎯 Recommendations by Role

### Security Team
→ **Azure Pipeline Template** - Enforce scanning across all projects

### DevOps Engineer  
→ **Azure Pipeline Template** - Integrate into deployment gates

### Developer (Daily Coding)
→ **Copilot Chat** - Get real-time security guidance

### Developer (Code Review)
→ **Command Line** - Scan branches before merging

### QA/Testing
→ **Command Line** - Scan test environments

---

## 📚 More Details

- Full documentation: [README.md](README.md)
- Pipeline template: [pipeline-template.yml](pipeline-template.yml)
- Example configuration: [azure-pipelines-example.yml](azure-pipelines-example.yml)
- Skills definition: [SKILL.md](SKILL.md)

---

## ❓ Quick Troubleshooting

**Q: Pipeline fails with "repository not found"**  
A: Use full format `name: Vancity/IS.Copilot.Playbook` (ProjectName/RepoName)

**Q: Windows auth doesn't work**  
A: Add `--token YOUR_PAT` to CLI commands

**Q: Copilot doesn't know about SQL injection**  
A: Make sure IS.Copilot.Playbook is in your workspace

**Q: Too many false positives**  
A: Review MEDIUM/LOW findings - they need context validation

---

Need help? Contact the Platform Engineering team or open an issue in the Playbook repository.
