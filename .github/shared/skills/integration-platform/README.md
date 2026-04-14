# Integration Platform MCP Server

A unified Model Context Protocol (MCP) server providing comprehensive security scanning and repository analysis tools for the Integration Services team.

## Overview

The Integration Platform consolidates multiple development tools into a single MCP server, following the same one-server, multi-tool pattern used by Azure MCP servers. This provides a streamlined experience in GitHub Copilot and VS Code.

**Key Features:**
- ✅ **SQL Injection Scanning** - In-process Python AST + multi-language regex detection
- ✅ **Repository Analysis** - Clone and scan remote Git repositories (Azure DevOps, GitHub, GitLab, Bitbucket)
- ✅ **HTML Reporting** - Generate styled security reports
- ✅ **Multi-Language Support** - Python, JavaScript, TypeScript, C#, Java, PHP, SQL
- ✅ **CWE + Severity Output** - CWE-89/CWE-564 with CRITICAL/HIGH/MEDIUM/LOW scoring
- ✅ **Windows Authentication** - Works with Azure DevOps (no token needed!)
- ✅ **Security Scanner** - In-process static security checks across common source/config files
- ✅ **Test Generator** - C# test stub generation with xUnit, NUnit, and MSTest support
- ✅ **Security Pipeline** - End-to-end orchestrator: clone → SQL scan → security scan → fix suggestions → HTML report → PR

## Available Tools

### 1. `sql_scanner`
Module tool for SQL scanning and report generation.

Supported `action` values:
- `scan_sql_injection_file`
- `scan_sql_injection_directory`
- `check_parameterized_query`
- `generate_scan_report`
- `generate_html_report`

Example:
```json
{
  "name": "sql_scanner",
  "arguments": {
    "action": "scan_sql_injection_file",
    "file_path": "c:\\projects\\myapp\\database.py"
  }
}
```

### 2. `repo_analyzer`
Module tool for repository analysis.

Supported `action` values:
- `scan_repository`
- `list_repository_branches`
- `check_repository_access`

Example:
```json
{
  "name": "repo_analyzer",
  "arguments": {
    "action": "scan_repository",
    "repo_url": "https://dev.azure.com/Vancity/Project/_git/MyRepo",
    "branch": "master",
    "scan_type": "security"
  }
}
```

### 3. `scan_security`
Module tool for broader security scanning.

Supported `action` values:
- `scan_path`
- `list_profiles`
- `generate_report`
- `generate_html_report`

Input arguments for `scan_path`:
- `target_path` (required) - File or directory path to scan
- `recursive` (optional) - Recursively scan subdirectories (default: `true`)
- `profile` (optional) - Scan profile: `quick`, `full`, or `secrets`

Profile behavior:
- `quick` - Higher-signal checks for secrets, injection, command execution, deserialization, TLS verification, and auth issues
- `full` - Everything in `quick` plus broader checks such as weak crypto usage and DOM XSS sinks
- `secrets` - Hardcoded credentials and private key material only

Input arguments for `generate_report`:
- `findings` (required) - Findings array returned by `scan_path`
- `output_format` (optional) - `text`, `json`, or `summary`

Input arguments for `generate_html_report`:
- `findings` (required) - Findings array returned by `scan_path`
- `output_file` (required) - HTML output file path
- `scan_path` (optional) - Display label for the scanned target

