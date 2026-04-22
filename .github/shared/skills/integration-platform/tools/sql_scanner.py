"""
SQL Injection Scanner Tool - Bank-Grade Edition

Provides comprehensive SQL injection vulnerability scanning capabilities.
Built for the unified Integration Platform MCP server.

Features:
- In-process AST analysis for Python files (no external processes, no data leaves)
- Extended regex pattern detection (6+ patterns across Python, Java, C#, PHP, SQL)
- ORM-aware detection: SQLAlchemy text(), Django .raw(), Hibernate HQL
- CWE-89 / CWE-564 mapping on all findings
- Severity differentiation: CRITICAL / HIGH / MEDIUM / LOW
- Parameterized query validation
- Text and HTML report generation
"""

import os
import re
import ast
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

# Disable logging to avoid interfering with MCP stdio protocol
logging.disable(logging.CRITICAL)

logger = logging.getLogger(__name__)


# ============================================================================
# Enhanced SQL Injection Pattern Detection
# ============================================================================

# ============================================================================
# SQL Injection Pattern Detection — Multi-Language
# ============================================================================

# Each entry: (regex_pattern, description, severity, cwe, recommendation)

_PYTHON_PATTERNS = [
    (
        r'(?:cursor|con|conn|db|connection)\s*\.\s*execute\s*\(\s*(?:f["\']|["\'].*\+)',
        "Direct string construction in cursor.execute()",
        "CRITICAL", "CWE-89",
        "Use cursor.execute('SELECT ... WHERE id = ?', (user_id,)) with parameters."
    ),
    (
        r'f["\'].*\b(?:SELECT\b.*\bFROM\b|INSERT\s+INTO\b|UPDATE\b.*\bSET\b|DELETE\s+FROM\b).*\{',
        "f-string interpolation in SQL query",
        "CRITICAL", "CWE-89",
        "Never interpolate variables into SQL strings. Use parameterized queries."
    ),
    (
        r'\b(?:SELECT\b.*\bFROM\b|INSERT\s+INTO\b|UPDATE\b.*\bSET\b|DELETE\s+FROM\b).*["\'\s]\s*%\s*(?:\w|\()',
        "%-format string interpolation in SQL query",
        "HIGH", "CWE-89",
        "Replace %-formatting with parameterized queries."
    ),
    (
        r'(?:\.raw\s*\(\s*f["\']|\.raw\s*\(\s*["\'].*\+)',
        "Django ORM .raw() with unsafe string construction",
        "CRITICAL", "CWE-89",
        "Use Django ORM QuerySet methods or pass params= argument to .raw()."
    ),
    (
        r'(?:text|sqlalchemy\.text)\s*\(\s*f["\']',
        "SQLAlchemy text() with f-string",
        "CRITICAL", "CWE-89",
        "Use text() with bindparams: db.execute(text('... WHERE id=:id'), {'id': val})"
    ),
    (
        r'(?:text|sqlalchemy\.text)\s*\(\s*["\'].*\+',
        "SQLAlchemy text() with string concatenation",
        "CRITICAL", "CWE-89",
        "Use text() with bindparams: db.execute(text('... WHERE id=:id'), {'id': val})"
    ),
    (
        r'\b(?:SELECT\b.*\bFROM\b|INSERT\s+INTO\b|UPDATE\b.*\bSET\b|DELETE\s+FROM\b).*\+\s*\w+',
        "Variable concatenated into SQL string",
        "HIGH", "CWE-89",
        "Use parameterized queries to prevent injection."
    ),
]

_JAVA_PATTERNS = [
    (
        r'["\'](?:SELECT|INSERT|UPDATE|DELETE)[^"\']*["\']\s*\+',
        "SQL string concatenation in Java",
        "CRITICAL", "CWE-89",
        "Use PreparedStatement: conn.prepareStatement('SELECT ... WHERE id=?')"
    ),
    (
        r'createQuery\s*\(\s*["\'].*\+',
        "JPA/Hibernate createQuery() with string concatenation",
        "CRITICAL", "CWE-564",
        "Use named parameters: createQuery('FROM User WHERE id=:id').setParameter('id', val)"
    ),
    (
        r'createNativeQuery\s*\(\s*["\'].*\+',
        "JPA createNativeQuery() with string concatenation",
        "CRITICAL", "CWE-89",
        "Use setParameter() with positional parameters."
    ),
]

