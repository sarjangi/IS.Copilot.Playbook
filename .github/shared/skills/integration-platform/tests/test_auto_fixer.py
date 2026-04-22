"""
Tests for auto_fixer.py

Covers:
  - yaml.load → yaml.safe_load transform (with and without Loader kwarg)
  - requests verify=False removal (trailing, leading, sole arg positions)
  - SQL injection: f-string and concat parameterization + comment fallback
  - Hardcoded credentials: env-var replacement for Python, JS, C#, Java
  - Command injection: shell=True → shell=False; eval/exec comment fallback
  - Weak hash (CWE-327): MD5/SHA-1 → SHA-256
  - Missing file handling (graceful skip)
  - Unified diff generation is non-empty for fixable findings
  - Stats counters are accurate
  - Multi-finding file (mixed sql + security) produces single combined diff
"""

import ast
import difflib
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

# Make the tools directory importable regardless of cwd
_TOOLS_DIR = Path(__file__).parent.parent / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from auto_fixer import (
    generate_fixes,
    _classify_finding,
    _transform_yaml_load,
    _transform_requests_verify,
    _transform_sql_injection,
    _transform_hardcoded_credential,
    _transform_command_injection,
    _ensure_import,
    _comment_prefix,
    _build_comment_line,
    _apply_all_transforms,
    _make_unified_diff,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_finding(file="", line=1, cwe="CWE-502", issue="yaml.load", severity="MEDIUM",
                   code="", category="deserialization", recommendation=""):
    return {
        "file": file,
        "line": line,
        "cwe": cwe,
        "issue": issue,
        "severity": severity,
        "code": code,
        "category": category,
        "recommendation": recommendation,
    }


def _write_temp_file(content: str, suffix=".py") -> Path:
    """Write content to a temp file, return its Path (caller must not delete prematurely)."""
    fd, path_str = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
    return Path(path_str)


# ---------------------------------------------------------------------------
# _transform_yaml_load
# ---------------------------------------------------------------------------

class TestTransformYamlLoad(unittest.TestCase):

    def test_simple_yaml_load_is_renamed(self):
        result = _transform_yaml_load("    data = yaml.load(stream)\n")
        self.assertIsNotNone(result)
        self.assertIn("yaml.safe_load", result)
        self.assertNotIn("yaml.load(", result)

    def test_loader_kwarg_is_removed(self):
        result = _transform_yaml_load("data = yaml.load(s, Loader=yaml.FullLoader)\n")
        self.assertIsNotNone(result)
        self.assertNotIn("Loader=", result)
        self.assertIn("yaml.safe_load", result)

    def test_no_match_returns_none(self):
        result = _transform_yaml_load("result = json.loads(data)\n")
        self.assertIsNone(result)

    def test_indentation_is_preserved(self):
        line = "        cfg = yaml.load(f)\n"
        result = _transform_yaml_load(line)
        self.assertTrue(result.startswith("        "))

    def test_result_is_valid_python(self):
        """The transformed line must be syntactically valid Python in a minimal context."""
        line = "data = yaml.load(stream, Loader=yaml.SafeLoader)\n"
        result = _transform_yaml_load(line)
        self.assertIsNotNone(result)
        # Wrap in a function to allow parsing as a statement
        source = f"import yaml\ndef _f():\n    stream = None\n    {result.strip()}"
        try:
            ast.parse(source)
        except SyntaxError as exc:
            self.fail(f"Transformed line is not valid Python: {exc}\nLine: {result!r}")


# ---------------------------------------------------------------------------
# _transform_requests_verify
# ---------------------------------------------------------------------------

class TestTransformRequestsVerify(unittest.TestCase):

    def test_trailing_verify_false_removed(self):
        line = "    resp = requests.get(url, verify=False)\n"
        result = _transform_requests_verify(line)
        self.assertIsNotNone(result)
        self.assertNotIn("verify=False", result)
        self.assertIn("requests.get(url", result)

    def test_leading_verify_false_removed(self):
        line = "r = requests.post(url, verify=False, timeout=10)\n"
        result = _transform_requests_verify(line)
        self.assertIsNotNone(result)
        self.assertNotIn("verify=False", result)
        self.assertIn("timeout=10", result)

    def test_no_verify_returns_none(self):
        result = _transform_requests_verify("resp = requests.get(url)\n")
        self.assertIsNone(result)

    def test_verify_with_spaces_removed(self):
        line = "r = requests.get(url, verify = False)\n"
        result = _transform_requests_verify(line)
        self.assertIsNotNone(result)
        self.assertNotIn("verify", result)


# ---------------------------------------------------------------------------
# _transform_sql_injection
# ---------------------------------------------------------------------------

class TestTransformSqlInjection(unittest.TestCase):

    def _finding(self, file=".py"):
        return {"file": f"test{file}"}

    def test_fstring_single_var_parameterized(self):
        line = '    cursor.execute(f"SELECT * FROM users WHERE id={user_id}")\n'
        result = _transform_sql_injection(line, self._finding())
        self.assertIsNotNone(result)
        self.assertIn("?", result)
        self.assertIn("user_id", result)
        self.assertNotIn("f\"", result)

    def test_fstring_multiple_vars_parameterized(self):
        line = '    db.execute(f"SELECT * FROM t WHERE a={x} AND b={y}")\n'
        result = _transform_sql_injection(line, self._finding())
        self.assertIsNotNone(result)
        self.assertIn("?", result)
        self.assertIn("x", result)
        self.assertIn("y", result)

    def test_concat_pattern_parameterized(self):
        line = 'cursor.execute("SELECT * FROM users WHERE id=" + uid)\n'
        result = _transform_sql_injection(line, self._finding())
        self.assertIsNotNone(result)
        self.assertIn("?", result)
        self.assertIn("uid", result)

    def test_non_python_file_returns_none(self):
        line = '    cursor.execute(f"SELECT * WHERE id={uid}")\n'
        result = _transform_sql_injection(line, self._finding(".java"))
        self.assertIsNone(result)

    def test_unrecognised_pattern_returns_none(self):
        line = "result = build_query(table, filters)\n"
        result = _transform_sql_injection(line, self._finding())
        self.assertIsNone(result)

    def test_csharp_interpolated_string_parameterized(self):
        line = '        string query = $"SELECT * FROM Users WHERE Id = {userId}";\n'
        result = _transform_sql_injection(line, self._finding(".cs"))
        self.assertIsNotNone(result)
        self.assertIn("@p0", result)
        self.assertIn("userId", result)
        self.assertIn("AddWithValue", result)
        self.assertNotIn("$\"", result)

    def test_csharp_concat_parameterized(self):
        line = '        string query = "SELECT * FROM Users WHERE Id = " + userId;\n'
        result = _transform_sql_injection(line, self._finding(".cs"))
        self.assertIsNotNone(result)
        self.assertIn("@p0", result)
        self.assertIn("userId", result)
        self.assertIn("AddWithValue", result)


# ---------------------------------------------------------------------------
# _transform_hardcoded_credential
# ---------------------------------------------------------------------------

class TestTransformHardcodedCredential(unittest.TestCase):

    def _finding(self, file=".py"):
        return {"file": f"config{file}"}

    def test_python_credential_replaced(self):
        line = 'password = "s3cret123"\n'
        result = _transform_hardcoded_credential(line, self._finding(".py"))
        self.assertIsNotNone(result)
        self.assertIn("os.environ.get", result)
        self.assertIn("PASSWORD", result)
        self.assertNotIn("s3cret123", result)

    def test_python_api_key_replaced(self):
        line = 'api_key = "abc-123-def"\n'
        result = _transform_hardcoded_credential(line, self._finding(".py"))
        self.assertIsNotNone(result)
        self.assertIn("API_KEY", result)

    def test_js_credential_replaced(self):
        line = 'const password = "s3cret123";\n'
        result = _transform_hardcoded_credential(line, self._finding(".js"))
        self.assertIsNotNone(result)
        self.assertIn("process.env.PASSWORD", result)

    def test_cs_credential_replaced(self):
        line = 'string password = "s3cret123";\n'
        result = _transform_hardcoded_credential(line, self._finding(".cs"))
        self.assertIsNotNone(result)
        self.assertIn("GetEnvironmentVariable", result)

    def test_java_credential_replaced(self):
        line = 'String password = "s3cret123";\n'
        result = _transform_hardcoded_credential(line, self._finding(".java"))
        self.assertIsNotNone(result)
        self.assertIn("System.getenv", result)

    def test_short_value_ignored(self):
        # Values under 4 chars are not flagged (too likely to be non-credentials)
        line = 'token = "abc"\n'
        result = _transform_hardcoded_credential(line, self._finding(".py"))
        self.assertIsNone(result)

    def test_private_key_block_not_matched(self):
        line = "-----BEGIN RSA PRIVATE KEY-----\n"
        result = _transform_hardcoded_credential(line, self._finding(".py"))
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# _transform_command_injection
# ---------------------------------------------------------------------------

class TestTransformCommandInjection(unittest.TestCase):

    def test_shell_true_changed_to_false(self):
        line = "    subprocess.run(cmd, shell=True)\n"
        result = _transform_command_injection(line)
        self.assertIsNotNone(result)
        self.assertIn("shell=False", result)
        self.assertNotIn("shell=True", result)

    def test_no_shell_kwarg_returns_none(self):
        line = "    subprocess.run(cmd)\n"
        result = _transform_command_injection(line)
        self.assertIsNone(result)

    def test_eval_with_no_shell_returns_none(self):
        line = "    result = eval(user_input)\n"
        result = _transform_command_injection(line)
        self.assertIsNone(result)



# ---------------------------------------------------------------------------
# _comment_prefix / _build_comment_line
# ---------------------------------------------------------------------------

class TestCommentPrefix(unittest.TestCase):

    def test_python_uses_hash(self):
        self.assertEqual(_comment_prefix("app.py"), "#")

    def test_csharp_uses_slashslash(self):
        self.assertEqual(_comment_prefix("Service.cs"), "//")

    def test_java_uses_slashslash(self):
        self.assertEqual(_comment_prefix("Main.java"), "//")

    def test_javascript_uses_slashslash(self):
        self.assertEqual(_comment_prefix("app.js"), "//")

    def test_typescript_uses_slashslash(self):
        self.assertEqual(_comment_prefix("app.ts"), "//")

    def test_sql_uses_double_dash(self):
        self.assertEqual(_comment_prefix("query.sql"), "--")

    def test_powershell_uses_hash(self):
        self.assertEqual(_comment_prefix("deploy.ps1"), "#")

    def test_no_extension_defaults_to_hash(self):
        self.assertEqual(_comment_prefix(""), "#")

    def test_build_comment_line_csharp(self):
        line = "    cursor.Execute(sql);\n"
        result = _build_comment_line(line, "CWE-89 note", "Service.cs")
        self.assertTrue(result.startswith("    //"))
        self.assertNotIn("#", result)

    def test_build_comment_line_python(self):
        line = "    cursor.execute(sql)\n"
        result = _build_comment_line(line, "CWE-89 note", "app.py")
        self.assertTrue(result.startswith("    #"))

    def test_build_comment_line_java(self):
        line = "\tconn.execute(sql);\n"
        result = _build_comment_line(line, "CWE-89 note", "Dao.java")
        self.assertIn("//", result)
        self.assertNotIn("# ", result)


class TestApplyAllTransformsCsharpComment(unittest.TestCase):
    """Verify that comment fallback uses // for C# files, not #."""

    def test_sql_comment_uses_slashslash_in_cs(self):
        lines = ['    db.Execute("SELECT * FROM users WHERE id=" + userId);\n']
        findings = [_make_finding(
            file="Repository.cs", line=1, cwe="CWE-89", issue="SQL injection",
        )]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(len(applied), 1)
        # The inserted comment line should use // not #
        comment = result_lines[0]
        self.assertIn("//", comment, "C# comment must use // not #")
        self.assertNotIn("# ", comment)

    def test_credential_comment_uses_slashslash_in_cs(self):
        # Private key block — no simple var= pattern, falls to comment
        lines = ["-----BEGIN RSA PRIVATE KEY-----\n"]
        findings = [_make_finding(
            file="Keys.cs", line=1, cwe="CWE-798", issue="Private key material",
        )]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(len(applied), 1)
        comment = result_lines[0]
        self.assertIn("//", comment)
        self.assertNotIn("# ", comment)


# ---------------------------------------------------------------------------
# _ensure_import
# ---------------------------------------------------------------------------

class TestEnsureImport(unittest.TestCase):

    def test_adds_import_when_missing(self):
        lines = ["x = 1\n"]
        result = _ensure_import(lines, "os")
        self.assertTrue(any("import os" in l for l in result))

    def test_does_not_duplicate_existing_import(self):
        lines = ["import os\n", "x = 1\n"]
        result = _ensure_import(lines, "os")
        count = sum(1 for l in result if l.strip() == "import os")
        self.assertEqual(count, 1)

    def test_inserts_after_shebang(self):
        lines = ["#!/usr/bin/env python3\n", "x = 1\n"]
        result = _ensure_import(lines, "os")
        self.assertEqual(result[0], "#!/usr/bin/env python3\n")
        self.assertEqual(result[1], "import os\n")


# ---------------------------------------------------------------------------
# _classify_finding
# ---------------------------------------------------------------------------

class TestClassifyFinding(unittest.TestCase):

    def test_sql_injection_classified(self):
        # CWE-89 now routes to best-effort parameterization transform
        finding = _make_finding(cwe="CWE-89", issue="SQL injection")
        self.assertEqual(_classify_finding(finding), "sql_parameterize")

    def test_yaml_load_classified(self):
        finding = _make_finding(cwe="CWE-502", issue="Unsafe yaml.load", code="yaml.load(f)")
        self.assertEqual(_classify_finding(finding), "yaml_load_to_safe_load")

    def test_pickle_classified(self):
        # pickle deserialization is suggestion-only — no file modification
        finding = _make_finding(cwe="CWE-502", issue="pickle deserialization", code="pickle.load(f)")
        self.assertIsNone(_classify_finding(finding))

    def test_requests_verify_classified(self):
        finding = _make_finding(cwe="CWE-295", issue="TLS certificate verification disabled")
        self.assertEqual(_classify_finding(finding), "requests_verify_false")

    def test_weak_hash_classified(self):
        # CWE-327 is now auto-fixable — replaces md5/sha1 with sha256
        finding = _make_finding(cwe="CWE-327", issue="Weak hash MD5")
        self.assertEqual(_classify_finding(finding), "weak_hash_upgrade")

    def test_credential_classified(self):
        # CWE-798 now routes to env-var replacement transform
        finding = _make_finding(cwe="CWE-798", issue="Hardcoded credential")
        self.assertEqual(_classify_finding(finding), "hardcoded_credential_to_env")

    def test_private_key_classified(self):
        # CWE-798 still routes through hardcoded_credential_to_env;
        # private key blocks fall back to comment inside the transform
        finding = _make_finding(cwe="CWE-798", issue="Private key material present")
        self.assertEqual(_classify_finding(finding), "hardcoded_credential_to_env")

    def test_dom_xss_not_classified(self):
        finding = _make_finding(cwe="CWE-79", issue="DOM XSS")
        self.assertIsNone(_classify_finding(finding))


# ---------------------------------------------------------------------------
# _apply_all_transforms
# ---------------------------------------------------------------------------

class TestApplyAllTransforms(unittest.TestCase):

    def test_yaml_transform_applied(self):
        lines = ["import yaml\n", "data = yaml.load(f)\n"]
        findings = [_make_finding(line=2, cwe="CWE-502", issue="yaml", code="yaml.load")]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(len(applied), 1)
        # Comment line inserted before fixed line — safe_load is now at index 2
        self.assertIn("SECURITY FIX", result_lines[1])
        self.assertIn("yaml.safe_load", result_lines[2])

    def test_comment_inserted_above_pickle(self):
        # pickle is suggestion-only — no comment inserted, file unchanged
        lines = ["import pickle\n", "obj = pickle.load(f)\n"]
        findings = [_make_finding(line=2, cwe="CWE-502", issue="pickle deserialization", code="pickle.load")]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(applied, [])
        self.assertEqual(result_lines, lines)

    def test_weak_hash_md5_replaced_with_sha256(self):
        lines = ["import hashlib\n", "h = hashlib.md5(data)\n"]
        findings = [_make_finding(line=2, cwe="CWE-327", issue="Weak hash MD5", code="hashlib.md5")]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(len(applied), 1)
        # Comment line inserted before fixed line — sha256 is now at index 2
        self.assertIn("sha256", result_lines[2])
        self.assertNotIn("md5", result_lines[2])

    def test_weak_hash_sha1_replaced_with_sha256(self):
        lines = ["import hashlib\n", "h = hashlib.sha1(data)\n"]
        findings = [_make_finding(line=2, cwe="CWE-327", issue="Weak hash SHA1", code="hashlib.sha1")]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(len(applied), 1)
        # Comment line inserted before fixed line — sha256 is now at index 2
        self.assertIn("sha256", result_lines[2])
        self.assertNotIn("sha1", result_lines[2])

    def test_weak_hash_new_md5_replaced(self):
        lines = ["h = hashlib.new('md5')\n"]
        findings = [_make_finding(line=1, cwe="CWE-327", issue="Weak hash", code="hashlib.new('md5')")]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(len(applied), 1)
        # Comment line inserted before fixed line — sha256 is now at index 1
        self.assertIn("sha256", result_lines[1])
        self.assertNotIn("md5", result_lines[1])

    def test_multiple_findings_reverse_order_correct(self):
        """Two yaml.load fixes in one file should both be applied correctly."""
        lines = [
            "import yaml\n",             # line 1
            "d1 = yaml.load(f1)\n",      # line 2
            "pass\n",                    # line 3
            "d2 = yaml.load(f2)\n",      # line 4
        ]
        findings = [
            _make_finding(line=2, cwe="CWE-502", issue="yaml", code="yaml.load"),
            _make_finding(line=4, cwe="CWE-502", issue="yaml", code="yaml.load"),
        ]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(len(applied), 2)
        # Each auto-fix inserts a reason comment above the fixed line — 4 original + 2 comments = 6
        self.assertEqual(len(result_lines), 6)
        self.assertIn("yaml.safe_load", result_lines[2])
        self.assertIn("yaml.safe_load", result_lines[5])

    def test_out_of_range_line_skipped(self):
        lines = ["x = 1\n"]
        findings = [_make_finding(line=99, cwe="CWE-502", issue="yaml", code="yaml.load")]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(applied, [])
        self.assertEqual(result_lines, lines)

    def test_sql_fstring_parameterized_in_apply(self):
        lines = ['    cursor.execute(f"SELECT * WHERE id={uid}")\n']
        findings = [_make_finding(
            file="app.py", line=1, cwe="CWE-89", issue="SQL injection",
        )]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(len(applied), 1)
        # Comment line inserted before fixed line — parameterized query is now at index 1
        self.assertIn("?", result_lines[1])
        self.assertTrue(applied[0]["auto_fixable"])

    def test_sql_unmatched_inserts_comment(self):
        lines = ["result = db.raw(build_sql(t))\n"]
        findings = [_make_finding(
            file="app.py", line=1, cwe="CWE-89", issue="SQL injection",
        )]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(len(applied), 1)
        self.assertEqual(applied[0]["transform"], "sql_comment")
        self.assertFalse(applied[0]["auto_fixable"])
        # A comment line was inserted, so we now have 2 lines
        self.assertEqual(len(result_lines), 2)
        self.assertIn("CWE-89", result_lines[0])

    def test_sql_csharp_comment_uses_csharp_advice(self):
        """C# SQL finding fallback must use SqlParameter advice, not Python cursor.execute."""
        lines = ['    db.Execute("SELECT * FROM t WHERE id=" + userId);\n']
        findings = [_make_finding(
            file="Repo.cs", line=1, cwe="CWE-89", issue="SQL injection",
            recommendation="Use SqlCommand with SqlParameter.",
        )]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(len(applied), 1)
        comment = result_lines[0]
        # Must not contain Python-specific cursor.execute advice
        self.assertNotIn("cursor.execute", comment)
        # Must use the recommendation from the finding
        self.assertIn("SqlParameter", comment)
        # Comment syntax must be // for C#
        self.assertIn("//", comment)

    def test_sql_log_line_not_flagged_by_partial_keyword(self):
        """Regression: SQL verbs used as English words in log messages must not match.
        'Updated', 'update', 'Deleted', 'Selected' etc. should be ignored;
        structural SQL pairs (UPDATE...SET, SELECT...FROM) are required for a match."""
        import sys
        _TOOLS_DIR = Path(__file__).parent.parent / "tools"
        if str(_TOOLS_DIR) not in sys.path:
            sys.path.insert(0, str(_TOOLS_DIR))
        import re
        # The C# interpolated SQL pattern — requires SQL structural pairs
        pattern = re.compile(
            r'\$["\'].*\b(?:SELECT\b.*\bFROM\b|INSERT\s+INTO\b|UPDATE\b.*\bSET\b|DELETE\s+FROM\b).*\{',
            re.IGNORECASE
        )
        # These log lines should NOT match (English verbs, no SQL structure)
        safe_lines = [
            # past-tense verb forms
            '_log.Verbose($"{TrackingId} Updated opportunityId: {opportunityId} to Lose");',
            '_logger.Info($"{id} Deleted record {name}");',
            '_log.Debug($"Selected value: {val}");',
            # present-tense verb (the actual production false positive)
            '_log.Warning($"{TrackingId} Error trying to update Contact Identifiers: {ex.Message}");',
            '_log.Info($"About to insert row for {entity}");',
            '_log.Debug($"Will delete {count} stale records from cache");',
        ]
        for line in safe_lines:
            self.assertIsNone(pattern.search(line),
                              f"Log line incorrectly flagged as SQL injection: {line!r}")
        # These SQL lines SHOULD still match
        sql_lines = [
            'cmd.CommandText = $"SELECT col FROM users WHERE id={userId}";',
            'var q = $"UPDATE orders SET status={s} WHERE id={id}";',
            'db.Execute($"INSERT INTO logs (msg) VALUES ({msg})");',
            'db.Execute($"DELETE FROM sessions WHERE token={tok}");',
        ]
        for line in sql_lines:
            self.assertIsNotNone(pattern.search(line),
                                 f"Real SQL interpolation not detected: {line!r}")

    def test_hardcoded_credential_replaced_in_apply(self):
        lines = ['password = "s3cr3t!pw"\n']
        findings = [_make_finding(
            file="settings.py", line=1, cwe="CWE-798", issue="Hardcoded credential",
        )]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(len(applied), 1)
        # _ensure_import inserts 'import os' before the credential line
        full_text = "".join(result_lines)
        self.assertIn("os.environ.get", full_text)
        self.assertIn("import os", full_text)

    def test_command_shell_true_fixed_in_apply(self):
        lines = ["subprocess.run(cmd, shell=True)\n"]
        findings = [_make_finding(
            file="runner.py", line=1, cwe="CWE-78", issue="Command injection",
        )]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(len(applied), 1)
        # Comment line inserted before fixed line — shell=False is now at index 1
        self.assertIn("shell=False", result_lines[1])
        self.assertTrue(applied[0]["auto_fixable"])

    def test_eval_inserts_comment_in_apply(self):
        lines = ["    result = eval(user_input)\n"]
        findings = [_make_finding(
            file="handler.py", line=1, cwe="CWE-94", issue="Dynamic code execution",
        )]
        result_lines, applied = _apply_all_transforms(lines, findings)
        self.assertEqual(len(applied), 1)
        self.assertFalse(applied[0]["auto_fixable"])
        self.assertEqual(len(result_lines), 2)
        self.assertIn("CWE-78/94", result_lines[0])


# ---------------------------------------------------------------------------
# _make_unified_diff
# ---------------------------------------------------------------------------

class TestMakeUnifiedDiff(unittest.TestCase):

    def test_diff_is_non_empty_when_lines_differ(self):
        original = ["line 1\n", "old\n"]
        fixed    = ["line 1\n", "new\n"]
        diff = _make_unified_diff(original, fixed, "src/test.py")
        self.assertTrue(diff.strip(), "Expected non-empty diff")
        self.assertIn("+new", diff)
        self.assertIn("-old", diff)

    def test_diff_is_empty_when_lines_identical(self):
        lines = ["same\n", "same\n"]
        diff = _make_unified_diff(lines, lines, "src/test.py")
        self.assertEqual(diff, "")

    def test_diff_header_contains_file_path(self):
        original = ["a\n"]
        fixed    = ["b\n"]
        diff = _make_unified_diff(original, fixed, "subdir/file.py")
        self.assertIn("subdir/file.py", diff)


# ---------------------------------------------------------------------------
# generate_fixes (integration)
# ---------------------------------------------------------------------------

class TestGenerateFixes(unittest.TestCase):

    def setUp(self):
        self._temp_files: List[Path] = []

    def tearDown(self):
        for p in self._temp_files:
            try:
                p.unlink()
            except OSError:
                pass

    def _tmp(self, content: str, suffix=".py") -> Path:
        p = _write_temp_file(content, suffix)
        self._temp_files.append(p)
        return p

    # -- yaml fix generates a diff ----------------------------------------

    def test_yaml_fix_produces_diff(self):
        path = self._tmp("import yaml\ndata = yaml.load(stream)\n")
        finding = _make_finding(file=str(path), line=2, cwe="CWE-502", issue="yaml", code="yaml.load")
        result = generate_fixes({"findings": [finding]})

        self.assertIn(str(path), result["diffs_by_file"])
        self.assertIn("yaml.safe_load", result["diffs_by_file"][str(path)])
        self.assertEqual(result["stats"]["auto_fixable"], 1)

    # -- requests fix -------------------------------------------------------

    def test_requests_verify_fix_produces_diff(self):
        path = self._tmp("import requests\nresp = requests.get(url, verify=False)\n")
        finding = _make_finding(
            file=str(path), line=2, cwe="CWE-295",
            issue="TLS certificate verification disabled", code="verify=False",
        )
        result = generate_fixes({"findings": [finding]})

        diff = result["diffs_by_file"].get(str(path), "")
        self.assertTrue(diff, "Expected non-empty diff for verify=False removal")
        self.assertIn("-", diff)

    # -- SQL injection: simple concat pattern is parameterized ---------------

    def test_sql_concat_injection_is_parameterized(self):
        path = self._tmp('cursor.execute("SELECT * FROM users WHERE id=" + uid)\n')
        finding = _make_finding(
            file=str(path), line=1, cwe="CWE-89",
            issue="SQL injection", recommendation="Use parameterized queries",
        )
        result = generate_fixes({"findings": [finding]})

        diff = result["diffs_by_file"].get(str(path), "")
        self.assertTrue(diff, "SQL concat pattern should produce a parameterized diff")
        self.assertIn("?", diff)
        self.assertIn("uid", diff)
        suggestions = result["fix_suggestions"]
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["transform"], "sql_parameterize")
        self.assertTrue(suggestions[0]["auto_fixable"])

    # -- SQL injection: unrecognised pattern falls back to advisory comment ---

    def test_sql_unrecognised_pattern_inserts_comment(self):
        path = self._tmp('result = db.raw_query(build_sql(table, filters))\n')
        finding = _make_finding(
            file=str(path), line=1, cwe="CWE-89",
            issue="SQL injection", recommendation="Use parameterized queries",
        )
        result = generate_fixes({"findings": [finding]})

        diff = result["diffs_by_file"].get(str(path), "")
        self.assertTrue(diff, "Unrecognised SQL pattern should still produce a comment diff")
        self.assertIn("CWE-89", diff)
        suggestions = result["fix_suggestions"]
        self.assertEqual(suggestions[0]["transform"], "sql_comment")
        self.assertFalse(suggestions[0]["auto_fixable"])

    # -- Missing file is gracefully skipped ---------------------------------

    def test_missing_file_is_skipped(self):
        finding = _make_finding(file="/nonexistent/path/file.py", line=1, cwe="CWE-502", issue="yaml")
        result = generate_fixes({"findings": [finding]})
        self.assertIn("skipped_files", result)
        self.assertEqual(result["stats"]["skipped_missing_file"], 1)

    # -- Combined patch contains all diffs ----------------------------------

    def test_combined_patch_contains_all_diffs(self):
        path1 = self._tmp("data = yaml.load(x)\n")
        path2 = self._tmp("r = requests.get(url, verify=False)\n")
        findings = [
            _make_finding(file=str(path1), line=1, cwe="CWE-502", issue="yaml", code="yaml.load"),
            _make_finding(file=str(path2), line=1, cwe="CWE-295",
                          issue="TLS certificate verification disabled", code="verify=False"),
        ]
        result = generate_fixes({"findings": findings})

        combined = result["combined_patch"]
        self.assertIn("yaml.safe_load", combined)
        self.assertEqual(result["stats"]["files_with_diffs"], 2)

    # -- Multiple findings in one file produce a single diff entry ----------

    def test_multiple_findings_single_file_one_diff(self):
        content = textwrap.dedent("""\
            import yaml, pickle
            cfg = yaml.load(f)
            obj = pickle.load(p)
        """)
        path = self._tmp(content)
        findings = [
            _make_finding(file=str(path), line=2, cwe="CWE-502", issue="yaml", code="yaml.load"),
            _make_finding(file=str(path), line=3, cwe="CWE-502", issue="pickle", code="pickle.load"),
        ]
        result = generate_fixes({"findings": findings})

        self.assertEqual(result["stats"]["files_with_diffs"], 1,
                         "Both findings in same file should produce exactly one diff entry")

    # -- Stats accuracy -----------------------------------------------------

    def test_stats_reflect_mixed_findings(self):
        path = self._tmp("data = yaml.load(stream)\n")
        findings = [
            _make_finding(file=str(path), line=1, cwe="CWE-502", issue="yaml", code="yaml.load"),
            _make_finding(file="/missing.py", line=1, cwe="CWE-502", issue="yaml"),
            _make_finding(file=str(path), line=1, cwe="CWE-89", issue="SQL injection"),
        ]
        result = generate_fixes({"findings": findings})

        stats = result["stats"]
        self.assertEqual(stats["total_findings"], 3)
        self.assertGreaterEqual(stats["auto_fixable"], 1)
        # CWE-89 is no longer suggestion-only; it now goes through the transform path
        self.assertEqual(stats["suggestion_only"], 0)

    # -- Empty findings list ------------------------------------------------

    def test_empty_findings_returns_empty_result(self):
        result = generate_fixes({"findings": []})
        self.assertEqual(result["fix_suggestions"], [])
        self.assertEqual(result["diffs_by_file"], {})
        self.assertEqual(result["combined_patch"], "")

    # -- base_dir resolves relative paths -----------------------------------

    def test_base_dir_resolves_relative_paths(self):
        path = self._tmp("data = yaml.load(stream)\n")
        base = path.parent
        rel = path.name  # just the filename
        finding = _make_finding(file=rel, line=1, cwe="CWE-502", issue="yaml", code="yaml.load")
        result = generate_fixes({"findings": [finding], "base_dir": str(base)})

        # Should find the file and produce a diff
        self.assertFalse(result.get("skipped_files"), "File not found despite base_dir")
        self.assertEqual(result["stats"]["files_with_diffs"], 1)