The scanner reports findings with:
- `severity` (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
- `cwe` mappings where applicable
- `category` (for example: `secrets`, `injection`, `crypto`, `xss`)

Example:
```json
{
  "name": "scan_security",
  "arguments": {
    "action": "scan_path",
    "target_path": "c:\\projects\\myapp\\src",
    "profile": "quick"
  }
}
```

### 4. `test_generator`
Module tool for ecosystem-aware test generation.

Supported `action` values:
- `list_frameworks`
- `analyze_source`
- `generate_test_stub`

Current ecosystem support:
- `csharp`
- `python`

Current C# frameworks:
- `xunit`
- `nunit`
- `mstest`

Current Python frameworks:
- `pytest`
- `unittest`

Example:
```json
{
  "name": "test_generator",
  "arguments": {
    "action": "generate_test_stub",
    "ecosystem": "csharp",
    "framework": "xunit",
    "source_path": "c:\\projects\\myapp\\Services\\OrderService.cs"
  }
}
```

### 5. `pipeline`
End-to-end security pipeline orchestrator. Clones a repository, runs both SQL and security scans, generates fix suggestions (as unified diffs), produces an HTML report, and optionally pushes a fix branch and creates a pull request.

Supported `action` values:
- `dry_run` — Scan + report only. No git push, no PR created.
- `run` — Full pipeline: scan + apply fixes + push branch + create PR (GitHub or Azure DevOps auto-detected from URL).

Input arguments:
| Argument | Required | Description |
|----------|----------|-------------|
| `action` | Yes | `dry_run` or `run` |
| `repo_url` | Yes | HTTPS repository URL |
| `branch` | No | Branch to scan (default: repository default branch) |
| `auth_token` | For `run` / private repos | PAT with repo read+write scope |
| `base_branch` | No | PR target branch (default: `main`) |
| `scan_profile` | No | `quick` (default), `full`, or `secrets` |
| `pr_title` | No | Override auto-generated PR title |
| `pr_body` | No | Extra text appended to PR description |

Response fields:
| Field | Description |
|-------|-------------|
| `total_findings` | Total number of issues found |
| `sql_findings_count` | Issues from SQL injection scanner |
| `security_findings_count` | Issues from security scanner |
| `fix_suggestions` | List of per-finding fix suggestions with diffs |
| `combined_patch` | Single unified diff (apply with `git apply`) |
| `stats` | `{auto_fixable, suggestion_only}` counts |
| `html_report` | Inline HTML report (can be saved to `.html`) |
| `pr_url` | PR URL (`run` mode only) |
| `branch_name` | Pushed branch name (`run` mode only) |

**Auto-fix transforms** (applied for `run` mode):
- `yaml.load(` → `yaml.safe_load(` — CWE-502 unsafe deserialization
- `requests(... verify=False)` → remove `verify=False` — CWE-295 TLS bypass
- Security comment markers added above `pickle`, weak hash, and credential usage

**Manual review required** (documented but never auto-fixed):
- SQL injection (CWE-89) — requires parameterized query refactoring

Example — dry run:
```json
{
  "name": "pipeline",
  "arguments": {
    "action": "dry_run",
    "repo_url": "https://github.com/myorg/myrepo.git",
    "scan_profile": "quick"
  }
}
```

Example — full run with PR:
```json
{
  "name": "pipeline",
  "arguments": {
    "action": "run",
    "repo_url": "https://dev.azure.com/myorg/myproj/_git/myrepo",
    "auth_token": "<PAT>",
    "base_branch": "main",
    "scan_profile": "full"
  }
}
```

### Interactive agent: `security-pipeline`

The agent is at `.github/agents/security-pipeline.agent.md` — VS Code discovers it automatically from that location. Invoke it from GitHub Copilot Chat by selecting **security-pipeline** from the agent picker, or by typing `@security-pipeline` in the chat input.

#### Pipeline tool vs. agent — what's the difference?

Both the `pipeline` MCP tool and the `security-pipeline` agent call the same underlying `run_pipeline()` code and produce identical results. The difference is the experience:

| | `pipeline` tool (direct) | `security-pipeline` agent |
|---|---|---|
| **Input** | All parameters supplied upfront in one call | Guides you interactively, asks clarifying questions |
| **Output** | Raw JSON | Formatted markdown — severity cards, top-5 findings explained, next steps |
| **Workflow guidance** | None | Suggests `dry_run` first, explains what each step does |
| **Safety guardrails** | None | Never echoes auth token; flags SQL injection as manual-fix only |
| **Best for** | Scripting / automation where you already know all args | Interactive use, first-time runs, reviewing results |

**Rule of thumb:** use the agent for interactive exploration and the tool directly when calling from a script or another tool.

## Installation

### Automatic Setup (Recommended)

Run the global setup script from the repository root:

```powershell
.\setup-global-mcp-servers.ps1
```

This will:
- ✅ Auto-discover the Integration Platform server
- ✅ Configure it in your `mcp.json` with display name "Integration Platform"  
- ✅ Setup Python environment and dependencies

### Manual Setup

1. **Configure VS Code MCP** - Edit `C:\Users\[username]\AppData\Roaming\Code\User\mcp.json`:

```json
{
  "servers": {
    "Integration Platform": {
      "command": "C:/Python312/python.exe",
      "args": [
        "c:\\Users\\[username]\\source\\repos\\IS.Copilot.Playbook\\.github\\shared\\skills\\integration-platform\\integration_platform_mcp_server.py"
      ],
      "env": {}
    }
  }
}
```

2. **Install Dependencies**:

```bash
cd .github/shared/skills/integration-platform
pip install -r requirements.txt
```

**Required packages:**
- `GitPython>=3.1.40` - For repository operations

## Usage

### Using MCP Tools in GitHub Copilot and VS Code

After configuration, the tools are available through the MCP interface:

**Example MCP call: sql_scanner (scan file)**
```json
{
  "name": "sql_scanner",
  "arguments": {
    "action": "scan_sql_injection_file",
    "file_path": "c:\\projects\\myapp\\database.py"
  }
}
```

**Example MCP call: repo_analyzer (scan repository)**
```json
{
  "name": "repo_analyzer",
  "arguments": {
    "action": "scan_repository",
    "repo_url": "https://dev.azure.com/Vancity/_git/MyRepo",
    "branch": "main",
    "scan_type": "security"
  }
}
```

**Example 1: Scan a single file**
```
"Scan this file for SQL injection vulnerabilities: 
c:\projects\myapp\database.py"
```

**Example 2: Scan entire directory**
```
"Scan the entire c:\projects\myapp\src directory for SQL injection issues"
```

**Example 3: Scan Azure DevOps repository**
```
"Scan the repository at https://dev.azure.com/Vancity/_git/MyRepo for security issues"
```

### Using the Command Line Interface

The Integration Platform includes a powerful CLI for standalone use:

#### Scan Commands

**Scan a single file:**
```bash
python cli.py scan-file ./path/to/file.py
python cli.py scan-file database.py --json
python cli.py scan-file app.py --html report.html
```

**Scan directory:**
```bash
python cli.py scan-dir ./src --recursive
python cli.py scan-dir ./app --json
python cli.py scan-dir ./src --html security-report.html
```

**Check parameterized queries:**
```bash
python cli.py check-params "SELECT * FROM users WHERE id = ?"
python cli.py check-params "SELECT * FROM users WHERE id = {user_id}" --json
```

#### Repository Commands

**Scan remote repository:**
```bash
# Azure DevOps (Windows authentication)
python cli.py scan-repo https://dev.azure.com/Vancity/_git/MyRepo --branch master

# GitHub with token
python cli.py scan-repo https://github.com/user/repo --token YOUR_PAT

# With HTML report
python cli.py scan-repo https://dev.azure.com/Vancity/_git/MyRepo --html repo-scan.html
```

**List repository branches:**
```bash
python cli.py list-branches https://dev.azure.com/Vancity/_git/MyRepo
python cli.py list-branches https://github.com/user/repo --token YOUR_PAT
```

**Check repository access:**
```bash
python cli.py check-access https://dev.azure.com/Vancity/_git/MyRepo
python cli.py check-access https://github.com/user/repo --token YOUR_TOKEN
```

### Import in Python Code

```python
from tools.sql_scanner import (
    scan_sql_injection_file,
    scan_sql_injection_directory,
    check_parameterized_query,
    generate_html_report
)
from tools.repo_analyzer import (
    scan_repository,
    list_repository_branches,
    check_repository_access
)

# Scan a file
result = scan_sql_injection_file({"file_path": "./database.py"})
print(result)

# Scan a repository
result = scan_repository({
    "repo_url": "https://dev.azure.com/Vancity/Project/_git/MyRepo",
    "branch": "master",
    "scan_type": "security"
})
print(result)

# List branches
branches = list_repository_branches({"repo_url": "https://dev.azure.com/Vancity/_git/MyRepo"})
print(branches)
```

## Detection Patterns

The scanner detects common SQL injection vulnerabilities:

### ❌ Vulnerable Patterns

- String concatenation in SQL queries: `"SELECT * WHERE id = " + user_id`
- f-strings embedding variables: `f"SELECT * WHERE id = {user_id}"`
- `.format()` in SQL construction: `"SELECT * WHERE id = {}".format(user_id)`
- `%` formatting in SQL: `"SELECT * WHERE id = %s" % user_id`
- Template literals in JavaScript: `` `SELECT * WHERE id = ${userId}` ``
- String interpolation in C#: `$"SELECT * WHERE id = {userId}"`
- Unparameterized `cursor.execute()`, `exec()`, `executemany()` calls
- ORM raw queries with injection risks
- SQL injection indicator payloads like `OR 1=1`, `UNION SELECT`, `SLEEP()`, `WAITFOR DELAY`, and stacked DDL patterns

All findings include severity and CWE mapping (`CWE-89`, `CWE-564` where applicable).

### ✅ Safe Patterns

- Parameterized queries with placeholders: `?`, `:param`, `%(name)s`
- ORM query builders (Django ORM, SQLAlchemy, Entity Framework)
- Prepared statements with parameter binding
- Properly escaped stored procedures

## Azure DevOps Authentication

**Windows Users:** Authentication happens automatically using your Windows credentials!

```bash
# Just run - no token needed for Azure DevOps on Windows
python cli.py scan-repo https://dev.azure.com/Vancity/_git/MyRepo
python cli.py list-branches https://dev.azure.com/Vancity/_git/MyRepo
```

**Personal Access Token (if needed):**
```bash
python cli.py scan-repo https://dev.azure.com/Vancity/_git/MyRepo --token YOUR_PAT
```

## Example Output

### Console Output
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

### HTML Report Output

The HTML report includes:
- ✅ Modern responsive design with CSS styling
- ✅ Executive summary with statistics
- ✅ Findings grouped by severity (Critical, High, Medium, Low)
- ✅ Color-coded severity indicators
- ✅ File paths and line numbers
- ✅ Code snippets and recommendations
- ✅ Timestamp and scan metadata

## Testing Examples

The `examples/` directory contains both vulnerable and safe code patterns:

**Vulnerable examples** (`examples/vulnerable/`):
- `python_concatenation.py` - String concatenation patterns
- `javascript_template_literal.js` - Template literal injection

**Safe examples** (`examples/safe/`):
- `python_parameterized.py` - Proper parameterized queries
- `javascript_parameterized.js` - Safe parameter binding

**Evaluation files** (`evals/test_files/`):
- Test cases for validating scanner accuracy
- Multi-language vulnerability samples
- False positive test cases

## Architecture

```
integration-platform/
├── integration_platform_mcp_server.py  # Main MCP server (5 module tools)
├── cli.py                              # Command-line interface
├── requirements.txt                    # Python dependencies (GitPython)
├── README.md                           # This file
├── tools/
│   ├── sql_scanner.py                  # SQL injection scanning engine
│   ├── repo_analyzer.py                # Repository analysis engine
│   ├── security_scanner.py             # Broad static security scanner
│   ├── test_generator.py               # Ecosystem-aware test generator
│   ├── auto_fixer.py                   # Fix suggestion + unified diff generator
│   ├── pr_creator.py                   # Branch push + PR creator (GitHub / AzDO)
│   └── pipeline.py                     # End-to-end orchestrator
├── tests/
│   ├── test_auto_fixer.py              # 33 tests
│   ├── test_pr_creator.py              # 30 tests
│   ├── test_pipeline.py                # 32 tests
│   └── test_test_generator.py          # 5 tests
├── examples/
│   ├── README.md                       # Usage examples documentation
│   ├── safe/                           # Safe code patterns
│   │   ├── python_parameterized.py
│   │   └── javascript_parameterized.js
│   └── vulnerable/                     # Vulnerable code patterns
│       ├── python_concatenation.py
│       └── javascript_template_literal.js
└── evals/
    ├── evals.json                      # Evaluation definitions
    └── test_files/                     # Test cases
        ├── python_vulnerable.py
        ├── python_safe.py
        ├── javascript_vulnerable.js
        └── csharp_vulnerable.cs
```

## Roadmap

### ✅ Completed (v1.0)
- SQL injection scanning (file, directory, repository)
- Repository cloning and analysis
- Multi-language support (Python, JavaScript, TypeScript, C#, Java, PHP)
- HTML report generation
- Command-line interface
- MCP integration
- Windows authentication for Azure DevOps
- In-process Python AST scanning (no external scanner subprocess)
- CWE mapping and severity-based reporting

### ✅ Completed (v1.1)
- End-to-end security pipeline (`pipeline` tool)
  - Auto-fix transforms: `yaml.load→yaml.safe_load` (CWE-502), `verify=False` removal (CWE-295), security comment markers
  - Unified diff / patch output for all findings
  - Inline HTML report per run
  - GitHub + Azure DevOps PR creation (auto-detected from URL)
- `security-pipeline` interactive agent for guided pipeline runs
- 100 unit tests across all tool modules

### 🚧 In Progress
- Additional ecosystem support in test_generator
- Advanced code quality metrics

### 📋 Planned
- OWASP Top 10 vulnerability scanning
- Performance profiling integration
- Integration with Azure Pipelines
- GitHub Actions support
- Custom rule engine

## Contributing

To extend the Integration Platform:

1. **Add a new tool module** in `tools/` directory
2. **Implement MCP tool handlers** with signature: `def tool_name(args: Dict[str, Any]) -> Dict[str, Any]`
3. **Register the tool** in `integration_platform_mcp_server.py`:
   - Import the handler
   - Add tool definition to `self.tools` dictionary
   - Define input schema (JSON Schema format)
4. **Add CLI command** in `cli.py` (optional, for standalone use)
5. **Update README.md** with tool documentation

## Development

### Adding a New Tool

1. Create tool handler in `tools/new_tool.py`:
```python
def my_new_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    # Implementation
    return {"result": "success"}
```

2. Import and register in `integration_platform_mcp_server.py`:
```python
from tools.new_tool import my_new_tool

self.tools["my_new_tool"] = {
    "description": "Description of what it does",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "Parameter description"}
        },
        "required": ["param1"]
    },
    "handler": my_new_tool
}
```

### Testing

Test individual tools:
```python
from tools.sql_scanner import scan_sql_injection_file

result = scan_sql_injection_file({"file_path": "test.py"})
print(result)
```

## Migration Note

This platform is the current home for SQL injection scanning and repository analysis capabilities.

## Support

For issues or feature requests, contact the Integration Services team.

## Version History

- **v1.1.0** (Current)
  - `pipeline` tool: end-to-end clone → scan → fix → report → PR orchestrator
  - `auto_fixer`: unified diff generator with safe mechanical transforms
  - `pr_creator`: branch push + GitHub / Azure DevOps PR creation
  - `security-pipeline.agent.md`: guided interactive agent
  - 100 unit tests (all passing)

- **v1.0.0**
  - Initial unified platform release
  - SQL injection scanning (migrated from standalone server)
  - Security scanning and C# test generation added to the unified tool surface

## License

Internal use for Integration Services team