_CSHARP_PATTERNS = [
    (
        r'new\s+SqlCommand\s*\(\s*["\'].*\+',
        "SqlCommand constructed with string concatenation",
        "CRITICAL", "CWE-89",
        "Use SqlCommand with SqlParameter: cmd.Parameters.AddWithValue('@id', id)"
    ),
    (
        r'CommandText\s*=\s*["\'].*\+',
        "CommandText assigned via string concatenation",
        "CRITICAL", "CWE-89",
        "Build SQL with parameterized placeholders (@param) and add SqlParameters."
    ),
    (
        r'string\.Format\s*\(\s*["\'].*\b(?:SELECT\b.*\bFROM\b|INSERT\s+INTO\b|UPDATE\b.*\bSET\b|DELETE\s+FROM\b)',
        "string.Format() used to build SQL command",
        "CRITICAL", "CWE-89",
        "Replace string.Format() SQL with SqlParameter-based queries."
    ),
    (
        r'\$["\'].*\b(?:SELECT\b.*\bFROM\b|INSERT\s+INTO\b|UPDATE\b.*\bSET\b|DELETE\s+FROM\b).*\{',
        "C# interpolated string used in SQL query",
        "CRITICAL", "CWE-89",
        "Never use C# string interpolation in SQL. Use SqlParameter instead."
    ),
]

_PHP_PATTERNS = [
    (
        r'mysql_query\s*\(',
        "mysql_query() used — deprecated and injectable",
        "CRITICAL", "CWE-89",
        "Use PDO with prepared statements or MySQLi with bind_param()."
    ),
    (
        r'mysqli_query\s*\([^,]+,\s*["\'].*\$',
        "mysqli_query() with interpolated variable",
        "CRITICAL", "CWE-89",
        "Use $stmt = $mysqli->prepare('... WHERE id=?'); $stmt->bind_param('i', $id);"
    ),
    (
        r'\$(?:pdo|db|conn|dbh)\s*->\s*query\s*\(["\'].*\$',
        "PDO->query() with variable interpolation",
        "CRITICAL", "CWE-89",
        "Use $pdo->prepare() + $stmt->execute([$var]) instead."
    ),
    (
        r'["\'](?:SELECT|INSERT|UPDATE|DELETE)[^"\']*["\']\s*\.\s*\$',
        "PHP string concatenation with variable into SQL",
        "CRITICAL", "CWE-89",
        "Use PDO prepared statements. Never concatenate PHP variables into SQL."
    ),
]

_SQL_FILE_PATTERNS = [
    (
        r'EXEC\s*\(\s*(?:[\'"][^\'"]*[\'"]|@\w+)\s*\+',
        "Dynamic SQL in EXEC() with concatenation",
        "CRITICAL", "CWE-89",
        "Use sp_executesql with @params instead of EXEC() with concatenation."
    ),
    (
        r'EXECUTE\s*\(\s*(?:[\'"][^\'"]*[\'"]|@\w+)\s*\+',
        "Dynamic SQL in EXECUTE() with concatenation",
        "CRITICAL", "CWE-89",
        "Use sp_executesql with parameterized queries."
    ),
    (
        r'SET\s+@\w+\s*=\s*[\'"][^\'\"]*[\'\"]\s*\+',
        "Dynamic SQL variable built via string concatenation in stored procedure",
        "HIGH", "CWE-89",
        "Use parameterized sp_executesql rather than building SQL strings dynamically."
    ),
]

