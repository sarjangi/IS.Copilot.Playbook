"""Security scanner module for broad secure-coding checks.

This scanner is intentionally in-process and dependency-free so it can be run in
restricted enterprise environments. It performs static pattern checks across
common source file types and reports findings with severity and CWE mapping.

The public entrypoint uses action-based routing so the module can grow without
changing the top-level MCP tool contract.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


_SCANNABLE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".java",
    ".cs",
    ".php",
    ".rb",
    ".go",
    ".ps1",
    ".psm1",
    ".yaml",
    ".yml",
    ".json",
    ".xml",
    ".config",
    ".ini",
    ".env",
    ".properties",
}

_SEVERITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

_SCAN_PROFILES: Dict[str, Dict[str, Any]] = {
    "quick": {
        "description": "Fast high-signal scan focused on credentials, injection, deserialization, transport, and auth issues.",
        "rule_categories": [
            "secrets",
            "injection",
            "command-injection",
            "deserialization",
            "transport-security",
            "auth",
        ],
    },
    "full": {
        "description": "Broader in-process scan including lower-signal categories such as weak crypto and DOM XSS sinks.",
        "rule_categories": [
            "secrets",
            "injection",
            "command-injection",
            "deserialization",
            "crypto",
            "transport-security",
            "auth",
            "xss",
        ],
    },
    "secrets": {
        "description": "Focused scan for hardcoded credentials and private key material.",
        "rule_categories": ["secrets"],
    },
}

_SUPPORTED_REPORT_FORMATS = {"text", "json", "summary"}

_PATTERNS: List[Tuple[re.Pattern[str], str, str, str, str, str]] = [
    (
        re.compile(r"(?i)(password|passwd|pwd|api[_-]?key|secret|token)\s*[:=]\s*['\"][^'\"]{6,}['\"]"),
        "Hardcoded credential or token in source/config",
        "HIGH",
        "CWE-798",
        "secrets",
        "regex",
    ),
    (
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "Private key material present in file",
        "CRITICAL",
        "CWE-798",
        "secrets",
        "regex",
    ),
    (
        re.compile(r"\b(eval|exec)\s*\("),
        "Dynamic code execution primitive detected",
        "HIGH",
        "CWE-94",
        "injection",
        "regex",
    ),
    (
        re.compile(r"subprocess\.(run|Popen|call|check_output)\([^\n]*shell\s*=\s*True"),
        "Command execution with shell=True",
        "HIGH",
        "CWE-78",
        "command-injection",
        "regex",
    ),
    (
        re.compile(r"\bos\.system\s*\("),
        "Command execution via os.system",
        "HIGH",
        "CWE-78",
        "command-injection",
        "regex",
    ),
    (
        re.compile(r"pickle\.(load|loads)\s*\("),
        "Unsafe deserialization sink (pickle)",
        "MEDIUM",
        "CWE-502",
        "deserialization",
        "regex",
    ),
    (
        re.compile(r"yaml\.load\s*\("),
        "Potential unsafe YAML deserialization (yaml.load)",
        "MEDIUM",
        "CWE-502",
        "deserialization",
        "regex",
    ),
    (
        re.compile(r"hashlib\.(md5|sha1)\s*\("),
        "Weak cryptographic hash usage",
        "LOW",
        "CWE-327",
        "crypto",
        "regex",
    ),
    (
        re.compile(r"requests\.[A-Za-z_]+\([^\n]*verify\s*=\s*False"),
        "TLS certificate verification disabled",
        "MEDIUM",
        "CWE-295",
        "transport-security",
        "regex",
    ),
    (
        re.compile(r"\"alg\"\s*:\s*\"none\""),
        "JWT algorithm set to none",
        "HIGH",
        "CWE-345",
        "auth",
        "regex",
    ),
    (
        re.compile(r"\.innerHTML\s*=\s*[^\n;]+"),
        "Potential DOM XSS sink (.innerHTML assignment)",
        "MEDIUM",
        "CWE-79",
        "xss",
        "regex",
    ),
]


_SKIP_DIRS = {
    'venv', '.venv', '__pycache__', 'node_modules', '.git',
    'bin', 'obj',       # .NET build output
    '_site',            # DocFX / static site generators
    'vendor', 'dist', 'wwwroot',  # common vendor/generated output
}


def _is_scannable_file(file_path: Path) -> bool:
    # Exclude minified files — always vendor/generated
    if file_path.name.endswith(('.min.js', '.min.css')):
        return False
    return file_path.is_file() and file_path.suffix.lower() in _SCANNABLE_EXTENSIONS


def _candidate_files(target: Path, recursive: bool) -> List[Path]:
    if target.is_file():
        return [target] if _is_scannable_file(target) else []

    if not target.is_dir():
        return []

    iterator = target.rglob("*") if recursive else target.glob("*")
    return [
        path for path in iterator
        if _is_scannable_file(path)
        and not any(part in _SKIP_DIRS for part in path.parts)
    ]


def _scan_file(file_path: Path) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as exc:
        return [
            {
                "file": str(file_path),
                "line": 0,
                "severity": "LOW",
                "cwe": "N/A",
                "category": "scanner",
                "source": "scanner",
                "issue": f"File could not be read: {exc}",
                "pattern": "read_error",
            }
        ]

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        for pattern, issue, severity, cwe, category, source in _PATTERNS:
            if pattern.search(line):
                findings.append(
                    {
                        "file": str(file_path),
                        "line": line_number,
                        "severity": severity,
                        "cwe": cwe,
                        "category": category,
                        "source": source,
                        "issue": issue,
                        "pattern": pattern.pattern,
                        "code": line.strip()[:300],
                    }
                )

    return _deduplicate_findings(findings)


def _filter_findings_by_profile(findings: List[Dict[str, Any]], profile: str) -> List[Dict[str, Any]]:
    profile_config = _SCAN_PROFILES.get(profile, _SCAN_PROFILES["quick"])
    categories = set(profile_config["rule_categories"])
    return [finding for finding in findings if finding.get("category") in categories]


def _deduplicate_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: Dict[Tuple[str, int, str], Dict[str, Any]] = {}

    for finding in findings:
        key = (finding.get("file", ""), int(finding.get("line", 0)), finding.get("category", ""))
        existing = deduped.get(key)

        if existing is None:
            deduped[key] = finding
            continue

        if _SEVERITY_RANK.get(str(finding.get("severity", "LOW")), 1) > _SEVERITY_RANK.get(
            str(existing.get("severity", "LOW")), 1
        ):
            deduped[key] = finding

    return sorted(deduped.values(), key=lambda f: (f.get("file", ""), int(f.get("line", 0))))


def _scan_path(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run static security checks for a file or directory."""
    target_path = args.get("target_path")
    recursive = bool(args.get("recursive", True))
    profile = str(args.get("profile", "quick")).lower()

    if not target_path:
        return {"success": False, "error": "target_path is required"}

    if profile not in _SCAN_PROFILES:
        return {
            "success": False,
            "error": f"Unsupported security scan profile: {profile}",
            "supported_profiles": sorted(_SCAN_PROFILES.keys()),
        }

    target = Path(target_path)
    if not target.exists():
        return {"success": False, "error": f"Target path does not exist: {target_path}"}

    files_to_scan = _candidate_files(target, recursive)
    findings: List[Dict[str, Any]] = []

    for file_path in files_to_scan:
        findings.extend(_scan_file(file_path))

    findings = _filter_findings_by_profile(findings, profile)

    severity_summary = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
    }

    for finding in findings:
        severity = str(finding.get("severity", "LOW")).upper()
        if severity in severity_summary:
            severity_summary[severity] += 1

    return {
        "success": True,
        "action": "scan_path",
        "profile": profile,
        "target_path": str(target),
        "files_scanned": len(files_to_scan),
        "total_findings": len(findings),
        "severity_summary": severity_summary,
        "findings": findings,
        "message": (
            f"Security scan complete: {len(findings)} finding(s) in {len(files_to_scan)} file(s) using profile '{profile}'."
        ),
    }


