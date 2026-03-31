# SQL Injection Scanner - Python Tools

Automated security scanning for SQL injection vulnerabilities with support for local files, directories, and remote Git repositories (Azure DevOps, GitHub, GitLab, Bitbucket).

## Features

✅ **File Scanning** - Scan individual Python/JavaScript/SQL files  
✅ **Directory Scanning** - Recursive scanning of entire codebases  
✅ **Repository Scanning** - Clone and scan remote Git repositories  
✅ **Azure DevOps Support** - Works with Windows authentication (no token needed!)  
✅ **Multi-Platform** - GitHub, GitLab, Bitbucket support  
✅ **Pattern Detection** - Regex + Bandit static analysis  
✅ **Detailed Reports** - Line numbers, severity ratings, fix recommendations  

## Installation

### Option 1: Install from Git (Recommended for Developers)

Install directly from Azure DevOps - **no need to clone!**

```bash
# Install globally
pip install git+https://dev.azure.com/Vancity/Vancity/_git/IS.Copilot.Playbook#subdirectory=.github/shared/skills/sql-injection-scanner

# Or install in virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install git+https://dev.azure.com/Vancity/Vancity/_git/IS.Copilot.Playbook#subdirectory=.github/shared/skills/sql-injection-scanner
```

**After installation, use anywhere:**
```bash
sql-scanner scan-dir ./src
sql-scanner scan-repo https://dev.azure.com/Vancity/_git/MyRepo
sql-scanner scan-file database.py
```

### Option 2: Use from Source (For Development)

```bash
# Clone and install dependencies
git clone https://dev.azure.com/Vancity/Vancity/_git/IS.Copilot.Playbook
cd IS.Copilot.Playbook/.github/shared/skills/sql-injection-scanner
pip install -r requirements.txt

# Use with python
python cli.py scan-dir ./src
```

### Option 3: Azure DevOps Pipeline (For CI/CD)

Add to your project's `azure-pipelines.yml` - **no installation needed!**

```yaml
resources:
  repositories:
    - repository: playbook
      type: git
      name: Vancity/IS.Copilot.Playbook

extends:
  template: .github/shared/skills/sql-injection-scanner/pipeline-template.yml@playbook
```