# OData REST API injection patterns — applies to C#, JS, TS (Dynamics 365, SharePoint, etc.)
# Detects user-controlled variables interpolated directly into OData $filter / $search / $orderby queries.
# CWE-89 applies because OData filter injection allows the same logical attacks as SQL injection
# (tautologies, unauthorized data access, field enumeration).
_ODATA_PATTERNS = [
    (
        r'\$["\'][^"\']*\$(?:filter|search|orderby|apply)\b[^"\']*\{',
        "C# interpolated string with user input in OData $filter/$search/$orderby query",
        "HIGH", "CWE-89",
        "Validate field names against a whitelist. Escape single quotes in values: value.Replace(\"'\", \"''\"). "
        "Consider using a typed OData client (e.g. Microsoft.OData.Client) with strongly-typed expressions."
    ),
    (
        r'["\'][^"\']*\$(?:filter|search|orderby)\b[^"\']*["\'\s]*\+\s*\w',
        "OData query string built via string concatenation",
        "HIGH", "CWE-89",
        "Never concatenate user input into OData $filter. Validate field names against a whitelist "
        "and escape single quotes in values: value.Replace(\"'\", \"''\")."
    ),
    (
        r'string\.Format\s*\(\s*["\'][^"\']*\$(?:filter|search|orderby)\b',
        "OData query string built with string.Format()",
        "HIGH", "CWE-89",
        "Use strongly-typed OData query builders or sanitize all inputs before embedding in $filter."
    ),
]

_PATTERNS_BY_EXT: Dict[str, List] = {
    '.py':   _PYTHON_PATTERNS,
    '.java': _JAVA_PATTERNS,
    '.cs':   _CSHARP_PATTERNS + _ODATA_PATTERNS,
    '.php':  _PHP_PATTERNS,
    '.sql':  _SQL_FILE_PATTERNS,
    '.js':   _ODATA_PATTERNS,
    '.ts':   _ODATA_PATTERNS,
}

_GENERIC_PATTERNS = [
    (
        r'\b(?:SELECT\b.*\bFROM\b|INSERT\s+INTO\b|UPDATE\b.*\bSET\b|DELETE\s+FROM\b).*\+\s*[\w$]',
        "SQL string concatenation with variable",
        "HIGH", "CWE-89",
        "Use parameterized queries specific to your language/framework."
    ),
]

# Patterns that detect dangerous SQL snippets in string literals / input values
# (used to detect second-order, tautology, and time-based injection indicators)
_INDICATOR_PATTERNS = [
    (
        r"(?:'\s*OR\s*'1'\s*=\s*'1|'\s*OR\s*1\s*=\s*1|or\s+1\s*=\s*1)",
        "Authentication bypass tautology pattern detected (OR 1=1)",
        "CRITICAL", "CWE-89",
        "Ensure this string value is not passed to a SQL query without parameterization."
    ),
    (
        r"(?:(?<![.\w])SLEEP\s*\(\s*\d+|WAITFOR\s+DELAY\s*'|BENCHMARK\s*\(\s*\d+)",
        "Time-based blind SQL injection indicator (SLEEP/WAITFOR/BENCHMARK)",
        "CRITICAL", "CWE-89",
        "Input containing SQL time-delay functions must never reach a query. Validate and reject."
    ),
    (
        r"(?:UNION\s+(?:ALL\s+)?SELECT|UNION/\*.*\*/SELECT)",
        "UNION-based injection payload detected in source string",
        "CRITICAL", "CWE-89",
        "Ensure UNION SELECT strings in code are not passed to queries as user input."
    ),
    (
        r"(?:;\s*(?:DROP|ALTER|CREATE|EXEC|EXECUTE)\s+)",
        "Stacked query / DDL injection payload detected",
        "CRITICAL", "CWE-89",
        "Never allow stacked queries via user input. Use parameterized queries and input validation."
    ),
]

SUPPORTED_EXTENSIONS = {'.py', '.js', '.ts', '.sql', '.cs', '.java', '.php'}

_COMMENT_PREFIXES = ('#', '//', '--', '/*', '*')