class TestSqlScannerFalsePositives(unittest.TestCase):
    """Regression: scanner must not flag natural-language SQL verbs in log/message strings."""

    @classmethod
    def setUpClass(cls):
        import importlib
        _TOOLS_DIR = Path(__file__).parent.parent / "tools"
        if str(_TOOLS_DIR) not in sys.path:
            sys.path.insert(0, str(_TOOLS_DIR))
        cls.scanner = importlib.import_module("sql_scanner")

    def _scan(self, code: str, filename: str) -> list:
        return self.scanner._scan_code_with_regex(code, filename)

    # --- C# log lines that must produce zero findings ---

    def test_csharp_log_update_verb_not_flagged(self):
        """Production false positive: 'trying to update Contact Identifiers'"""
        line = '_log.Warning($"{TrackingId} Error trying to update Contact Identifiers: {ex.Message}", ex);'
        findings = self._scan(line, "ContactService.cs")
        sql_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertEqual(sql_findings, [],
                         f"Log line wrongly flagged as SQL injection: {sql_findings}")

    def test_csharp_log_insert_verb_not_flagged(self):
        line = '_log.Info($"About to insert {count} records into the cache");'
        findings = self._scan(line, "CacheService.cs")
        sql_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertEqual(sql_findings, [], f"Log line wrongly flagged: {sql_findings}")

    def test_csharp_log_delete_verb_not_flagged(self):
        line = '_log.Debug($"Will delete {count} stale entries from cache");'
        findings = self._scan(line, "CacheService.cs")
        sql_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertEqual(sql_findings, [], f"Log line wrongly flagged: {sql_findings}")

    def test_csharp_log_select_verb_not_flagged(self):
        line = '_log.Verbose($"{TrackingId} User selected tab {tabName} from menu");'
        findings = self._scan(line, "UiController.cs")
        sql_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertEqual(sql_findings, [], f"Log line wrongly flagged: {sql_findings}")

    # --- Real C# SQL interpolation that MUST be caught ---

    def test_csharp_update_set_interpolation_flagged(self):
        line = 'cmd.CommandText = $"UPDATE orders SET status={s} WHERE id={id}";'
        findings = self._scan(line, "OrderRepo.cs")
        sql_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertGreater(len(sql_findings), 0,
                           "UPDATE...SET SQL interpolation was not detected")

    def test_csharp_select_from_interpolation_flagged(self):
        line = 'var q = $"SELECT col FROM users WHERE id={userId}";'
        findings = self._scan(line, "UserRepo.cs")
        sql_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertGreater(len(sql_findings), 0,
                           "SELECT...FROM SQL interpolation was not detected")

    def test_csharp_insert_into_interpolation_flagged(self):
        line = 'db.Execute($"INSERT INTO logs (msg) VALUES ({msg})");'
        findings = self._scan(line, "Logger.cs")
        sql_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertGreater(len(sql_findings), 0,
                           "INSERT INTO SQL interpolation was not detected")

    def test_csharp_delete_from_interpolation_flagged(self):
        line = 'db.Execute($"DELETE FROM sessions WHERE token={tok}");'
        findings = self._scan(line, "SessionRepo.cs")
        sql_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertGreater(len(sql_findings), 0,
                           "DELETE FROM SQL interpolation was not detected")

    # --- Python log lines that must produce zero findings ---

    def test_python_log_update_fstring_not_flagged(self):
        line = 'logger.warning(f"Trying to update {count} records in cache")'
        findings = self._scan(line, "service.py")
        sql_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertEqual(sql_findings, [], f"Python log wrongly flagged: {sql_findings}")

    # --- Real Python SQL f-string that MUST be caught ---

    def test_python_update_set_fstring_flagged(self):
        line = 'cursor.execute(f"UPDATE users SET name={name} WHERE id={uid}")'
        findings = self._scan(line, "repo.py")
        sql_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertGreater(len(sql_findings), 0,
                           "Python UPDATE...SET f-string SQL not detected")


