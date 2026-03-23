"""
Security Tools - SQL Injection scanning tools
Standalone version for command-line usage
"""

from typing import Dict, Any, List, Optional
import os
import re
import json
import subprocess
import ast


# ============================================================================
# Helper Functions
# ============================================================================

# Regex patterns that indicate unsafe SQL construction
SQLI_PATTERNS = [
    (r'execute\s*\(\s*["\'].*\+', "String concatenation in execute()"),
    (r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE|WHERE).*\{', "f-string used in SQL query"),
    (r'".*(?:SELECT|INSERT|UPDATE|DELETE).*"\s*%\s*', "%-format used in SQL query"),
    (r'\.format\(.*\).*(?:SELECT|INSERT|UPDATE|DELETE)', ".format() used in SQL query"),
    (r'cursor\.execute\(\s*["\'][^,)]*\+', "String concat passed directly to cursor.execute"),
    (r'(?:SELECT|INSERT|UPDATE|DELETE)[^;]*\+\s*\w+', "Variable concatenated into SQL string"),
]

SUPPORTED_EXTENSIONS = {'.py', '.js', '.ts', '.sql', '.cs', '.java', '.php'}


def _scan_code_with_regex(code: str, filename: str) -> List[Dict[str, Any]]:
    """
    Scan source code lines for SQL injection patterns using regex.
    Returns list of findings with line numbers and severity.
    """
    findings = []
    lines = code.splitlines()
    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('//'):
            continue
        for pattern, description in SQLI_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                findings.append({
                    "file": filename,
                    "line": line_num,
                    "code_snippet": line.strip(),
                    "issue": description,
                    "severity": "HIGH",
                    "recommendation": "Use parameterized queries or an ORM instead of string construction."
                })
                break  # One finding per line
    return findings


# ============================================================================
# Tool Handlers
# ============================================================================

async def scan_file_handler(
    file_path: str
) -> Dict[str, Any]:
    """
    Scan a single source file for SQL injection vulnerabilities.

    Uses both regex pattern matching and bandit (if available).
    Returns findings with file name, line number, code snippet, and recommendation.
    """
    try:
        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}", "findings": []}

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return {
                "success": True,
                "file": file_path,
                "skipped": True,
                "reason": f"Unsupported file type: {ext}",
                "findings": []
            }

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()

        findings = _scan_code_with_regex(code, file_path)

        # Also run bandit for Python files
        bandit_findings = []
        if ext == '.py':
            try:
                result = subprocess.run(
                    ['bandit', '-r', file_path, '-t', 'B608', '-f', 'json', '-q'],
                    capture_output=True, text=True, timeout=30
                )
                if result.stdout:
                    bandit_output = json.loads(result.stdout)
                    for issue in bandit_output.get('results', []):
                        bandit_findings.append({
                            "file": issue.get('filename', file_path),
                            "line": issue.get('line_number', 0),
                            "code_snippet": issue.get('code', '').strip(),
                            "issue": issue.get('issue_text', ''),
                            "severity": issue.get('issue_severity', 'MEDIUM').upper(),
                            "recommendation": "Use parameterized queries or SQLAlchemy ORM.",
                            "source": "bandit"
                        })
            except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, PermissionError, OSError):
                pass  # bandit not installed, timed out, or access denied — regex results still returned

        all_findings = findings + bandit_findings

        return {
            "success": True,
            "file": file_path,
            "total_findings": len(all_findings),
            "findings": all_findings,
            "is_clean": len(all_findings) == 0
        }

    except Exception as e:
        return {"success": False, "error": str(e), "findings": []}


async def scan_directory_handler(
    directory_path: str,
    recursive: bool = True
) -> Dict[str, Any]:
    """
    Scan all supported source files in a directory for SQL injection vulnerabilities.
    Returns a consolidated report with findings grouped by file.
    """
    try:
        if not os.path.exists(directory_path):
            return {"success": False, "error": f"Directory not found: {directory_path}", "findings": []}

        if not os.path.isdir(directory_path):
            return {"success": False, "error": f"Path is not a directory: {directory_path}", "findings": []}

        all_findings = []
        files_scanned = []
        files_skipped = []

        if recursive:
            file_iter = (
                os.path.join(root, f)
                for root, _, files in os.walk(directory_path)
                for f in files
            )
        else:
            file_iter = (
                os.path.join(directory_path, f)
                for f in os.listdir(directory_path)
                if os.path.isfile(os.path.join(directory_path, f))
            )

        for file_path in file_iter:
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                files_skipped.append(file_path)
                continue

            # Skip virtual environments and cache dirs
            parts = file_path.replace('\\', '/').split('/')
            if any(p in parts for p in ['venv', '.venv', '__pycache__', 'node_modules', '.git']):
                files_skipped.append(file_path)
                continue

            result = await scan_file_handler(file_path)
            files_scanned.append(file_path)
            if result.get('findings'):
                all_findings.extend(result['findings'])

        # Group by severity
        critical = [f for f in all_findings if f['severity'] == 'CRITICAL']
        high = [f for f in all_findings if f['severity'] == 'HIGH']
        medium = [f for f in all_findings if f['severity'] == 'MEDIUM']

        return {
            "success": True,
            "directory": directory_path,
            "files_scanned": len(files_scanned),
            "files_skipped": len(files_skipped),
            "total_findings": len(all_findings),
            "summary": {
                "critical": len(critical),
                "high": len(high),
                "medium": len(medium)
            },
            "is_clean": len(all_findings) == 0,
            "findings": all_findings
        }

    except Exception as e:
        return {"success": False, "error": str(e), "findings": []}