def _scan_code_with_regex(code: str, filename: str) -> List[Dict[str, Any]]:
    """
    Scan source code lines for SQL injection patterns using language-aware regex.
    Returns list of findings with line, severity, and CWE mapping.
    """
    ext = os.path.splitext(filename)[1].lower()
    lang_patterns = _PATTERNS_BY_EXT.get(ext, []) + _GENERIC_PATTERNS

    findings = []
    lines = code.splitlines()
    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if any(stripped.startswith(p) for p in _COMMENT_PREFIXES):
            continue
        if not stripped:
            continue
        for pattern, description, severity, cwe, recommendation in lang_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                findings.append({
                    "file": filename,
                    "line": line_num,
                    "code_snippet": line.strip()[:120],
                    "issue": description,
                    "severity": severity,
                    "cwe": cwe,
                    "recommendation": recommendation,
                    "source": "regex"
                })
                break

    # Pass 2: indicator patterns (apply to all languages)
    seen_lines = {f['line'] for f in findings}
    for line_num, line in enumerate(lines, start=1):
        if line_num in seen_lines:
            continue
        stripped = line.strip()
        if any(stripped.startswith(p) for p in _COMMENT_PREFIXES) or not stripped:
            continue
        for pattern, description, severity, cwe, recommendation in _INDICATOR_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                findings.append({
                    "file": filename,
                    "line": line_num,
                    "code_snippet": line.strip()[:120],
                    "issue": description,
                    "severity": severity,
                    "cwe": cwe,
                    "recommendation": recommendation,
                    "source": "regex-indicator"
                })
                break
    return findings


# SQL keyword regex used by AST scanner (same logic as Bandit B608)
_SQL_KEYWORD_RE = re.compile(
    r"(select\s.*from\s|"
    r"delete\s+from\s|"
    r"insert\s+into\s.*values[\s(]|"
    r"update\s.*set\s)",
    re.IGNORECASE | re.DOTALL,
)

# Names of DB execute functions
_EXECUTE_NAMES = {"execute", "executemany", "raw", "query"}