def _list_profiles(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return supported scan profiles for discoverability."""
    return {
        "success": True,
        "action": "list_profiles",
        "profiles": [
            {
                "name": name,
                "description": config["description"],
                "rule_categories": config["rule_categories"],
            }
            for name, config in sorted(_SCAN_PROFILES.items())
        ],
    }


def _generate_report(args: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a security scan report from findings."""
    findings = args.get("findings", [])
    output_format = str(args.get("output_format", "text")).lower()

    if output_format not in _SUPPORTED_REPORT_FORMATS:
        return {
            "success": False,
            "error": f"Unsupported report format: {output_format}",
            "supported_formats": sorted(_SUPPORTED_REPORT_FORMATS),
        }

    if not findings:
        empty_report = {
            "text": "✅ No security findings detected.",
            "summary": "Security Scan Summary\n========================================\nTotal findings : 0\n",
            "json": "[]",
        }
        return {
            "success": True,
            "action": "generate_report",
            "output_format": output_format,
            "report": empty_report[output_format],
            "total": 0,
        }

    critical = [f for f in findings if f.get("severity") == "CRITICAL"]
    high = [f for f in findings if f.get("severity") == "HIGH"]
    medium = [f for f in findings if f.get("severity") == "MEDIUM"]
    low = [f for f in findings if f.get("severity") == "LOW"]
    other = [
        f for f in findings if f.get("severity") not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    ]

    if output_format == "json":
        return {
            "success": True,
            "action": "generate_report",
            "output_format": output_format,
            "report": json.dumps(findings, indent=2),
            "total": len(findings),
        }

    if output_format == "summary":
        report = (
            "Security Scan Summary\n"
            "========================================\n"
            f"Total findings : {len(findings)}\n"
            f"  CRITICAL     : {len(critical)}\n"
            f"  HIGH         : {len(high)}\n"
            f"  MEDIUM       : {len(medium)}\n"
            f"  LOW          : {len(low)}\n"
        )
        return {
            "success": True,
            "action": "generate_report",
            "output_format": output_format,
            "report": report,
            "total": len(findings),
        }

    report_lines = [
        "Security Scan Report",
        "============================================================",
        f"Total findings: {len(findings)}",
        f"CRITICAL: {len(critical)} | HIGH: {len(high)} | MEDIUM: {len(medium)} | LOW: {len(low)}",
        "",
    ]

    for severity, group in [
        ("CRITICAL", critical),
        ("HIGH", high),
        ("MEDIUM", medium),
        ("LOW", low),
        ("OTHER", other),
    ]:
        if not group:
            continue
        report_lines.append(f"{severity} ({len(group)})")
        report_lines.append("------------------------------------------------------------")
        for finding in group:
            report_lines.append(f"File     : {finding.get('file', 'unknown')}")
            report_lines.append(f"Line     : {finding.get('line', '?')}")
            report_lines.append(f"Category : {finding.get('category', 'unknown')}")
            report_lines.append(f"CWE      : {finding.get('cwe', 'N/A')}")
            report_lines.append(f"Issue    : {finding.get('issue', '')}")
            if finding.get("code"):
                report_lines.append(f"Code     : {finding.get('code')}")
            report_lines.append("")

    return {
        "success": True,
        "action": "generate_report",
        "output_format": output_format,
        "report": "\n".join(report_lines),
        "total": len(findings),
    }


def _html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _generate_html_report(args: Dict[str, Any]) -> Dict[str, Any]:
    """Generate an HTML security scan report from findings."""
    findings = args.get("findings", [])
    output_file = args.get("output_file")
    scan_path = str(args.get("scan_path", "security scan"))

    if not output_file:
        return {"success": False, "error": "output_file is required"}

    critical = [f for f in findings if f.get("severity") == "CRITICAL"]
    high = [f for f in findings if f.get("severity") == "HIGH"]
    medium = [f for f in findings if f.get("severity") == "MEDIUM"]
    low = [f for f in findings if f.get("severity") == "LOW"]

    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for finding in findings:
        file_path = str(finding.get("file", "unknown"))
        by_file.setdefault(file_path, []).append(finding)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset=\"UTF-8\">
    <title>Security Scan Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f7fb; padding: 20px; color: #1f2937; }}
        .container {{ max-width: 1320px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.08); }}
        header {{ background: linear-gradient(135deg, #0f766e 0%, #1d4ed8 100%); color: #fff; padding: 32px; }}
        header h1 {{ font-size: 30px; margin-bottom: 8px; }}
        header .meta {{ opacity: 0.92; font-size: 14px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; padding: 24px; background: #f8fafc; border-bottom: 1px solid #e5e7eb; }}
        .card {{ background: #fff; border-radius: 10px; padding: 18px; border-left: 5px solid #64748b; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .card.total {{ border-left-color: #2563eb; }}
        .card.critical {{ border-left-color: #dc2626; }}
        .card.high {{ border-left-color: #ea580c; }}
        .card.medium {{ border-left-color: #d97706; }}
        .card.low {{ border-left-color: #0891b2; }}
        .value {{ font-size: 34px; font-weight: 700; }}
        .label {{ font-size: 13px; color: #475569; margin-top: 4px; }}
        .content {{ padding: 24px; }}
        .file-section {{ margin-bottom: 24px; border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; }}
        .file-header {{ background: #111827; color: #fff; padding: 14px 18px; display: flex; justify-content: space-between; gap: 12px; font-family: Consolas, monospace; font-size: 13px; }}
        .finding {{ padding: 18px; border-bottom: 1px solid #e5e7eb; }}
        .finding:last-child {{ border-bottom: none; }}
        .finding-head {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 12px; }}
        .severity {{ padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; letter-spacing: 0.04em; }}
        .severity.critical {{ background: #fee2e2; color: #991b1b; }}
        .severity.high {{ background: #ffedd5; color: #9a3412; }}
        .severity.medium {{ background: #fef3c7; color: #92400e; }}
        .severity.low {{ background: #cffafe; color: #155e75; }}
        .pill {{ background: #e5e7eb; color: #374151; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; }}
        .issue {{ font-size: 14px; margin-bottom: 10px; }}
        pre {{ background: #f8fafc; border-left: 4px solid #cbd5e1; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 12px; }}
        .empty {{ padding: 48px 24px; text-align: center; color: #047857; }}
    </style>
</head>
<body>
    <div class=\"container\">
        <header>
            <h1>Security Scan Report</h1>
            <div class=\"meta\">Target: <strong>{_html_escape(scan_path)}</strong></div>
        </header>
        <div class=\"summary\">
            <div class=\"card total\"><div class=\"value\">{len(findings)}</div><div class=\"label\">Total Findings</div></div>
            <div class=\"card critical\"><div class=\"value\">{len(critical)}</div><div class=\"label\">Critical</div></div>
            <div class=\"card high\"><div class=\"value\">{len(high)}</div><div class=\"label\">High</div></div>
            <div class=\"card medium\"><div class=\"value\">{len(medium)}</div><div class=\"label\">Medium</div></div>
            <div class=\"card low\"><div class=\"value\">{len(low)}</div><div class=\"label\">Low</div></div>
        </div>
        <div class=\"content\">
"""

    if not findings:
        html += """
            <div class=\"empty\">
                <h2>No security findings detected</h2>
            </div>
"""
    else:
        for file_path, file_findings in sorted(by_file.items()):
            html += f"""
            <div class=\"file-section\">
                <div class=\"file-header\">
                    <span>{_html_escape(file_path)}</span>
                    <span>{len(file_findings)} finding(s)</span>
                </div>
"""
            for finding in sorted(file_findings, key=lambda item: (int(item.get("line", 0)), str(item.get("issue", "")))):
                severity = str(finding.get("severity", "LOW")).lower()
                issue = _html_escape(str(finding.get("issue", "")))
                code = _html_escape(str(finding.get("code", "")))
                cwe = _html_escape(str(finding.get("cwe", "N/A")))
                category = _html_escape(str(finding.get("category", "unknown")))
                line = _html_escape(str(finding.get("line", "?")))
                html += f"""
                <div class=\"finding\">
                    <div class=\"finding-head\">
                        <span class=\"severity {severity}\">{severity.upper()}</span>
                        <span class=\"pill\">Line {line}</span>
                        <span class=\"pill\">{cwe}</span>
                        <span class=\"pill\">{category}</span>
                    </div>
                    <div class=\"issue\">{issue}</div>
                    <pre>{code}</pre>
                </div>
"""
            html += """
            </div>
"""

    html += """
        </div>
    </div>
</body>
</html>
"""

    Path(output_file).write_text(html, encoding="utf-8")
    return {
        "success": True,
        "action": "generate_html_report",
        "output_file": str(output_file),
        "total_findings": len(findings),
    }


def scan_security_vulnerabilities(args: Dict[str, Any]) -> Dict[str, Any]:
    """Route security scanner actions for the scan_security MCP tool.

    Supported actions:
    - scan_path: scan a file or directory using a named profile
    - list_profiles: list supported scan profiles
    - generate_report: format findings as text/json/summary
    - generate_html_report: write findings to an HTML report
    """
    action = args.get("action")

    if action == "scan_path":
        return _scan_path(args)
    if action == "list_profiles":
        return _list_profiles(args)
    if action == "generate_report":
        return _generate_report(args)
    if action == "generate_html_report":
        return _generate_html_report(args)

    return {
        "success": False,
        "error": f"Unsupported scan_security action: {action}",
        "supported_actions": ["scan_path", "list_profiles", "generate_report", "generate_html_report"],
    }