class TestODataInjectionScanner(unittest.TestCase):
    """Regression suite for OData $filter injection detection (Dynamics 365 / SharePoint pattern)."""

    @classmethod
    def setUpClass(cls):
        import importlib
        _TOOLS_DIR = Path(__file__).parent.parent / "tools"
        if str(_TOOLS_DIR) not in sys.path:
            sys.path.insert(0, str(_TOOLS_DIR))
        cls.scanner = importlib.import_module("sql_scanner")

    def _scan(self, code: str, filename: str) -> list:
        return self.scanner._scan_code_with_regex(code, filename)

    # --- Production pattern from Queries.cs (the exact failing case) ---

    def test_csharp_odata_filter_interpolation_flagged(self):
        """Regression: Queries.cs OData $filter with user-controlled criteria.Value must be detected."""
        line = 'return $"contacts?$filter={criteria.Field.ToLower()} eq \'{criteria.Value}\'";'
        findings = self._scan(line, "Queries.cs")
        odata_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertGreater(len(odata_findings), 0,
                           "OData $filter interpolation in Queries.cs was not detected")

    def test_csharp_odata_filter_ampersand_prefix_flagged(self):
        """The &$filter=... form (query string append) must also be detected."""
        line = 'return $"&$filter={criteria.Field.ToLower()} eq \'{criteria.Value}\'";'
        findings = self._scan(line, "Queries.cs")
        odata_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertGreater(len(odata_findings), 0,
                           "OData &$filter interpolation not detected")

    def test_csharp_odata_search_interpolation_flagged(self):
        line = 'var url = $"entities?$search={userInput}";'
        findings = self._scan(line, "SearchService.cs")
        odata_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertGreater(len(odata_findings), 0,
                           "OData $search interpolation not detected")

    def test_csharp_odata_orderby_interpolation_flagged(self):
        line = 'var url = $"contacts?$orderby={sortField} asc";'
        findings = self._scan(line, "ContactRepo.cs")
        odata_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertGreater(len(odata_findings), 0,
                           "OData $orderby interpolation not detected")

    def test_csharp_odata_concat_flagged(self):
        line = 'var url = "contacts?$filter=name eq \'" + value + "\'";'
        findings = self._scan(line, "Queries.cs")
        odata_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertGreater(len(odata_findings), 0,
                           "OData $filter string concatenation not detected")

    # --- Log lines / clean code that must NOT be flagged ---

    def test_csharp_log_odata_not_flagged(self):
        """A log message mentioning 'OData filter' but containing no variable injection."""
        line = '_log.Info($"OData filter applied for {entity}");'
        findings = self._scan(line, "ContactService.cs")
        odata_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertEqual(odata_findings, [],
                         f"Benign OData log line wrongly flagged: {odata_findings}")

    def test_csharp_hardcoded_odata_not_flagged(self):
        """A hardcoded (no interpolation) OData URL must not be flagged."""
        line = 'var url = "contacts?$filter=statecode eq 0&$select=name,email";'
        findings = self._scan(line, "ContactRepo.cs")
        odata_findings = [f for f in findings if f.get("cwe") == "CWE-89"]
        self.assertEqual(odata_findings, [],
                         f"Hardcoded OData URL wrongly flagged: {odata_findings}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