def _ast_contains_sql(node: ast.AST) -> bool:
    """Check if an AST node's string content looks like a SQL statement."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return _SQL_KEYWORD_RE.search(node.value) is not None
    return False


def _get_call_name(node: ast.Call) -> str:
    """Extract the function name from a Call node."""
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return ""


def _is_execute_call(node: ast.AST) -> bool:
    """Return True if node is a call to execute/executemany/raw/query."""
    return isinstance(node, ast.Call) and _get_call_name(node) in _EXECUTE_NAMES


def _scan_python_ast(code: str, file_path: str) -> List[Dict[str, Any]]:
    """
    In-process AST scanner for Python files — equivalent to Bandit B608.

    Detects unsafe SQL construction patterns:
    - BinOp (+):           "SELECT * FROM t WHERE id=" + user_id
    - JoinedStr (f-string): f"SELECT * FROM t WHERE id={user_id}"
    - .format():           "SELECT * FROM t WHERE id={}".format(user_id)
    - .replace():          "SELECT [V] FROM t".replace("[V]", user_id)

    Assigns CRITICAL when found inside execute(), HIGH otherwise.
    All findings map to CWE-89.
    """
    findings = []
    try:
        tree = ast.parse(code, filename=file_path)
    except SyntaxError:
        return findings  # Not valid Python — skip

    # Walk every string-like node
    for node in ast.walk(tree):
        statement = ""
        build_method = ""
        in_execute = False

        # Pattern 1: BinOp — "SQL" + variable
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            parent = getattr(node, '_parent', None)
            if isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Add):
                statement = node.value
                build_method = "string concatenation (+)"
                grandparent = getattr(parent, '_parent', None)
                in_execute = _is_execute_call(grandparent) if grandparent else False

        # Pattern 2: f-string — f"SELECT...{var}"
        elif isinstance(node, ast.JoinedStr):
            parts = [
                child.value for child in node.values
                if isinstance(child, ast.Constant) and isinstance(child.value, str)
            ]
            statement = "".join(parts)
            build_method = "f-string interpolation"
            parent = getattr(node, '_parent', None)
            in_execute = _is_execute_call(parent) if parent else False

        # Pattern 3: .format() and .replace()
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            parent = getattr(node, '_parent', None)
            if isinstance(parent, ast.Attribute) and parent.attr in ("format", "replace"):
                statement = node.value
                build_method = f"string .{parent.attr}()"
                grandparent = getattr(parent, '_parent', None)
                call_node = getattr(grandparent, '_parent', None)
                in_execute = _is_execute_call(call_node) if call_node else False

        if statement and _SQL_KEYWORD_RE.search(statement):
            severity = "CRITICAL" if in_execute else "HIGH"
            findings.append({
                "file": file_path,
                "line": getattr(node, 'lineno', 0),
                "code_snippet": statement[:120].strip(),
                "issue": f"Unsafe SQL construction via {build_method}",
                "severity": severity,
                "cwe": "CWE-89",
                "recommendation": (
                    "Replace with parameterized queries: "
                    "cursor.execute('SELECT ... WHERE id = ?', (user_id,))"
                ),
                "source": "ast"
            })

    # Set parent references so parent checks work on re-walks
    # (done after initial walk so all nodes exist)
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child._parent = node  # type: ignore[attr-defined]

    # Re-run findings with parent info now that _parent is set
    return _scan_python_ast_with_parents(code, file_path, tree)


def _scan_python_ast_with_parents(
    code: str, file_path: str, tree: ast.Module
) -> List[Dict[str, Any]]:
    """Second pass over pre-parsed tree that already has _parent set."""
    findings = []
    seen_lines: set = set()

    for node in ast.walk(tree):

        statement = ""
        build_method = ""
        in_execute = False
        lineno = getattr(node, 'lineno', 0)

        # Pattern 1: BinOp string concatenation
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            parent = getattr(node, '_parent', None)
            if isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Add):
                statement = node.value
                build_method = "string concatenation (+)"
                gp = getattr(parent, '_parent', None)
                in_execute = _is_execute_call(gp) if gp else False

        # Pattern 2: f-string
        if isinstance(node, ast.JoinedStr):
            parts = [
                child.value for child in node.values
                if isinstance(child, ast.Constant) and isinstance(child.value, str)
            ]
            statement = "".join(parts)
            build_method = "f-string interpolation"
            parent = getattr(node, '_parent', None)
            in_execute = _is_execute_call(parent) if parent else False

        # Pattern 3: .format() / .replace()
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            parent = getattr(node, '_parent', None)
            if isinstance(parent, ast.Attribute) and parent.attr in ("format", "replace"):
                statement = node.value
                build_method = f"string .{parent.attr}()"
                gp = getattr(parent, '_parent', None)  # the Call node
                ggp = getattr(gp, '_parent', None)      # wrapping call
                in_execute = _is_execute_call(ggp) if ggp else False

        if statement and _SQL_KEYWORD_RE.search(statement) and lineno not in seen_lines:
            seen_lines.add(lineno)
            severity = "CRITICAL" if in_execute else "HIGH"
            findings.append({
                "file": file_path,
                "line": lineno,
                "code_snippet": statement[:120].strip(),
                "issue": f"Unsafe SQL construction via {build_method}",
                "severity": severity,
                "cwe": "CWE-89",
                "recommendation": (
                    "Replace with parameterized queries: "
                    "cursor.execute('SELECT ... WHERE id = ?', (user_id,))"
                ),
                "source": "ast"
            })

    return findings


# ============================================================================
# MCP Tool Handlers
# ============================================================================

def scan_sql_injection_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP tool handler: Scan a single file for SQL injection vulnerabilities.

    Uses language-aware regex scanning for all supported files and in-process
    AST analysis for Python files.
    
    Args:
        args: Dictionary containing 'file_path' key
        
    Returns:
        Scan results dictionary with findings, file info, and clean status
    """
    file_path = args.get("file_path")
    
    if not file_path:
        return {"success": False, "error": "file_path is required"}
    
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}
    
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return {
            "success": True,
            "file": file_path,
            "skipped": True,
            "reason": f"Unsupported file type: {ext}",
            "findings": []
        }
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        
        findings = _scan_code_with_regex(code, file_path)

        # In-process AST analysis for Python files (no subprocess, no external calls)
        if ext == '.py':
            ast_findings = _scan_python_ast(code, file_path)
            # Merge by line number, keeping the finding with higher severity
            _sev_rank = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
            merged: Dict[int, Dict[str, Any]] = {}
            for finding in findings + ast_findings:
                line = finding.get('line', 0)
                existing = merged.get(line)
                if existing is None:
                    merged[line] = finding
                else:
                    if _sev_rank.get(finding['severity'], 0) > _sev_rank.get(existing['severity'], 0):
                        merged[line] = finding
            findings = list(merged.values())
        
        return {
            "success": True,
            "file": file_path,
            "total_findings": len(findings),
            "findings": findings,
            "is_clean": len(findings) == 0
        }
    
    except Exception as e:
        logger.error(f"Error scanning file {file_path}: {str(e)}")
        return {"success": False, "error": str(e)}


