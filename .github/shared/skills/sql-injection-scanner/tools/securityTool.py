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
                    capture_output=True, text=True, timeout=5, check=False
                )
                if result.returncode == 0 and result.stdout:
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
            except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, PermissionError, OSError, Exception):
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


async def generate_html_report_handler(
    findings: List[Dict[str, Any]],
    output_file: str,
    scan_path: str = "."
) -> Dict[str, Any]:
    """
    Generate an HTML security report from scan findings.
    
    Args:
        findings: List of vulnerability findings
        output_file: Path to write HTML report
        scan_path: Path that was scanned (for display)
    
    Returns:
        Dict with success status and output file path
    """
    try:
        from datetime import datetime
        
        total = len(findings)
        critical = [f for f in findings if f.get('severity') == 'CRITICAL']
        high = [f for f in findings if f.get('severity') == 'HIGH']
        medium = [f for f in findings if f.get('severity') == 'MEDIUM']
        low = [f for f in findings if f.get('severity') == 'LOW']
        
        # Group findings by file
        by_file = {}
        for f in findings:
            file_path = f.get('file', 'unknown')
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(f)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SQL Injection Security Scan Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{ 
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
        }}
        header h1 {{ font-size: 32px; margin-bottom: 10px; }}
        header .meta {{ opacity: 0.9; font-size: 14px; }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #6c757d;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .summary-card.total {{ border-left-color: #007bff; }}
        .summary-card.critical {{ border-left-color: #dc3545; }}
        .summary-card.high {{ border-left-color: #fd7e14; }}
        .summary-card.medium {{ border-left-color: #ffc107; }}
        .summary-card.low {{ border-left-color: #17a2b8; }}
        .summary-value {{ font-size: 36px; font-weight: bold; color: #333; }}
        .summary-label {{ font-size: 14px; color: #6c757d; margin-top: 5px; }}
        
        .content {{ padding: 30px; }}
        .file-section {{
            margin-bottom: 30px;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            overflow: hidden;
        }}
        .file-header {{
            background: #343a40;
            color: white;
            padding: 15px 20px;
            font-family: 'Consolas', monospace;
            font-size: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .file-path {{ font-weight: bold; }}
        .finding-count {{ 
            background: rgba(255,255,255,0.2);
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
        }}
        
        .finding {{
            padding: 20px;
            border-bottom: 1px solid #e9ecef;
            background: white;
        }}
        .finding:last-child {{ border-bottom: none; }}
        .finding:hover {{ background: #f8f9fa; }}
        
        .finding-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }}
        .severity {{
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .severity.critical {{ background: #dc3545; color: white; }}
        .severity.high {{ background: #fd7e14; color: white; }}
        .severity.medium {{ background: #ffc107; color: #000; }}
        .severity.low {{ background: #17a2b8; color: white; }}
        
        .line-number {{
            background: #e9ecef;
            padding: 4px 12px;
            border-radius: 4px;
            font-family: 'Consolas', monospace;
            font-size: 12px;
            color: #495057;
        }}
        
        .issue-description {{
            color: #495057;
            font-size: 14px;
            margin-bottom: 15px;
        }}
        
        .code-block {{
            background: #f8f9fa;
            border-left: 3px solid #dc3545;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
            overflow-x: auto;
        }}
        .code-block code {{
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
            color: #e83e8c;
            display: block;
            white-space: pre;
        }}
        
        .recommendation {{
            background: #d4edda;
            border-left: 3px solid #28a745;
            padding: 15px;
            border-radius: 4px;
            margin-top: 15px;
        }}
        .recommendation-title {{
            font-weight: bold;
            color: #155724;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .recommendation-text {{
            color: #155724;
            font-size: 14px;
        }}
        
        .no-findings {{
            text-align: center;
            padding: 60px 20px;
            color: #28a745;
        }}
        .no-findings-icon {{ font-size: 64px; margin-bottom: 20px; }}
        .no-findings-text {{ font-size: 24px; font-weight: 500; }}
        
        footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-size: 14px;
            border-top: 1px solid #e9ecef;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔒 SQL Injection Security Scan Report</h1>
            <div class="meta">
                <div>Scan Path: <strong>{scan_path}</strong></div>
                <div>Generated: <strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong></div>
            </div>
        </header>
        
        <div class="summary">
            <div class="summary-card total">
                <div class="summary-value">{total}</div>
                <div class="summary-label">Total Findings</div>
            </div>
            <div class="summary-card critical">
                <div class="summary-value">{len(critical)}</div>
                <div class="summary-label">Critical</div>
            </div>
            <div class="summary-card high">
                <div class="summary-value">{len(high)}</div>
                <div class="summary-label">High</div>
            </div>
            <div class="summary-card medium">
                <div class="summary-value">{len(medium)}</div>
                <div class="summary-label">Medium</div>
            </div>
            <div class="summary-card low">
                <div class="summary-value">{len(low)}</div>
                <div class="summary-label">Low</div>
            </div>
        </div>
        
        <div class="content">
"""
        
        if total == 0:
            html += """
            <div class="no-findings">
                <div class="no-findings-icon">✅</div>
                <div class="no-findings-text">No SQL Injection Vulnerabilities Found</div>
                <p style="margin-top: 10px; color: #6c757d;">Your code appears to be using safe parameterized queries.</p>
            </div>
"""
        else:
            for file_path, file_findings in sorted(by_file.items()):
                html += f"""
            <div class="file-section">
                <div class="file-header">
                    <span class="file-path">{file_path}</span>
                    <span class="finding-count">{len(file_findings)} issue{'s' if len(file_findings) != 1 else ''}</span>
                </div>
"""
                for finding in sorted(file_findings, key=lambda x: x.get('line', 0)):
                    severity = finding.get('severity', 'MEDIUM').lower()
                    line = finding.get('line', '?')
                    issue = finding.get('issue', 'SQL injection vulnerability detected')
                    code = finding.get('code_snippet', '').replace('<', '&lt;').replace('>', '&gt;')
                    recommendation = finding.get('recommendation', 'Use parameterized queries')
                    
                    html += f"""
                <div class="finding">
                    <div class="finding-header">
                        <span class="severity {severity}">{severity}</span>
                        <span class="line-number">Line {line}</span>
                    </div>
                    <div class="issue-description">{issue}</div>
                    <div class="code-block"><code>{code}</code></div>
                    <div class="recommendation">
                        <div class="recommendation-title">✅ Recommended Fix:</div>
                        <div class="recommendation-text">{recommendation}</div>
                    </div>
                </div>
"""
                html += """
            </div>
"""
        
        html += """
        </div>
        
        <footer>
            <p>Generated by Vancity SQL Injection Scanner</p>
            <p style="margin-top: 5px; font-size: 12px;">For more information, see scan documentation</p>
        </footer>
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return {
            "success": True,
            "output_file": output_file,
            "total_findings": total
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Agent Framework Integration
# ============================================================================
# Note: FunctionTool definitions for agent-framework-github-copilot integration
# have been removed from this standalone CLI version.
#
# For agent framework usage, use the handler functions directly:
# - scan_file_handler, scan_directory_handler, check_parameterized_handler, generate_report_handler
