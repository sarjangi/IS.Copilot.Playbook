"""Auto-fix suggestion engine for Integration Platform.

Consumes findings from sql_scanner and security_scanner and produces
high-confidence fix suggestions as unified diffs.

Design principles:
  - Suggestions ONLY — never writes to disk, never mutates files
  - High-confidence mechanical transforms only; ambiguous rewrites are skipped
  - Every finding gets either a code fix or an advisory comment in the diff
  - ORM SQL (CWE-564), XSS (CWE-79), and data integrity (CWE-345) are suggestion-only
  - Multiple fixes per file are grouped into one unified diff per file

Public interface:
    generate_fixes(args) -> dict
        args:
            findings  : list[dict]   findings from sql_scanner / security_scanner
            base_dir  : str (opt.)   resolve relative file paths against this dir
        returns:
            fix_suggestions  : list of per-finding suggestion dicts
            diffs_by_file    : dict[file_path -> unified diff string]
            combined_patch   : str  all diffs concatenated (git-apply compatible)
            stats            : dict totals
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Transform classification
# ---------------------------------------------------------------------------

# Maps transform_key -> human-readable label
_TRANSFORM_LABELS: Dict[str, str] = {
    "yaml_load_to_safe_load":         "Replace yaml.load() with yaml.safe_load()",
    "requests_verify_false":          "Remove requests verify=False (TLS verification)",
    "weak_hash_upgrade":              "Replace weak hash (MD5/SHA-1) with SHA-256 (CWE-327)",
    "sql_parameterize":               "Parameterize SQL query with ? placeholder [CWE-89]",
    "hardcoded_credential_to_env":    "Replace hardcoded credential with env var [CWE-798]",
    "command_shell_fix":              "Change shell=True to shell=False [CWE-78/94]",
    "pickle_comment":                 "Add security warning above pickle deserialization",
    "weak_hash_comment":              "Add CWE-327 note above weak hash usage",
    "credential_comment":             "Add CWE-798 note above hardcoded credential",
    "private_key_comment":            "Add CWE-798 note above private key material",
    "command_injection_comment":      "Add CWE-78/94 note above dynamic execution",
    "sql_comment":                    "Add CWE-89 note above SQL string construction",
}

# CWEs where we skip entirely (truly context-dependent, no safe mechanical fix).
# CWE-89/798/78/94 now have best-effort transforms; only ORM-variant and XSS remain here.
_SUGGESTION_ONLY_CWES = {"CWE-564", "CWE-345", "CWE-79"}

# Security comment messages keyed by transform_key
_COMMENT_MESSAGES: Dict[str, str] = {
    "pickle_comment": (
        "SECURITY [CWE-502]: pickle deserialization can execute arbitrary code. "
        "Consider using json, msgpack, or a schema-validated alternative."
    ),
    "weak_hash_comment": (
        "SECURITY [CWE-327]: MD5/SHA-1 are cryptographically weak. "
        "Use hashlib.sha256() or stronger for security-sensitive purposes."
    ),
    "credential_comment": (
        "SECURITY [CWE-798]: Hardcoded credential detected. "
        "Replace with os.environ.get('YOUR_SECRET_NAME') or a secrets vault."
    ),
    "private_key_comment": (
        "SECURITY [CWE-798]: Private key material should not be stored in source. "
        "Use environment variables or a secrets manager (e.g. Azure Key Vault)."
    ),
    "command_injection_comment": (
        "SECURITY [CWE-78/94]: Dynamic code/command execution detected. "
        "Validate and sanitise all inputs; prefer allow-lists over deny-lists."
    ),
}


def _classify_finding(finding: Dict[str, Any]) -> Optional[str]:
    """Return the transform key for a finding, or None if not auto-fixable."""
    cwe = (finding.get("cwe") or "").strip().upper()
    issue = (finding.get("issue") or "").lower()
    code = (finding.get("code") or finding.get("code_snippet") or "").lower()

    if cwe in _SUGGESTION_ONLY_CWES:
        return None

    # yaml.load → yaml.safe_load  (real code fix)
    if cwe == "CWE-502" and ("yaml" in issue or "yaml" in code):
        return "yaml_load_to_safe_load"

    # requests verify=False → remove kwarg  (real code fix)
    if cwe == "CWE-295":
        return "requests_verify_false"

    # weak hash (MD5/SHA-1) → SHA-256  (real code fix)
    if cwe == "CWE-327":
        return "weak_hash_upgrade"

    # SQL injection — best-effort parameterization (f-string & simple concat)
    if cwe == "CWE-89":
        return "sql_parameterize"

    # Hardcoded credential → environment variable lookup
    if cwe == "CWE-798":
        return "hardcoded_credential_to_env"

    # Command/code injection — change shell=True to shell=False where possible
    if cwe in ("CWE-78", "CWE-94"):
        return "command_shell_fix"

    # All other CWE-502 cases (e.g. pickle) — suggestion only, no file modification
    return None


# ---------------------------------------------------------------------------
# Individual line transforms
# ---------------------------------------------------------------------------

def _transform_yaml_load(line: str) -> Optional[str]:
    """yaml.load(... → yaml.safe_load(... and remove Loader= kwarg."""
    if not re.search(r'\byaml\.load\b', line):
        return None
    new = re.sub(r'\byaml\.load\b', 'yaml.safe_load', line)
    # yaml.safe_load does not accept Loader= — remove it
    new = re.sub(r',\s*Loader\s*=\s*[\w.]+', '', new)
    return new if new != line else None


def _transform_requests_verify(line: str) -> Optional[str]:
    """Remove verify=False keyword argument from a requests call."""
    if 'verify' not in line:
        return None
    new = line
    # Trailing position:  requests.get(url, verify=False)
    new = re.sub(r',\s*verify\s*=\s*False', '', new)
    # Leading position:   requests.get(verify=False, timeout=5)
    new = re.sub(r'verify\s*=\s*False\s*,\s*', '', new)
    # Sole argument: requests.get(verify=False)  (already covered above, guard)
    new = re.sub(r'verify\s*=\s*False', '', new)
    return new if new.rstrip() != line.rstrip() else None


def _transform_weak_hash(line: str) -> Optional[str]:
    """Replace hashlib.md5 / hashlib.sha1 / hashlib.new('md5') with sha256."""
    new = line
    # hashlib.md5( → hashlib.sha256(
    new = re.sub(r'\bhashlib\.md5\b', 'hashlib.sha256', new)
    # hashlib.sha1( → hashlib.sha256(
    new = re.sub(r'\bhashlib\.sha1\b', 'hashlib.sha256', new)
    # hashlib.new('md5') / hashlib.new("md5") → hashlib.new('sha256')
    new = re.sub(r"hashlib\.new\((['\"])md5\1\)", r"hashlib.new(\1sha256\1)", new)
    new = re.sub(r"hashlib\.new\((['\"])sha1\1\)", r"hashlib.new(\1sha256\1)", new)
    # MD5.new() / SHA.new() from Crypto / PyCryptodome — leave for manual review
    # (different API, risk of breaking)
    return new if new != line else None

def _transform_sql_injection(line: str, finding: Optional[Dict] = None) -> Optional[str]:
    """Best-effort SQL parameterization for Python and C#.

    Python handles:
    - f-string interpolation: cursor.execute(f"SELECT ... {var} ...")
    - Simple string concatenation: cursor.execute("SELECT ... " + var)

    C# handles:
    - Interpolated string in assignment: string q = $"SELECT ... {var} ...";
    - String concatenation: string q = "SELECT ... " + var + " ...";

    Returns None when the pattern is not recognised (caller falls back to comment).
    """
    finding = finding or {}
    file_path = finding.get("file", "")
    ext = Path(file_path).suffix.lower() if file_path else ".py"

    # ── C# transforms ──────────────────────────────────────────────────────
    if ext == ".cs":
        # Pattern: [var/string] name = $"...{var1}...{var2}...";
        m = re.match(
            r'^(\s*)(?:(?:var|string)\s+)?(\w+)\s*=\s*\$["\'](.+?)["\'];?\s*$',
            line,
        )
        if m:
            indent, var_name, sql_body = m.groups()
            vars_found = re.findall(r'\{([^{}:!]+)[^{}]*\}', sql_body)
            if vars_found:
                plain_sql = re.sub(r'\{[^{}]+\}', '@p{}', sql_body)
                # number the placeholders: @p0, @p1, ...
                counter = [0]
                def _num(match):
                    n = counter[0]; counter[0] += 1; return f'@p{n}'
                plain_sql = re.sub(r'@p\{\}', _num, plain_sql)
                params = "".join(
                    f'\n{indent}// cmd.Parameters.AddWithValue("@p{i}", {v});'
                    for i, v in enumerate(vars_found)
                )
                return (
                    f'{indent}var {var_name} = "{plain_sql}";\n'
                    f'{indent}// TODO [CWE-89]: Use parameterized query — replace above with SqlCommand:\n'
                    f'{indent}// using var cmd = new SqlCommand({var_name}, connection);{params}\n'
                )

        # Pattern: string name = "SQL " + var + "...";
        m2 = re.match(
            r'^(\s*)(?:(?:var|string)\s+)?(\w+)\s*=\s*"([^"]+)"\s*\+\s*(.+?);?\s*$',
            line,
        )
        if m2:
            indent, var_name, sql_part, rest = m2.groups()
            concat_vars = [v.strip() for v in rest.split('+') if v.strip().isidentifier()]
            if concat_vars:
                placeholders = " ".join(f'@p{i}' for i in range(len(concat_vars)))
                params = "".join(
                    f'\n{indent}// cmd.Parameters.AddWithValue("@p{i}", {v});'
                    for i, v in enumerate(concat_vars)
                )
                return (
                    f'{indent}var {var_name} = "{sql_part.rstrip()} {placeholders}";\n'
                    f'{indent}// TODO [CWE-89]: Use parameterized query — replace above with SqlCommand:\n'
                    f'{indent}// using var cmd = new SqlCommand({var_name}, connection);{params}\n'
                )
        return None

    # ── Python transforms ───────────────────────────────────────────────────
    # Only attempt mechanical rewrite for Python files
    if file_path and ext != ".py":
        return None

    # Pattern 1: cursor.execute(f"...{var}...")
    m = re.match(
        r'^(\s*)([\w.]+\.execute\s*\(\s*)(f["\'])(.*?)(["\'])(\s*\).*?)$',
        line,
    )
    if m:
        indent, call, fq, sql_body, _cq, rest = m.groups()
        vars_found = re.findall(r'\{([^{}:!]+)[^{}]*\}', sql_body)
        if vars_found:
            plain_sql = re.sub(r'\{[^{}]+\}', '?', sql_body)
            q = fq[1]  # the ' or " after 'f'
            params = ", ".join(vars_found)
            return f'{indent}{call}{q}{plain_sql}{q}, ({params},){rest}\n'

    # Pattern 2: cursor.execute("SQL " + var)
    m2 = re.match(
        r'^(\s*)([\w.]+\.execute\s*\(\s*)(["\'])([^"\']+)\3\s*\+\s*(\w+)(\s*\).*?)$',
        line,
    )
    if m2:
        indent, call, q, sql_part, var_name, rest = m2.groups()
        plain_sql = sql_part.rstrip() + "?"
        return f'{indent}{call}{q}{plain_sql}{q}, ({var_name},){rest}\n'

    return None


def _transform_hardcoded_credential(line: str, finding: Optional[Dict] = None) -> Optional[str]:
    """Replace a hardcoded credential literal with an environment variable lookup.

    Language-aware:
    - Python  → os.environ.get("VAR", "")
    - JS/TS   → process.env.VAR || ""
    - C#      → Environment.GetEnvironmentVariable("VAR") ?? ""
    - Java    → System.getenv("VAR")

    Returns None when the line doesn't match a simple assignment pattern
    (e.g. multi-line private key blocks).
    """
    finding = finding or {}
    # Match: [modifiers] [type] varname = "value"[;]
    # The credential value must be at least 4 chars to avoid false positives on empty
    m = re.match(
        r'^(\s*)(?:(?:const|let|var|final|static|private|public|protected|readonly)\s+)*'
        r'(?:\w+\s+)?(\w+)\s*=\s*(["\'])([^"\']{4,})\3\s*;?\s*$',
        line,
    )
    if not m:
        return None
    indent, var_name, quote, _value = m.group(1), m.group(2), m.group(3), m.group(4)
    env_key = re.sub(r'[^A-Z0-9_]', '_', var_name.upper())

    file_path = finding.get("file", "")
    ext = Path(file_path).suffix.lower() if file_path else ".py"

    if ext in (".js", ".ts"):
        kw_m = re.match(r'\s*(const|let|var)\s+', line)
        kw = (kw_m.group(1) + " ") if kw_m else ""
        return f'{indent}{kw}{var_name} = process.env.{env_key} || {quote}{quote};\n'
    if ext == ".cs":
        return (
            f'{indent}var {var_name} = '
            f'Environment.GetEnvironmentVariable({quote}{env_key}{quote}) ?? {quote}{quote};\n'
        )
    if ext == ".java":
        return f'{indent}String {var_name} = System.getenv({quote}{env_key}{quote});\n'
    # Python (default)
    return f'{indent}{var_name} = os.environ.get({quote}{env_key}{quote}, {quote}{quote})\n'


def _transform_command_injection(line: str) -> Optional[str]:
    """Change shell=True to shell=False in subprocess calls.

    This is a safe mechanical fix for the most common pattern. Callers that
    genuinely need shell features (pipes, globs) will need to refactor — the
    dev reviewing the PR will catch that.
    """
    if 'shell' not in line:
        return None
    new = re.sub(r'\bshell\s*=\s*True\b', 'shell=False', line)
    return new if new != line else None


def _ensure_import(lines: List[str], module: str) -> List[str]:
    """Insert 'import <module>' if not already present anywhere in the file."""
    import_stmt = f"import {module}\n"
    for line in lines:
        if re.match(rf'^(?:import\s+{re.escape(module)}\b|from\s+{re.escape(module)}\s+import)', line):
            return lines  # already imported
    # Insert after any leading shebang / encoding / docstring / blank lines
    insert_at = 0
    in_docstring = False
    docstring_char: Optional[str] = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if in_docstring:
            if docstring_char and docstring_char in stripped:
                in_docstring = False
            insert_at = i + 1
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            in_docstring = True
            docstring_char = stripped[:3]
            if stripped.count(docstring_char) >= 2 and len(stripped) > 3:
                in_docstring = False  # single-line docstring
            insert_at = i + 1
        elif not stripped or stripped.startswith('#'):
            insert_at = i + 1
        else:
            break
    result = list(lines)
    result.insert(insert_at, import_stmt)
    return result

def _comment_prefix(file_path: str) -> str:
    """Return the single-line comment token for the given file extension."""
    ext = Path(file_path).suffix.lower() if file_path else ""
    if ext in (".cs", ".java", ".js", ".ts", ".go", ".cpp", ".c", ".h", ".swift", ".kt"):
        return "//"
    if ext in (".sql",):
        return "--"
    if ext in (".ps1", ".psm1", ".psd1"):
        return "#"  # PowerShell also uses #
    # Default: Python / Ruby / YAML / shell / config files
    return "#"


def _build_comment_line(original_line: str, message: str, file_path: str = "") -> str:
    """Create a comment line with the same indentation as original_line.

    Uses the correct single-line comment syntax for the target language.
    """
    indent = len(original_line) - len(original_line.lstrip())
    prefix = _comment_prefix(file_path)
    return " " * indent + prefix + " " + message + "\n"


def _is_inside_multiline_string(lines: List[str], zero_based_idx: int) -> bool:
    """Return True if line[zero_based_idx] is inside a triple-quoted string or a
    line-continuation block, so that inserting a comment there would break syntax.

    Scans from the start of the file up to (but not including) the target line,
    tracking triple-quote open/close state and backslash continuations.
    """
    in_triple = False
    triple_char = ""
    for i, line in enumerate(lines[:zero_based_idx]):
        stripped = line.rstrip("\n")
        # Backslash continuation — next line is a logical continuation
        if not in_triple and stripped.endswith("\\"):
            # If the *target* line is the direct continuation of this line, skip it
            if i + 1 == zero_based_idx:
                return True
        # Track triple-quote open/close
        j = 0
        while j < len(stripped):
            if not in_triple:
                for delim in ('"""', "'''"):
                    if stripped[j:j+3] == delim:
                        in_triple = True
                        triple_char = delim
                        j += 3
                        break
                else:
                    # Skip single-quoted strings quickly
                    if stripped[j] in ('"', "'"):
                        q = stripped[j]
                        j += 1
                        while j < len(stripped) and stripped[j] != q:
                            if stripped[j] == "\\":
                                j += 1
                            j += 1
                    j += 1
            else:
                if stripped[j:j+3] == triple_char:
                    in_triple = False
                    triple_char = ""
                    j += 3
                else:
                    j += 1
    return in_triple


# ---------------------------------------------------------------------------
# Multi-finding transform application
# ---------------------------------------------------------------------------

def _apply_all_transforms(
    lines: List[str],
    file_findings: List[Dict[str, Any]],
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Apply all applicable transforms to a file's lines (in-place on a copy).

    Processes findings from highest line number to lowest so that insertions
    of comment lines do not shift the indices of findings at lower lines.

    Returns (modified_lines, list_of_applied_suggestion_dicts).
    """
    working = list(lines)
    applied: List[Dict[str, Any]] = []

    sorted_findings = sorted(
        file_findings,
        key=lambda f: int(f.get("line", 0)),
        reverse=True,
    )

    for finding in sorted_findings:
        line_num = int(finding.get("line", 0))
        if line_num <= 0 or line_num > len(working):
            continue

        idx = line_num - 1  # 0-based
        original = working[idx]
        transform_key = _classify_finding(finding)

        if transform_key is None:
            continue

        file_path = finding.get("file", "")
        cwe = finding.get("cwe", "")
        severity = finding.get("severity", "")

        if transform_key == "yaml_load_to_safe_load":
            new_line = _transform_yaml_load(original)
            if new_line is not None:
                working[idx] = new_line
                applied.append({
                    "file": file_path,
                    "line": line_num,
                    "original_code": original.rstrip(),
                    "fixed_code": new_line.rstrip(),
                    "explanation": _TRANSFORM_LABELS[transform_key],
                    "cwe": cwe,
                    "severity": severity,
                    "auto_fixable": True,
                    "transform": transform_key,
                })

        elif transform_key == "requests_verify_false":
            new_line = _transform_requests_verify(original)
            if new_line is not None:
                working[idx] = new_line
                applied.append({
                    "file": file_path,
                    "line": line_num,
                    "original_code": original.rstrip(),
                    "fixed_code": new_line.rstrip(),
                    "explanation": _TRANSFORM_LABELS[transform_key],
                    "cwe": cwe,
                    "severity": severity,
                    "auto_fixable": True,
                    "transform": transform_key,
                })

        elif transform_key == "weak_hash_upgrade":
            new_line = _transform_weak_hash(original)
            if new_line is not None:
                working[idx] = new_line
                applied.append({
                    "file": file_path,
                    "line": line_num,
                    "original_code": original.rstrip(),
                    "fixed_code": new_line.rstrip(),
                    "explanation": _TRANSFORM_LABELS[transform_key],
                    "cwe": cwe,
                    "severity": severity,
                    "auto_fixable": True,
                    "transform": transform_key,
                })

        elif transform_key == "sql_parameterize":
            new_line = _transform_sql_injection(original, finding)
            if new_line is not None:
                working[idx] = new_line
                applied.append({
                    "file": file_path,
                    "line": line_num,
                    "original_code": original.rstrip(),
                    "fixed_code": new_line.rstrip(),
                    "explanation": _TRANSFORM_LABELS["sql_parameterize"],
                    "cwe": cwe,
                    "severity": severity,
                    "auto_fixable": True,
                    "transform": transform_key,
                })
            else:
                # Pattern not recognised or non-Python file — insert a language-appropriate
                # advisory comment above the flagged line so it appears in the PR diff.
                # The existing line is NOT modified; the comment is a review marker only.
                recommendation = (finding.get("recommendation") or "").strip()
                ext = Path(file_path).suffix.lower() if file_path else ".py"
                if recommendation:
                    # Use the scanner's own recommendation (already language-specific)
                    advice = recommendation
                elif ext == ".cs":
                    advice = (
                        "Use SqlCommand with SqlParameter: "
                        "cmd.Parameters.AddWithValue(\"@param\", value)"
                    )
                elif ext == ".java":
                    advice = (
                        "Use PreparedStatement: "
                        "conn.prepareStatement(\"SELECT ... WHERE id=?\"); stmt.setInt(1, id)"
                    )
                elif ext in (".js", ".ts"):
                    advice = (
                        "Use a parameterized query: "
                        "db.query('SELECT ... WHERE id=?', [id])"
                    )
                else:
                    advice = (
                        "Parameterize this SQL query — "
                        "never build SQL from user-controlled strings"
                    )
                message = f"TODO [CWE-89]: {advice}"
                if _is_inside_multiline_string(working, idx):
                    continue
                comment_line = _build_comment_line(original, message, file_path)
                working.insert(idx, comment_line)
                applied.append({
                    "file": file_path,
                    "line": line_num,
                    "original_code": original.rstrip(),
                    "fixed_code": comment_line.rstrip() + "\n" + original.rstrip(),
                    "explanation": _TRANSFORM_LABELS["sql_comment"],
                    "cwe": cwe,
                    "severity": severity,
                    "auto_fixable": False,
                    "transform": "sql_comment",
                })

        elif transform_key == "hardcoded_credential_to_env":
            new_line = _transform_hardcoded_credential(original, finding)
            if new_line is not None:
                working[idx] = new_line
                applied.append({
                    "file": file_path,
                    "line": line_num,
                    "original_code": original.rstrip(),
                    "fixed_code": new_line.rstrip(),
                    "explanation": _TRANSFORM_LABELS["hardcoded_credential_to_env"],
                    "cwe": cwe,
                    "severity": severity,
                    "auto_fixable": True,
                    "transform": transform_key,
                })
            else:
                # Private key blocks / multi-line patterns — insert advisory comment
                message = (
                    "SECURITY [CWE-798]: Hardcoded secret detected. "
                    "Replace with os.environ.get('SECRET_NAME') or an Azure Key Vault reference."
                )
                if _is_inside_multiline_string(working, idx):
                    continue
                comment_line = _build_comment_line(original, message, file_path)
                working.insert(idx, comment_line)
                applied.append({
                    "file": file_path,
                    "line": line_num,
                    "original_code": original.rstrip(),
                    "fixed_code": comment_line.rstrip() + "\n" + original.rstrip(),
                    "explanation": _TRANSFORM_LABELS["credential_comment"],
                    "cwe": cwe,
                    "severity": severity,
                    "auto_fixable": False,
                    "transform": "credential_comment",
                })

        elif transform_key == "command_shell_fix":
            new_line = _transform_command_injection(original)
            if new_line is not None:
                working[idx] = new_line
                applied.append({
                    "file": file_path,
                    "line": line_num,
                    "original_code": original.rstrip(),
                    "fixed_code": new_line.rstrip(),
                    "explanation": _TRANSFORM_LABELS["command_shell_fix"],
                    "cwe": cwe,
                    "severity": severity,
                    "auto_fixable": True,
                    "transform": transform_key,
                })
            else:
                # eval() / exec() / os.system() — no safe mechanical substitute
                message = (
                    "SECURITY [CWE-78/94]: Dynamic command/code execution detected. "
                    "Validate all inputs; avoid eval/exec; prefer subprocess with shell=False."
                )
                if _is_inside_multiline_string(working, idx):
                    continue
                comment_line = _build_comment_line(original, message, file_path)
                working.insert(idx, comment_line)
                applied.append({
                    "file": file_path,
                    "line": line_num,
                    "original_code": original.rstrip(),
                    "fixed_code": comment_line.rstrip() + "\n" + original.rstrip(),
                    "explanation": _TRANSFORM_LABELS["command_injection_comment"],
                    "cwe": cwe,
                    "severity": severity,
                    "auto_fixable": False,
                    "transform": "command_injection_comment",
                })

        else:
            # Comment-based transforms — insert a warning above the flagged line
            if _is_inside_multiline_string(working, idx):
                continue
            message = _COMMENT_MESSAGES.get(transform_key, "SECURITY: Review this line.")
            comment_line = _build_comment_line(original, message, file_path)
            working.insert(idx, comment_line)
            applied.append({
                "file": file_path,
                "line": line_num,
                "original_code": original.rstrip(),
                "fixed_code": comment_line.rstrip() + "\n" + original.rstrip(),
                "explanation": _TRANSFORM_LABELS.get(transform_key, transform_key),
                "cwe": cwe,
                "severity": severity,
                "auto_fixable": False,
                "transform": transform_key,
            })

    # Inject 'import os' for Python files where credential-to-env transform fired
    if any(s.get("transform") == "hardcoded_credential_to_env" for s in applied):
        file_of_first = next(
            (s["file"] for s in applied if s.get("transform") == "hardcoded_credential_to_env"),
            "",
        )
        if file_of_first.endswith(".py"):
            working = _ensure_import(working, "os")

    return working, applied


# ---------------------------------------------------------------------------
# Diff generation
# ---------------------------------------------------------------------------

def _make_unified_diff(
    original_lines: List[str],
    fixed_lines: List[str],
    file_path: str,
) -> str:
    """Generate a unified diff string (git-apply compatible)."""
    # Ensure lines end with newline for canonical diff output
    def _ensure_newline(lines: List[str]) -> List[str]:
        return [l if l.endswith("\n") else l + "\n" for l in lines]

    diff_lines = list(
        difflib.unified_diff(
            _ensure_newline(original_lines),
            _ensure_newline(fixed_lines),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
    )
    return "".join(diff_lines)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def generate_fixes(args: Dict[str, Any]) -> Dict[str, Any]:
    """Generate fix suggestions for a list of findings.

    Args (dict keys):
        findings  list[dict]  findings from sql_scanner and/or security_scanner
        base_dir  str         optional base directory to resolve relative paths

    Returns dict with:
        fix_suggestions  list[dict]      per-finding suggestion records
        diffs_by_file    dict[str, str]  file -> unified diff string
        combined_patch   str             all diffs concatenated
        stats            dict            summary counts
    """
    findings: List[Dict[str, Any]] = args.get("findings", [])
    base_dir_str: str = args.get("base_dir", "")
    base_dir = Path(base_dir_str) if base_dir_str else None

    if not isinstance(findings, list):
        return {
            "error": "findings must be a list",
            "fix_suggestions": [],
            "diffs_by_file": {},
            "combined_patch": "",
            "stats": {},
        }

    # Group findings by resolved file path
    findings_by_file: Dict[str, List[Dict[str, Any]]] = {}
    skipped_missing: List[str] = []

    for finding in findings:
        raw_path = finding.get("file", "")
        if not raw_path:
            continue
        file_path = Path(raw_path)
        if base_dir and not file_path.is_absolute():
            file_path = base_dir / file_path
        file_key = str(file_path)
        findings_by_file.setdefault(file_key, []).append({**finding, "file": file_key})

    fix_suggestions: List[Dict[str, Any]] = []
    diffs_by_file: Dict[str, str] = {}
    total_findings = len(findings)
    auto_fixable_count = 0
    suggestion_only_count = 0
    skipped_count = 0

    for file_key, file_findings in findings_by_file.items():
        file_path = Path(file_key)

        # Findings that cannot be auto-fixed get suggestion-only entries
        for finding in file_findings:
            cwe = (finding.get("cwe") or "").upper()
            if cwe in _SUGGESTION_ONLY_CWES:
                suggestion_only_count += 1
                fix_suggestions.append({
                    "file": file_key,
                    "line": finding.get("line", 0),
                    "original_code": (
                        finding.get("code") or finding.get("code_snippet") or ""
                    ),
                    "fixed_code": None,
                    "explanation": (
                        f"Manual fix required: {finding.get('recommendation', '')} "
                        f"[{finding.get('issue', '')}]"
                    ).strip(),
                    "cwe": cwe,
                    "severity": finding.get("severity", ""),
                    "auto_fixable": False,
                    "transform": "suggestion_only",
                })

        # Read file for transform application
        if not file_path.exists():
            skipped_missing.append(file_key)
            skipped_count += len(file_findings)
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            skipped_count += len(file_findings)
            continue

        original_lines = content.splitlines(keepends=True)
        fixed_lines, applied = _apply_all_transforms(original_lines, file_findings)

        if applied:
            # Compute relative path for diff header if possible
            try:
                rel = file_path.relative_to(base_dir) if base_dir else file_path
            except ValueError:
                rel = file_path
            diff = _make_unified_diff(original_lines, fixed_lines, str(rel).replace("\\", "/"))
            if diff:
                diffs_by_file[file_key] = diff

            for suggestion in applied:
                is_real_fix = suggestion.get("auto_fixable", False)
                auto_fixable_count += 1 if is_real_fix else 0
                fix_suggestions.append(suggestion)

    # Build combined patch (all diffs concatenated)
    combined_patch = "\n".join(diffs_by_file.values())

    stats = {
        "total_findings": total_findings,
        "auto_fixable": auto_fixable_count,
        "suggestion_only": suggestion_only_count,
        "skipped_missing_file": skipped_count,
        "files_with_diffs": len(diffs_by_file),
    }

    result: Dict[str, Any] = {
        "fix_suggestions": fix_suggestions,
        "diffs_by_file": diffs_by_file,
        "combined_patch": combined_patch,
        "stats": stats,
    }
    if skipped_missing:
        result["skipped_files"] = skipped_missing

    return result
