"""
Pipeline orchestrator for Integration Platform.

Chains: clone → SQL scan → security scan → fix suggestions → HTML report → [branch + PR].

Actions:
  dry_run  Clone, scan, generate fix suggestions and HTML report. No changes pushed.
  run      All of dry_run, then apply fixes, push a branch, and create a PR.

Public interface:
    run_pipeline(args) -> dict

Requires GitPython for cloning (project dependency).
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

_TOOLS_DIR = Path(__file__).parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from auto_fixer import generate_fixes  # noqa: E402
from pr_creator import (  # noqa: E402
    _build_auth_push_url,
    create_pr,
    detect_platform,
    parse_repo_url,
)
from security_scanner import scan_security_vulnerabilities  # noqa: E402
from sql_scanner import scan_sql_injection_directory  # noqa: E402

try:
    from git import GitCommandError, Repo
    _GIT_AVAILABLE = True
except ImportError:
    _GIT_AVAILABLE = False
    Repo = None  # type: ignore[assignment,misc]
    GitCommandError = Exception  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Cloning helper
# ---------------------------------------------------------------------------

def _build_clone_url(repo_url: str, auth_token: str) -> str:
    """Embed token into HTTPS URL for cloning (skip if SSH or no token)."""
    if not auth_token or not repo_url.startswith("https://"):
        return repo_url
    try:
        platform = detect_platform(repo_url)
        return _build_auth_push_url(repo_url, auth_token, platform)
    except ValueError:
        return repo_url


def _clone_repo(repo_url: str, target_dir: str, auth_token: str, branch: str) -> None:
    """Clone repo_url into target_dir. Raises GitCommandError on failure."""
    # Clean up any pre-existing directory so every scan starts fresh.
    target_path = Path(target_dir)
    if target_path.exists():
        shutil.rmtree(target_path, ignore_errors=True)
    target_path.mkdir(parents=True, exist_ok=True)

    clone_url = _build_clone_url(repo_url, auth_token)
    kwargs: Dict[str, Any] = {
        # Disable the Windows Credential Manager so the embedded PAT is used
        # directly rather than being intercepted by the system credential store.
        "env": {"GIT_TERMINAL_PROMPT": "0"},
        "config": ["credential.helper="],
        "allow_unsafe_options": True,
    }
    if branch:
        kwargs["branch"] = branch
    Repo.clone_from(clone_url, target_dir, **kwargs)


# ---------------------------------------------------------------------------
# HTML report builder
# ---------------------------------------------------------------------------

_HTML_STYLE = """
<style>
  body { font-family: -apple-system, Arial, sans-serif; margin: 24px; color: #1a1a2e; }
  h1 { font-size: 1.6rem; margin-bottom: 4px; }
  .meta { color: #666; font-size: 0.85rem; margin-bottom: 20px; }
  .summary-grid { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
  .card { border: 1px solid #ccc; border-radius: 8px; padding: 12px 20px; min-width: 120px; }
  .card h3 { margin: 0 0 4px 0; font-size: 1.5rem; }
  .card p { margin: 0; font-size: 0.8rem; color: #555; }
  .CRITICAL h3 { color: #c0392b; }
  .HIGH h3 { color: #e67e22; }
  .MEDIUM h3 { color: #f39c12; }
  .LOW h3 { color: #2980b9; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 24px; font-size: 0.85rem; }
  th { background: #f0f4f8; text-align: left; padding: 8px 12px; }
  td { padding: 6px 12px; border-bottom: 1px solid #eee; vertical-align: top; }
  .sev-CRITICAL { color: #c0392b; font-weight: bold; }
  .sev-HIGH { color: #e67e22; font-weight: bold; }
  .sev-MEDIUM { color: #f39c12; }
  .sev-LOW { color: #2980b9; }
  .fix-badge { background: #27ae60; color: #fff; border-radius: 4px;
               padding: 2px 6px; font-size: 0.75rem; }
  .suggest-badge { background: #8e44ad; color: #fff; border-radius: 4px;
                   padding: 2px 6px; font-size: 0.75rem; }
  pre { background: #f6f8fa; padding: 12px; border-radius: 4px;
        overflow-x: auto; font-size: 0.8rem; margin: 0; }
  details { margin: 4px 0; }
  summary { cursor: pointer; color: #2c3e50; }
</style>
"""


def _rel_path(abs_path: str, base_dir: str) -> str:
    try:
        return str(Path(abs_path).relative_to(base_dir)).replace("\\", "/")
    except ValueError:
        return abs_path


def _build_html_report(
    repo_url: str,
    scan_dir: str,
    sql_findings: List[Dict],
    security_findings: List[Dict],
    fix_result: Dict,
    action: str,
    pr_url: str,
    branch_name: str,
) -> str:
    all_findings = sql_findings + security_findings
    stats = fix_result.get("stats", {})
    fix_suggestions = fix_result.get("fix_suggestions", [])
    combined_patch = fix_result.get("combined_patch", "")

    sev_counts: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in all_findings:
        sev = (f.get("severity") or "").upper()
        if sev in sev_counts:
            sev_counts[sev] += 1

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pr_banner = (
        f'<p style="color:#27ae60;font-weight:bold;">✓ Pull request created: '
        f'<a href="{pr_url}">{pr_url}</a></p>'
        if pr_url
        else ""
    )

    cards = "".join(
        f'<div class="card {sev}"><h3>{count}</h3><p>{sev}</p></div>'
        for sev, count in sev_counts.items()
    )

    # Findings table rows
    rows = []
    for finding in all_findings:
        sev = (finding.get("severity") or "").upper()
        rel = _rel_path(finding.get("file", ""), scan_dir)
        line = finding.get("line", "")
        issue = finding.get("issue") or finding.get("description") or ""
        cwe = finding.get("cwe", "")
        src = finding.get("source", "")
        snippet = (finding.get("code") or finding.get("code_snippet") or "")[:120]
        rows.append(
            f"<tr>"
            f"<td><span class='sev-{sev}'>{sev}</span></td>"
            f"<td>{rel}:{line}</td>"
            f"<td>{cwe}</td>"
            f"<td>{issue}</td>"
            f"<td><code>{_esc(snippet)}</code></td>"
            f"<td>{src}</td>"
            f"</tr>"
        )
    findings_table = (
        "<table><tr><th>Severity</th><th>Location</th><th>CWE</th>"
        "<th>Issue</th><th>Code</th><th>Source</th></tr>"
        + "".join(rows)
        + "</table>"
        if rows
        else "<p>No findings.</p>"
    )

    # Fix suggestions rows
    fix_rows = []
    for suggestion in fix_suggestions:
        sev = (suggestion.get("severity") or "").upper()
        rel = _rel_path(suggestion.get("file", ""), scan_dir)
        line = suggestion.get("line", "")
        badge = (
            "<span class='fix-badge'>auto-fix</span>"
            if suggestion.get("auto_fixable")
            else "<span class='suggest-badge'>review</span>"
        )
        explanation = _esc(suggestion.get("explanation", ""))
        orig = _esc(suggestion.get("original_code") or "")
        fixed = _esc(suggestion.get("fixed_code") or "")
        fix_rows.append(
            f"<tr>"
            f"<td><span class='sev-{sev}'>{sev}</span></td>"
            f"<td>{rel}:{line}</td>"
            f"<td>{badge}</td>"
            f"<td>{explanation}</td>"
            f"<td><details><summary>diff</summary>"
            f"<pre>- {orig}\n+ {fixed}</pre></details></td>"
            f"</tr>"
        )
    fixes_table = (
        "<table><tr><th>Severity</th><th>Location</th><th>Type</th>"
        "<th>Explanation</th><th>Change</th></tr>"
        + "".join(fix_rows)
        + "</table>"
        if fix_rows
        else "<p>No fix suggestions.</p>"
    )

    patch_section = (
        f"<details><summary>Combined patch (apply with <code>git apply</code>)"
        f"</summary><pre>{_esc(combined_patch)}</pre></details>"
        if combined_patch
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Security Pipeline Report</title>{_HTML_STYLE}</head>
<body>
<h1>Security Pipeline Report</h1>
<div class="meta">
  Repository: {_esc(repo_url)} &bull; Scanned: {ts} &bull; Action: {action}
</div>
{pr_banner}
<h2>Summary</h2>
<div class="summary-grid">
  {cards}
  <div class="card"><h3>{stats.get("auto_fixable", 0)}</h3><p>Auto-fixed</p></div>
  <div class="card"><h3>{stats.get("suggestion_only", 0)}</h3><p>Manual review</p></div>
</div>
<h2>Findings ({len(all_findings)})</h2>
{findings_table}
<h2>Fix Suggestions ({len(fix_suggestions)})</h2>
{fixes_table}
{patch_section}
</body></html>"""


def _esc(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def run_pipeline(args: Dict[str, Any]) -> Dict[str, Any]:
    """Orchestrate the full security scan + fix suggestion pipeline.

    Args (dict keys):
        action       str   "dry_run" or "run" (default: "dry_run")
        repo_url     str   Git repository URL (HTTPS)
        branch       str   Branch to scan (optional; defaults to repo default)
        auth_token   str   PAT for private repos and PR creation (required for "run")
        base_branch  str   Base branch for the PR (default: "main")
        scan_profile str   "quick" | "full" | "secrets" (default: "quick")
        pr_title     str   (optional) override PR title
        pr_body      str   (optional) additional text for PR description
        output_file  str   (optional) full path to write the HTML report to disk

    Returns dict with:
        action            str
        repo_url          str
        total_findings    int
        sql_findings_count int
        security_findings_count int
        fix_suggestions   list
        combined_patch    str
        stats             dict
        html_report       str  (full HTML report as string)
        html_report_path  str  (path where HTML was saved, or "" if output_file not given)
        pr_url            str  (run mode only, empty on dry_run or if no fixes)
        branch_name       str  (run mode only)
    """
    if not _GIT_AVAILABLE:
        return {"error": "GitPython is not installed. Run: pip install gitpython"}

    action: str = args.get("action", "dry_run").strip().lower()
    repo_url: str = args.get("repo_url", "")
    branch: str = args.get("branch", "")
    auth_token: str = args.get("auth_token", "")
    base_branch: str = args.get("base_branch", "main")
    scan_profile: str = args.get("scan_profile", "quick")
    output_file: str = args.get("output_file", "")
    pbi_number: str = str(args.get("pbi_number", "")).strip()
    pr_title: str = args.get(
        "pr_title", "Automated security fix suggestions [Integration Platform]"
    )
    pr_body_extra: str = args.get("pr_body", "")

    if action not in ("dry_run", "run"):
        return {"error": f"Unsupported action: {action!r}. Use 'dry_run' or 'run'."}

    if not repo_url:
        return {"error": "repo_url is required"}

    if action == "run" and not auth_token:
        return {"error": "auth_token is required for action='run' (needed for push + PR)"}

    # -----------------------------------------------------------------------
    # Step 1: Clone
    # -----------------------------------------------------------------------
    temp_dir = tempfile.mkdtemp(prefix="ip_pipeline_")
    try:
        try:
            _clone_repo(repo_url, temp_dir, auth_token, branch)
        except GitCommandError as exc:
            return {"error": f"Clone failed: {exc}"}

        # -----------------------------------------------------------------------
        # Step 2: SQL injection scan
        # -----------------------------------------------------------------------
        sql_result = scan_sql_injection_directory(
            {"directory_path": temp_dir, "recursive": True}
        )
        sql_findings: List[Dict] = sql_result.get("findings", [])

        # -----------------------------------------------------------------------
        # Step 3: Security scan
        # -----------------------------------------------------------------------
        sec_result = scan_security_vulnerabilities(
            {"action": "scan_path", "target_path": temp_dir, "profile": scan_profile}
        )
        security_findings: List[Dict] = sec_result.get("findings", [])

        all_findings = sql_findings + security_findings

        # -----------------------------------------------------------------------
        # Step 4: Generate fix suggestions
        # -----------------------------------------------------------------------
        fix_result = generate_fixes({"findings": all_findings, "base_dir": temp_dir})
        fix_suggestions = fix_result.get("fix_suggestions", [])
        combined_patch = fix_result.get("combined_patch", "")

        # -----------------------------------------------------------------------
        # Step 5: PR (run mode only)
        # -----------------------------------------------------------------------
        pr_url = ""
        branch_name = ""

        if action == "run":
            work_item_ids = [int(pbi_number)] if pbi_number.isdigit() else []
            # Pre-build branch name with PBI prefix so it's consistent
            ts = datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%S")
            auto_branch = f"PBI-{pbi_number}-security-fixes-{ts}" if pbi_number.isdigit() else f"security-fixes-{ts}"

            pr_description = _build_pr_body(
                repo_url, len(all_findings), fix_result, pr_body_extra,
                sql_findings=sql_findings, security_findings=security_findings,
                branch_name=auto_branch,
            )
            # Build a preliminary HTML report (no pr_url yet) and write it into
            # the cloned repo so it is committed alongside the code fixes.
            _html_for_commit = _build_html_report(
                repo_url, temp_dir, sql_findings, security_findings,
                fix_result, action, "", "",
            )
            _report_filename = "security-report.html"
            import os as _os
            _report_in_repo = _os.path.join(temp_dir, _report_filename)
            with open(_report_in_repo, "w", encoding="utf-8") as _fh:
                _fh.write(_html_for_commit)

            pr_result = create_pr(
                {
                    "repo_url": repo_url,
                    "base_branch": base_branch,
                    "auth_token": auth_token,
                    "repo_dir": temp_dir,
                    "findings": all_findings,
                    "pr_title": pr_title,
                    "pr_body": pr_description,
                    "extra_files": [_report_filename],
                    "work_item_ids": work_item_ids,
                    "branch_name": auto_branch,
                }
            )
            if "error" in pr_result:
                # Non-fatal: include the error in the result but still return the report
                return {
                    "action": action,
                    "repo_url": repo_url,
                    "error": pr_result["error"],
                    "branch_name": pr_result.get("branch_name", auto_branch),
                    "total_findings": len(all_findings),
                    "fix_suggestions": fix_suggestions,
                    "combined_patch": combined_patch,
                    "stats": fix_result.get("stats", {}),
                    "html_report": _build_html_report(
                        repo_url, temp_dir, sql_findings, security_findings,
                        fix_result, action, "", "",
                    ),
                }
            pr_url = pr_result.get("pr_url", "")
            branch_name = pr_result.get("branch_name", "")

        # -----------------------------------------------------------------------
        # Step 6: HTML report
        # -----------------------------------------------------------------------
        html_report = _build_html_report(
            repo_url, temp_dir, sql_findings, security_findings,
            fix_result, action, pr_url, branch_name,
        )

        html_report_path = ""
        if output_file:
            try:
                import os
                os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as fh:
                    fh.write(html_report)
                html_report_path = os.path.abspath(output_file)
            except Exception as write_err:
                html_report_path = f"ERROR: {write_err}"

        return {
            "action": action,
            "repo_url": repo_url,
            "total_findings": len(all_findings),
            "sql_findings_count": len(sql_findings),
            "security_findings_count": len(security_findings),
            "fix_suggestions": fix_suggestions,
            "combined_patch": combined_patch,
            "stats": fix_result.get("stats", {}),
            "html_report": html_report,
            "html_report_path": html_report_path,
            "pr_url": pr_url,
            "branch_name": branch_name,
        }

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _build_pr_body(
    repo_url: str,
    total_findings: int,
    fix_result: Dict[str, Any],
    extra: str,
    sql_findings: Optional[List[Dict]] = None,
    security_findings: Optional[List[Dict]] = None,
    branch_name: str = "",
) -> str:
    stats = fix_result.get("stats", {})
    auto_fixable = stats.get("auto_fixable", 0)
    suggestion_only = stats.get("suggestion_only", 0)

    # Build severity counts table
    all_findings = (sql_findings or []) + (security_findings or [])
    sev_counts: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in all_findings:
        sev = (f.get("severity") or "").upper()
        if sev in sev_counts:
            sev_counts[sev] += 1

    sev_table = (
        "| Severity | Count |\n"
        "|----------|-------|\n"
        + "".join(
            f"| {sev} | {count} |\n"
            for sev, count in sev_counts.items()
        )
    )

    # Top findings detail (up to 5, sorted by severity)
    _sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    top = sorted(
        all_findings,
        key=lambda f: _sev_order.get((f.get("severity") or "").upper(), 9),
    )[:5]
    top_rows = ""
    for f in top:
        sev = (f.get("severity") or "").upper()
        cwe = f.get("cwe", "")
        issue = f.get("issue") or f.get("description") or ""
        fpath = f.get("file", "")
        line = f.get("line", "")
        top_rows += f"| {sev} | {cwe} | {issue[:80]} | {fpath}:{line} |\n"

    lines = [
        "## Automated Security Scan Results",
        "",
        f"This PR was created by the **Integration Platform Security Pipeline**.",
        f"Repository scanned: `{repo_url}`",
        "",
        "### Findings Summary",
        "",
        sev_table,
        f"- **Total findings**: {total_findings}",
        f"- **Auto-applied fixes**: {auto_fixable} (safe mechanical transforms only)",
        f"- **Manual review required**: {suggestion_only} (complex issues — see full report)",
        "",
    ]

    # Add a clickable link to the committed HTML report file
    if branch_name:
        try:
            parsed = parse_repo_url(repo_url)
            if parsed["platform"] == "azuredevops":
                org, project, repo = parsed["org"], parsed["project"], parsed["repo"]
                report_url = (
                    f"https://dev.azure.com/{org}/{project}/_git/{repo}"
                    f"?path=%2Fsecurity-report.html&version=GB{branch_name}&_a=contents"
                )
            else:
                owner, repo = parsed["owner"], parsed["repo"]
                report_url = (
                    f"https://github.com/{owner}/{repo}/blob/{branch_name}/security-report.html"
                )
            lines += [
                "### 📄 Full Security Report",
                f"[View security-report.html]({report_url})",
                "",
                "> The HTML report is committed to this branch and contains the full "
                "findings with code snippets, fix suggestions, and severity details.",
                "",
            ]
        except Exception:
            pass  # URL construction is best-effort

    if top_rows:
        lines += [
            "### Top Findings",
            "",
            "| Severity | CWE | Issue | Location |",
            "|----------|-----|-------|----------|",
            top_rows,
        ]

    lines += [
        "### What was auto-fixed",
        "Only high-confidence, low-risk transformations were applied:",
        "- `yaml.load(` → `yaml.safe_load(` (CWE-502)",
        "- `requests(... verify=False)` → `verify=True` (CWE-295)",
        "",
        "### What requires manual review",
        "SQL injection (CWE-89), hardcoded credentials (CWE-798), weak hashes (CWE-327), "
        "pickle (CWE-502), and command injection (CWE-78/94) are listed in the full report "
        "but require manual fixes — they cannot be auto-patched safely.",
        "",
    ]

    if extra:
        lines += ["### Additional context", extra, ""]

    lines += [
        "---",
        "*Generated by Integration Platform Security Pipeline. "
        "Review all changes before merging.*",
    ]
    return "\n".join(lines)