See [CI/CD Integration](#cicd-integration) section for details.

## Usage

### Command Line Interface

#### Scan a Single File
```bash
# If installed via pip
sql-scanner scan-file ./path/to/file.py

# If using from source
python cli.py scan-file ./path/to/file.py
```

#### Scan Directory
```bash
sql-scanner scan-dir ./src --recursive
```

#### Scan Azure DevOps Repository
```bash
sql-scanner scan-repo https://dev.azure.com/Vancity/Project/_git/RepoName --branch master
```

#### List Repository Branches
```bash
sql-scanner list-branches https://dev.azure.com/Vancity/Project/_git/RepoName
```

#### JSON Output
```bash
sql-scanner scan-file ./app.py --json
```

### Import in Python Code

```python
import asyncio
from tools import scan_file_handler, scan_repository_handler

# Scan a file
result = asyncio.run(scan_file_handler('./database.py'))
print(result)

# Scan Azure DevOps repo
result = asyncio.run(scan_repository_handler(
    'https://dev.azure.com/Vancity/Project/_git/MyRepo',
    branch='master'
))
print(result)
```

### Use in CI/CD Pipeline

#### Option 1: Use Reusable Template (Recommended)

Add this to **any project's azure-pipelines.yml**:

```yaml
# Reference the Playbook repository
resources:
  repositories:
    - repository: playbook
      type: git
      name: Vancity/IS.Copilot.Playbook

# Use the scanner template
extends:
  template: .github/shared/skills/sql-injection-scanner/pipeline-template.yml@playbook
  parameters:
    scanPath: '$(Build.SourcesDirectory)'
    failOnFindings: true
```

**That's it!** The template automatically:
- ✅ Checks out scanner code from Playbook repo
- ✅ Installs dependencies
- ✅ Scans your project
- ✅ Publishes results as artifacts
- ✅ Fails build if vulnerabilities found

See [azure-pipelines-example.yml](azure-pipelines-example.yml) for advanced configuration.

#### Option 2: Inline Scanner in Your Pipeline

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

resources:
  repositories:
    - repository: playbook
      type: git
      name: Vancity/IS.Copilot.Playbook

steps:
- checkout: self
- checkout: playbook

- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.12'

- script: |
    pip install -r $(Build.SourcesDirectory)/IS.Copilot.Playbook/.github/shared/skills/sql-injection-scanner/requirements.txt
    cd $(Build.SourcesDirectory)/IS.Copilot.Playbook/.github/shared/skills/sql-injection-scanner
    python cli.py scan-dir $(Build.SourcesDirectory)
  displayName: 'SQL Injection Security Scan'
```

## Available Tools

### scan_file_handler(file_path)
Scan a single source file for SQL injection vulnerabilities.

**Returns:** Dict with findings, severity, line numbers

### scan_directory_handler(directory_path, recursive=True)
Scan all source files in a directory.

**Returns:** Dict with aggregated findings across all files

### scan_repository_handler(repo_url, branch="main", auth_token=None)
Clone and scan a Git repository.

**Supports:** Azure DevOps, GitHub, GitLab, Bitbucket

**Returns:** Dict with scan results + repository metadata

### list_repository_branches_handler(repo_url, auth_token=None)
List all branches in a remote repository.

**Returns:** Dict with list of branch names

### check_repository_access_handler(repo_url, auth_token=None)
Verify repository access and permissions.

**Returns:** Dict with access status

## Detection Patterns

The scanner detects:

- ❌ String concatenation in SQL queries
- ❌ f-strings embedding variables in SQL
- ❌ `.format()` used in SQL construction
- ❌ `%` formatting in SQL queries
- ❌ Unparameterized `cursor.execute()` calls
- ❌ `exec()`, `executemany()`, `executescript()` with dynamic SQL
- ❌ ORM raw queries with injection risks

✅ Safe patterns:
- Parameterized queries (`?`, `:param`, `%(name)s`)
- ORM query builders
- Prepared statements

## Azure DevOps Authentication

**Windows Users:** Authentication happens automatically using your Windows credentials!

```bash
# Just run - no token needed
python cli.py scan-repo https://dev.azure.com/Vancity/_git/MyRepo
```

**Token (if needed):**
```bash
python cli.py scan-repo https://dev.azure.com/Vancity/_git/MyRepo --token YOUR_PAT
```

## Example Output

```
Scan Results:
Files scanned: 47
Issues found: 3

Findings:
  [HIGH] database.py:45
    String concatenation in execute()
  [MEDIUM] api.py:89
    f-string used in SQL query
  [HIGH] auth.py:120
    Unparameterized cursor.execute()
```

## Integration with GitHub Copilot

This skill includes [SKILL.md](../../shared/skills/sql-injection-scanner/SKILL.md) that teaches GitHub Copilot about SQL injection patterns.

**In Copilot Chat:**
```
You: "Scan this file for SQL injection"

Copilot: [Uses SKILL.md knowledge + suggests running tools]
"Run the scanner: python tools/cli.py scan-file yourfile.py"
```

## Testing

The scanner includes a comprehensive automated test suite in `run_tests.py`.

### Run All Tests
```bash
python run_tests.py
```

### Run Tests with Verbose Output
```bash
python run_tests.py --verbose
```

### Run Specific Test
```bash
python run_tests.py --test-id 1
```

### Generate HTML Report
```bash
python run_tests.py --report test-report.html
```

### Test Coverage

The test suite validates:

✅ **Python Vulnerable Code**: Detects string concatenation, f-strings  
✅ **JavaScript Vulnerable Code**: Detects template literals  
✅ **C# Vulnerable Code**: Detects string interpolation  
✅ **Directory Scanning**: Multi-file, multi-language scanning  
✅ **Safe Code Detection**: Zero false positives on parameterized queries  

### Expected Test Results

```
🔒 SQL Injection Scanner - Test Runner
Running 5 test(s)...

✅ Test #1: PASS
✅ Test #2: PASS
✅ Test #3: PASS
✅ Test #4: PASS
✅ Test #5: PASS

============================================================
TEST SUMMARY
============================================================
Total Tests:   5
✅ Passed:     5
❌ Failed:     0
⚠️  Errors:     0
Success Rate:  100.0%
Duration:      1.23s
============================================================
```

### CI/CD Integration

#### For Other Projects (Recommended)

Use the **reusable pipeline template** to scan any project without copying code:

**1. Create azure-pipelines.yml in your project:**
```yaml
resources:
  repositories:
    - repository: playbook
      type: git
      name: Vancity/IS.Copilot.Playbook

extends:
  template: .github/shared/skills/sql-injection-scanner/pipeline-template.yml@playbook
```

**2. Create pipeline in Azure DevOps:**
- Navigate to **Pipelines** → **New Pipeline**
- Select your repository
- Choose **Existing Azure Pipelines YAML file**
- Point to your azure-pipelines.yml
- Run!

**3. Results:**
- ✅ Automatic scanning on every commit
- ✅ Build artifacts with JSON results
- ✅ HTML test reports
- ✅ Build fails if vulnerabilities found

See [azure-pipelines-example.yml](azure-pipelines-example.yml) for advanced configuration examples.

#### For This Repository (Self-Testing)

The scanner includes `azure-pipelines.yml` for testing itself:

```yaml
# Tests the scanner code itself
trigger:
  - main
  - develop
  - feature/*

stages:
  - Test          # Run test suite (run_tests.py)
  - Validate      # Validate SKILL.md schema
  - SecurityScan  # Run Bandit security scan
  - Package       # Create distributable package
```

This is for development/testing of the scanner itself, not for scanning other projects.

## Related Documentation

- [SKILL.md](../../shared/skills/sql-injection-scanner/SKILL.md) - GitHub Copilot skill definition
- [Shared README](../../shared/skills/sql-injection-scanner/README.md) - General documentation

---

## Troubleshooting

### Authentication Issues
**Problem**: Repository clone fails with authentication error  
**Solution**: Use Personal Access Token with `--token YOUR_PAT`

### Performance
**Problem**: Large repos scan slowly  
**Solution**: Use file pattern filtering: `--file-patterns "*.py" "*.js"`

### False Positives  
Review severity ratings: CRITICAL = user input, MEDIUM = needs context review

---

## License

Internal use only - Vancity Credit Union
