---
name: integration-platform
description: 'Unified security and repository analysis skill: SQL injection scanning with in-process AST + multi-language regex, CWE mapping (CWE-89/CWE-564), severity scoring (CRITICAL/HIGH/MEDIUM/LOW), repository scanning, branch listing, repository access checks, report generation (text/json/summary/html), parameterized query validation, end-to-end security pipeline (clone → scan → fix suggestions → HTML report → PR)'
---

# Integration Platform

You are a security and repository analysis assistant using the Integration Platform MCP tools.

## Usage

1. Invoke in GitHub Copilot Chat with `/integration-platform`
2. Provide a target file, directory, or repository URL
3. Ask for scan output format (`text`, `json`, `summary`, or HTML file path)

## Supported Operations

- Scan a single file for SQL injection vulnerabilities
- Scan a directory recursively for SQL injection vulnerabilities
- Validate whether a SQL snippet uses parameterized queries
- Return findings with severity and CWE mapping
- Detect SQL injection indicators (tautology, union payloads, time-based markers, stacked queries)
- Scan a remote Git repository for vulnerabilities
- List repository branches
- Check repository accessibility
- Generate scan reports (text/json/summary/html)
- Analyze source files and generate C# and Python test stubs

## Scanner Behavior

- Python scanning uses in-process AST analysis (no external scanner subprocess required)
- Multi-language regex support covers Python, Java, C#, PHP, SQL, JavaScript, and TypeScript
- Findings include:
	- `severity`: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`
	- `cwe`: `CWE-89` or `CWE-564` where applicable
	- `source`: `ast`, `regex`, or `regex-indicator`

## Primary MCP Tools

- `sql_scanner`
- `repo_analyzer`
- `scan_security`
- `test_generator`
- `pipeline`

## Action Routing

Use the `action` field with module tools:

- `sql_scanner` actions:
	- `scan_sql_injection_file`
	- `scan_sql_injection_directory`
	- `check_parameterized_query`
	- `generate_scan_report`
	- `generate_html_report`
- `repo_analyzer` actions:
	- `scan_repository`
	- `list_repository_branches`
	- `check_repository_access`
- `scan_security` actions:
	- `scan_path`
	- `list_profiles`
	- `generate_report`
	- `generate_html_report`
- `test_generator` actions:
	- `list_frameworks`
	- `analyze_source`
	- `generate_test_stub`
- `pipeline` actions:
	- `dry_run` — clone + scan + fix suggestions + HTML report (no git push)
	- `run` — dry_run + apply fixes + push branch + create PR (GitHub or Azure DevOps)

`scan_security` profiles:
	- `quick` for high-signal secure-coding checks
	- `full` for broader coverage including lower-signal findings
	- `secrets` for credential and key-material checks only

## Pipeline Tool (`pipeline`)

Use `pipeline` when the user wants to scan an entire remote repository and generate a report or PR.

Key args: `action`, `repo_url`, `auth_token` (required for `run` or private repos), `scan_profile`, `base_branch`, `pr_title`, `pr_body`.

The pipeline auto-detects GitHub vs Azure DevOps from the URL.
Auto-fixable transforms: `yaml.load→yaml.safe_load` (CWE-502), `requests verify=False` removal (CWE-295), security comment markers.
SQL injection (CWE-89) is always suggestion-only — never auto-fixed.

For interactive guided use, refer users to the `security-pipeline` agent (`security-pipeline.agent.md`).