def scan_sql_injection_directory(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP tool handler: Scan all supported source files in a directory.
    
    Args:
        args: Dictionary containing 'directory_path' and optional 'recursive' keys
        
    Returns:
        Consolidated scan results with findings grouped by severity
    """
    directory_path = args.get("directory_path")
    recursive = args.get("recursive", True)
    
    if not directory_path:
        return {"success": False, "error": "directory_path is required"}
    
    if not os.path.exists(directory_path):
        return {"success": False, "error": f"Directory not found: {directory_path}"}
    
    if not os.path.isdir(directory_path):
        return {"success": False, "error": f"Path is not a directory: {directory_path}"}
    
    try:
        all_findings = []
        files_scanned = []
        files_skipped = []
        
        # Iterate through files
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
            
            # Skip generated, build, and vendor directories
            parts = file_path.replace('\\', '/').split('/')
            _SKIP_DIRS = {
                'venv', '.venv', '__pycache__', 'node_modules', '.git',
                # .NET build output
                'bin', 'obj',
                # DocFX / static site generators
                '_site',
                # Common vendor/generated JS bundles
                'vendor', 'dist', 'wwwroot',
            }
            if any(p in _SKIP_DIRS for p in parts):
                files_skipped.append(file_path)
                continue

            # Skip minified files (*.min.js, *.min.css) — always vendor/generated
            if os.path.basename(file_path).endswith(('.min.js', '.min.css')):
                files_skipped.append(file_path)
                continue
            
            result = scan_sql_injection_file({"file_path": file_path})
            files_scanned.append(file_path)
            if result.get('findings'):
                all_findings.extend(result['findings'])
        
        # Group by severity
        critical = [f for f in all_findings if f.get('severity') == 'CRITICAL']
        high = [f for f in all_findings if f.get('severity') == 'HIGH']
        medium = [f for f in all_findings if f.get('severity') == 'MEDIUM']
        
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
        logger.error(f"Error scanning directory {directory_path}: {str(e)}")
        return {"success": False, "error": str(e)}


def check_parameterized_query(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP tool handler: Check whether a SQL code snippet uses safe parameterized queries.
    
    Args:
        args: Dictionary containing 'code_snippet' key
        
    Returns:
        Analysis with safety verdict and recommendations
    """
    code_snippet = args.get("code_snippet")
    
    if not code_snippet:
        return {"success": False, "error": "code_snippet is required"}
    
    try:
        safe_patterns = [
            (r'\?',                         "Positional placeholder (?)"),
            (r':\w+',                        "Named placeholder (:param)"),
            (r'%\s*\(',                      "PyFormat style %(name)s"),
            (r'\$\d+',                       "Numbered placeholder ($1)"),
            (r'\.filter\(|\.where\(|\.query\(', "ORM-style (SQLAlchemy / Django)"),
        ]
        
        unsafe_patterns = [
            (r'f["\'].*\b(?:SELECT\b.*\bFROM\b|INSERT\s+INTO\b|UPDATE\b.*\bSET\b|DELETE\s+FROM\b)', "f-string SQL"),
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
        logger.error(f"Error checking parameterized query: {str(e)}")
        return {"success": False, "error": str(e)}


def generate_scan_report(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP tool handler: Generate a human-readable security report from scan findings.
    
    Args:
        args: Dictionary containing 'findings' list and optional 'output_format' key
              output_format can be: 'text' | 'json' | 'summary'
        
    Returns:
        Generated report as text
    """
    findings = args.get("findings", [])
    output_format = args.get("output_format", "text")
    
    try:
        if not findings:
            report = "✅ No SQL injection vulnerabilities found. Code is clean."
            return {"success": True, "report": report, "total": 0}
        
        critical = [f for f in findings if f.get('severity') == 'CRITICAL']
        high     = [f for f in findings if f.get('severity') == 'HIGH']
        medium   = [f for f in findings if f.get('severity') == 'MEDIUM']
        low      = [f for f in findings if f.get('severity') == 'LOW']
        other    = [f for f in findings if f.get('severity') not in ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')]

        if output_format == "json":
            return {"success": True, "report": json.dumps(findings, indent=2), "total": len(findings)}

        if output_format == "summary":
            report = (
                f"🔒 SQL Injection Scan Summary\n"
                f"{'='*40}\n"
                f"Total findings : {len(findings)}\n"
                f"  🚨 CRITICAL  : {len(critical)}\n"
                f"  🔴 HIGH      : {len(high)}\n"
                f"  🟡 MEDIUM    : {len(medium)}\n"
                f"  🔵 LOW       : {len(low)}\n"
            )
            return {"success": True, "report": report, "total": len(findings)}

        # Full text report
        report_lines = [
            "🔒 SQL Injection Security Report",
            "=" * 60,
            f"Total vulnerabilities found: {len(findings)}",
            f"  🚨 CRITICAL: {len(critical)}  🔴 HIGH: {len(high)}  🟡 MEDIUM: {len(medium)}  🔵 LOW: {len(low)}",
            ""
        ]

        for severity, group, icon in [
            ("CRITICAL", critical, "🚨"),
            ("HIGH",     high,     "🔴"),
            ("MEDIUM",   medium,   "🟡"),
            ("LOW",      low,      "🔵"),
            ("OTHER",    other,    "⚪"),
        ]:
            if group:
                report_lines.append(f"{icon} {severity} ({len(group)} issues)")
                report_lines.append("-" * 50)
                for finding in group:
                    report_lines.append(f"  File   : {finding.get('file', 'unknown')}")
                    report_lines.append(f"  Line   : {finding.get('line', '?')}")
                    report_lines.append(f"  CWE    : {finding.get('cwe', 'CWE-89')}")
                    report_lines.append(f"  Issue  : {finding.get('issue', '')}")
                    report_lines.append(f"  Code   : {finding.get('code_snippet', '')}")
                    report_lines.append(f"  Fix    : {finding.get('recommendation', '')}")
                    report_lines.append("")

        return {"success": True, "report": "\n".join(report_lines), "total": len(findings)}
    
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return {"success": False, "error": str(e)}


def generate_html_report(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP tool handler: Generate an HTML security report from scan findings.
    
    Args:
        args: Dictionary containing:
            - 'findings': List of vulnerability findings
            - 'output_file': Path to write HTML report
            - 'scan_path': Path that was scanned (for display)
    
    Returns:
        Dict with success status and output file path
    """
    findings = args.get("findings", [])
    output_file = args.get("output_file")
    scan_path = args.get("scan_path", ".")
    
    if not output_file:
        return {"success": False, "error": "output_file is required"}
    
    try:
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
            <p>Generated by Integration Platform MCP Server - SQL Scanner</p>
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
        logger.error(f"Error generating HTML report: {str(e)}")
        return {"success": False, "error": str(e)}