async def check_parameterized_handler(
    code_snippet: str
) -> Dict[str, Any]:
    """
    Check whether a SQL code snippet uses safe parameterized queries.

    Returns whether it's safe, the detected style, and a recommendation if unsafe.
    """
    try:
        safe_patterns = [
            (r'\?',                         "Positional placeholder (?)"),
            (r':\w+',                        "Named placeholder (:param)"),
            (r'%\s*\(',                      "PyFormat style %(name)s"),
            (r'\$\d+',                       "Numbered placeholder ($1)"),
            (r'\.filter\(|\.where\(|\.query\(', "ORM-style (SQLAlchemy / Django)"),
        ]

        unsafe_patterns = [
            (r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE)', "f-string SQL"),
            (r'["\'].*\+\s*\w',              "String concatenation"),
            (r'\.format\(.*\)',              ".format() interpolation"),
            (r'%\s*[^\(]',                   "%-format without tuple"),
        ]

        detected_safe = []
        detected_unsafe = []

        for pattern, label in safe_patterns:
            if re.search(pattern, code_snippet, re.IGNORECASE):
                detected_safe.append(label)

        for pattern, label in unsafe_patterns:
            if re.search(pattern, code_snippet, re.IGNORECASE):
                detected_unsafe.append(label)

        is_safe = bool(detected_safe) and not detected_unsafe

        return {
            "success": True,
            "is_safe": is_safe,
            "safe_patterns_found": detected_safe,
            "unsafe_patterns_found": detected_unsafe,
            "verdict": "✅ Safe — uses parameterized queries" if is_safe else "❌ Unsafe — vulnerable to SQL injection",
            "recommendation": (
                None if is_safe else
                "Replace string construction with parameterized queries:\n"
                "  cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))\n"
                "  or use an ORM like SQLAlchemy."
            )
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def generate_report_handler(
    findings: List[Dict[str, Any]],
    output_format: str = "text"
) -> Dict[str, Any]:
    """
    Generate a human-readable security report from scan findings.

    output_format: 'text' | 'json' | 'summary'
    """
    try:
        if not findings:
            report = "✅ No SQL injection vulnerabilities found. Code is clean."
            return {"success": True, "report": report, "total": 0}

        critical = [f for f in findings if f.get('severity') == 'CRITICAL']
        high     = [f for f in findings if f.get('severity') == 'HIGH']
        medium   = [f for f in findings if f.get('severity') == 'MEDIUM']
        other    = [f for f in findings if f.get('severity') not in ('CRITICAL', 'HIGH', 'MEDIUM')]

        if output_format == "json":
            return {"success": True, "report": json.dumps(findings, indent=2), "total": len(findings)}

        if output_format == "summary":
            report = (
                f"🔒 SQL Injection Scan Summary\n"
                f"{'='*40}\n"
                f"Total findings : {len(findings)}\n"
                f"  🔴 CRITICAL  : {len(critical)}\n"
                f"  🟠 HIGH      : {len(high)}\n"
                f"  🟡 MEDIUM    : {len(medium)}\n"
                f"  ⚪ OTHER     : {len(other)}\n"
            )
            return {"success": True, "report": report, "total": len(findings)}

        # Full text report
        lines = [
            "🔒 SQL Injection Security Report",
            "=" * 50,
            f"Total vulnerabilities found: {len(findings)}",
            f"  🔴 CRITICAL: {len(critical)}  🟠 HIGH: {len(high)}  🟡 MEDIUM: {len(medium)}",
            ""
        ]

        for severity, group, icon in [
            ("CRITICAL", critical, "🔴"),
            ("HIGH",     high,     "🟠"),
            ("MEDIUM",   medium,   "🟡"),
            ("OTHER",    other,    "⚪"),
        ]:
            if group:
                lines.append(f"{icon} {severity} ({len(group)} issues)")
                lines.append("-" * 40)
                for f in group:
                    lines.append(f"  File   : {f.get('file', 'unknown')}")
                    lines.append(f"  Line   : {f.get('line', '?')}")
                    lines.append(f"  Issue  : {f.get('issue', '')}")
                    lines.append(f"  Code   : {f.get('code_snippet', '')}")
                    lines.append(f"  Fix    : {f.get('recommendation', '')}")
                    lines.append("")

        return {"success": True, "report": "\n".join(lines), "total": len(findings)}

    except Exception as e:
        return {"success": False, "error": str(e), "report": ""}


# ============================================================================
# Agent Framework Integration
# ============================================================================
# Note: FunctionTool definitions for agent-framework-github-copilot integration
# have been removed from this standalone CLI version.
#
# For agent framework usage, use the handler functions directly:
# - scan_file_handler, scan_directory_handler, check_parameterized_handler, generate_report_handler
