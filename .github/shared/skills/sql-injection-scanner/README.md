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

```bash
# Install dependencies
pip install -r requirements.txt

# Or use the tools directly (no installation needed)
cd IS.Copilot.Playbook/.github/python/skills/sql-injection-scanner
```

## Usage

### Command Line Interface

#### Scan a Single File
```bash
python cli.py scan-file ./path/to/file.py
```

#### Scan Directory
```bash
python cli.py scan-dir ./src --recursive
```

#### Scan Azure DevOps Repository
```bash
python cli.py scan-repo https://dev.azure.com/Vancity/Project/_git/RepoName --branch master
```

#### List Repository Branches
```bash
python cli.py list-branches https://dev.azure.com/Vancity/Project/_git/RepoName
```

#### JSON Output
```bash
python cli.py scan-file ./app.py --json
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

#### Azure DevOps Pipeline
```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.12'

- script: |
    pip install -r .github/python/skills/sql-injection-scanner/requirements.txt
    python .github/python/skills/sql-injection-scanner/cli.py scan-dir $(Build.SourcesDirectory)
  displayName: 'Security Scan'
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

## Related Documentation

- [SKILL.md](../../shared/skills/sql-injection-scanner/SKILL.md) - GitHub Copilot skill definition
- [Shared README](../../shared/skills/sql-injection-scanner/README.md) - General documentation

## License

Internal use only - Vancity Credit Union
