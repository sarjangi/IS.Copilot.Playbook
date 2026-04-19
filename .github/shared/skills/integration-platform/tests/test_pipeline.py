"""
Tests for pipeline.py

All network, git, and sub-tool calls are mocked.
Tests cover: dry_run, run, error paths, HTML report, PR body builder.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

_TOOLS_DIR = Path(__file__).parent.parent / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from pipeline import (
    _build_clone_url,
    _build_pr_body,
    _esc,
    _rel_path,
    run_pipeline,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_finding(
    severity="HIGH",
    cwe="CWE-502",
    issue="Unsafe deserialization",
    file="/tmp/repo/app.py",
    line=10,
    source="security",
):
    return {
        "severity": severity,
        "cwe": cwe,
        "issue": issue,
        "file": file,
        "line": line,
        "code": "pickle.loads(data)",
        "source": source,
    }


def _make_sql_finding(file="/tmp/repo/db.py", line=20):
    return {
        "severity": "HIGH",
        "cwe": "CWE-89",
        "issue": "SQL injection",
        "file": file,
        "line": line,
        "code": "cursor.execute(f\"SELECT * FROM users WHERE id={uid}\")",
        "source": "sql",
    }


def _fix_result(findings):
    return {
        "fix_suggestions": [
            {
                "severity": f["severity"],
                "file": f["file"],
                "line": f["line"],
                "auto_fixable": False,
                "explanation": f["issue"],
                "original_code": f["code"],
                "fixed_code": "# SECURITY: review",
            }
            for f in findings
        ],
        "diffs_by_file": {},
        "combined_patch": "--- a/app.py\n+++ b/app.py\n@@ -10,1 +10,1 @@\n-pickle.loads\n+# SECURITY",
        "stats": {"auto_fixable": 0, "suggestion_only": len(findings)},
    }


# ---------------------------------------------------------------------------
# _build_clone_url
# ---------------------------------------------------------------------------

class TestBuildCloneUrl(unittest.TestCase):

    def test_no_token_returns_original(self):
        url = "https://github.com/org/repo.git"
        self.assertEqual(_build_clone_url(url, ""), url)

    def test_ssh_url_skipped(self):
        url = "git@github.com:org/repo.git"
        self.assertEqual(_build_clone_url(url, "TOKEN"), url)

    def test_github_embeds_token(self):
        url = "https://github.com/org/repo.git"
        result = _build_clone_url(url, "mytoken")
        self.assertIn("mytoken", result)
        self.assertNotIn("mytoken", url)

    def test_azdo_embeds_token(self):
        url = "https://dev.azure.com/myorg/myproj/_git/myrepo"
        result = _build_clone_url(url, "mytoken")
        # Azure DevOps clone URL must include org:token@ (non-empty username required)
        self.assertIn("myorg:mytoken@", result)

    def test_unknown_platform_returns_original(self):
        # Unsupported host — detect_platform raises ValueError
        url = "https://gitlab.com/org/repo.git"
        result = _build_clone_url(url, "token")
        self.assertEqual(result, url)


# ---------------------------------------------------------------------------
# _rel_path
# ---------------------------------------------------------------------------

class TestRelPath(unittest.TestCase):

    def test_relative_path(self):
        base = "/tmp/ip_pipeline_abc"
        abs_path = base + "/src/app.py"
        result = _rel_path(abs_path, base)
        self.assertEqual(result, "src/app.py")

    def test_unrelated_path_returned_as_is(self):
        result = _rel_path("/other/path/file.py", "/some/base")
        self.assertEqual(result, "/other/path/file.py")


# ---------------------------------------------------------------------------
# _esc
# ---------------------------------------------------------------------------

class TestEsc(unittest.TestCase):

    def test_ampersand(self):
        self.assertIn("&amp;", _esc("a & b"))

    def test_lt_gt(self):
        self.assertIn("&lt;", _esc("<tag>"))
        self.assertIn("&gt;", _esc("<tag>"))

    def test_quote(self):
        self.assertIn("&quot;", _esc('"quoted"'))

    def test_no_special_chars(self):
        self.assertEqual(_esc("hello"), "hello")


# ---------------------------------------------------------------------------
# _build_pr_body
# ---------------------------------------------------------------------------

class TestBuildPrBody(unittest.TestCase):

    def test_contains_total_findings(self):
        body = _build_pr_body("https://github.com/org/repo", 5, _fix_result([]), "")
        self.assertIn("5", body)

    def test_contains_extra_context(self):
        body = _build_pr_body("https://github.com/org/repo", 0, _fix_result([]), "My context")
        self.assertIn("My context", body)

    def test_no_extra_context_omits_section(self):
        body = _build_pr_body("https://github.com/org/repo", 0, _fix_result([]), "")
        self.assertNotIn("Additional context", body)

    def test_auto_fixable_count(self):
        stats = {"auto_fixable": 3, "suggestion_only": 2}
        body = _build_pr_body(
            "https://github.com/org/repo", 5, {"stats": stats}, ""
        )
        self.assertIn("3", body)
        self.assertIn("2", body)


# ---------------------------------------------------------------------------
# run_pipeline — input validation
# ---------------------------------------------------------------------------

class TestRunPipelineValidation(unittest.TestCase):

    @patch("pipeline._GIT_AVAILABLE", True)
    def test_missing_repo_url(self):
        result = run_pipeline({"action": "dry_run"})
        self.assertIn("error", result)
        self.assertIn("repo_url", result["error"])

    @patch("pipeline._GIT_AVAILABLE", True)
    def test_invalid_action(self):
        result = run_pipeline({"action": "explode", "repo_url": "https://github.com/a/b"})
        self.assertIn("error", result)
        self.assertIn("action", result["error"])

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline._resolve_ado_token", return_value="")   # prevent git credential fill blocking
    def test_run_without_auth_token_ado(self, _mock_ado):
        """ADO repos with no cached credentials should return a clear error."""
        result = run_pipeline({"action": "run", "repo_url": "https://dev.azure.com/org/proj/_git/repo", "branch": "main"})
        self.assertIn("error", result)
        # Error must guide the user — not expose internal implementation details
        self.assertTrue(
            "auth_token" in result["error"] or "ADO" in result["error"] or "credential" in result["error"],
            f"Unexpected error message: {result['error']}"
        )

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline._resolve_ado_token", return_value="fake_gcm_token")  # prevent git credential fill blocking
    def test_run_ado_gcm_token_resolves_silently(self, _mock_ado):
        """ADO repos should use GCM-cached credentials without a PAT being passed in."""
        import pipeline as _pipeline
        fake_git_error = _pipeline.GitCommandError("git clone", 128, "Repository not found")
        with patch("pipeline._clone_repo", side_effect=fake_git_error):
            result = run_pipeline({"action": "run", "repo_url": "https://dev.azure.com/org/proj/_git/repo"})
        self.assertIn("error", result)
        # Should be a clone error, not a credential error
        self.assertNotIn("auth_token is required", result.get("error", ""))

    @patch("pipeline._GIT_AVAILABLE", True)
    def test_run_github_no_token_resolves_silently(self):
        """GitHub repos should NOT hard-error on missing token — pipeline tries gh auth token.
        If gh auth returns a token but clone fails (non-existent repo), that is a clone error,
        not an auth_token error."""
        from unittest.mock import patch as _patch
        import pipeline as _pipeline
        fake_git_error = _pipeline.GitCommandError("git clone", 128, "Repository not found")
        with _patch("pipeline._resolve_github_token", return_value="ghp_fake"):
            with _patch("pipeline._clone_repo", side_effect=fake_git_error):
                result = run_pipeline({"action": "run", "repo_url": "https://github.com/a/b"})
        self.assertIn("error", result)
        # Should be a clone error, not a 'no auth_token' error
        self.assertNotIn("auth_token is required", result.get("error", ""))

    def test_no_git_available(self):
        with patch("pipeline._GIT_AVAILABLE", False):
            result = run_pipeline({"action": "dry_run", "repo_url": "https://github.com/a/b"})
        self.assertIn("error", result)
        self.assertIn("GitPython", result["error"])


# ---------------------------------------------------------------------------
# run_pipeline — dry_run success
# ---------------------------------------------------------------------------

class TestRunPipelineDryRun(unittest.TestCase):

    def _make_mock_repo(self):
        mock_repo = MagicMock()
        return mock_repo

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline.shutil.rmtree")
    @patch("pipeline.create_pr")
    @patch("pipeline.generate_fixes")
    @patch("pipeline.scan_security_vulnerabilities")
    @patch("pipeline.scan_sql_injection_directory")
    @patch("pipeline.Repo")
    def test_dry_run_returns_expected_keys(
        self,
        mock_repo_cls,
        mock_sql,
        mock_sec,
        mock_fixes,
        mock_create_pr,
        mock_rmtree,
    ):
        findings = [_make_finding()]
        mock_sql.return_value = {"findings": findings, "success": True}
        mock_sec.return_value = {"findings": [], "success": True}
        mock_fixes.return_value = _fix_result(findings)

        result = run_pipeline(
            {
                "action": "dry_run",
                "branch": "main",
                "repo_url": "https://github.com/org/repo.git",
            }
        )

        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "dry_run")
        self.assertEqual(result["total_findings"], 1)
        self.assertEqual(result["sql_findings_count"], 1)
        self.assertEqual(result["security_findings_count"], 0)
        self.assertIn("html_report", result)
        self.assertIn("fix_suggestions", result)
        self.assertIn("combined_patch", result)
        self.assertIn("stats", result)
        # PR fields empty on dry_run
        self.assertEqual(result["pr_url"], "")
        self.assertEqual(result["branch_name"], "")
        # create_pr must NOT be called in dry_run
        mock_create_pr.assert_not_called()

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline.shutil.rmtree")
    @patch("pipeline.generate_fixes")
    @patch("pipeline.scan_security_vulnerabilities")
    @patch("pipeline.scan_sql_injection_directory")
    @patch("pipeline.Repo")
    def test_dry_run_html_report_contains_findings(
        self,
        mock_repo_cls,
        mock_sql,
        mock_sec,
        mock_fixes,
        mock_rmtree,
    ):
        findings = [_make_finding(severity="CRITICAL", cwe="CWE-502")]
        mock_sql.return_value = {"findings": findings, "success": True}
        mock_sec.return_value = {"findings": [], "success": True}
        mock_fixes.return_value = _fix_result(findings)

        result = run_pipeline(
            {"action": "dry_run", "branch": "main", "repo_url": "https://github.com/org/repo.git"}
        )

        self.assertIn("CRITICAL", result["html_report"])
        self.assertIn("CWE-502", result["html_report"])

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline.shutil.rmtree")
    @patch("pipeline.generate_fixes")
    @patch("pipeline.scan_security_vulnerabilities")
    @patch("pipeline.scan_sql_injection_directory")
    @patch("pipeline.Repo")
    def test_tempdir_always_cleaned_up(
        self,
        mock_repo_cls,
        mock_sql,
        mock_sec,
        mock_fixes,
        mock_rmtree,
    ):
        mock_sql.return_value = {"findings": [], "success": True}
        mock_sec.return_value = {"findings": [], "success": True}
        mock_fixes.return_value = _fix_result([])

        run_pipeline(
            {"action": "dry_run", "branch": "main", "repo_url": "https://github.com/org/repo.git"}
        )

        mock_rmtree.assert_called()
        call_args = mock_rmtree.call_args_list[-1]
        self.assertTrue(call_args[1].get("ignore_errors") or call_args[0][1] is True
                        or call_args.kwargs.get("ignore_errors"))

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline.shutil.rmtree")
    @patch("pipeline.generate_fixes")
    @patch("pipeline.scan_security_vulnerabilities")
    @patch("pipeline.scan_sql_injection_directory")
    @patch("pipeline.Repo")
    def test_tempdir_cleaned_up_on_clone_failure(
        self,
        mock_repo_cls,
        mock_sql,
        mock_sec,
        mock_fixes,
        mock_rmtree,
    ):
        import pipeline as _pipeline_mod
        mock_repo_cls.clone_from.side_effect = _pipeline_mod.GitCommandError("clone failed", "")

        result = run_pipeline(
            {"action": "dry_run", "branch": "main", "repo_url": "https://github.com/org/repo.git"}
        )
        self.assertIn("error", result)
        self.assertGreaterEqual(mock_rmtree.call_count, 1)

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline.shutil.rmtree")
    @patch("pipeline.generate_fixes")
    @patch("pipeline.scan_security_vulnerabilities")
    @patch("pipeline.scan_sql_injection_directory")
    @patch("pipeline.Repo")
    def test_both_scanner_findings_merged(
        self,
        mock_repo_cls,
        mock_sql,
        mock_sec,
        mock_fixes,
        mock_rmtree,
    ):
        sql_finding = _make_sql_finding()
        sec_finding = _make_finding()
        mock_sql.return_value = {"findings": [sql_finding], "success": True}
        mock_sec.return_value = {"findings": [sec_finding], "success": True}
        mock_fixes.return_value = _fix_result([sql_finding, sec_finding])

        result = run_pipeline(
            {"action": "dry_run", "branch": "main", "repo_url": "https://github.com/org/repo.git"}
        )

        self.assertEqual(result["total_findings"], 2)
        self.assertEqual(result["sql_findings_count"], 1)
        self.assertEqual(result["security_findings_count"], 1)
        # Verify generate_fixes received BOTH findings
        call_args = mock_fixes.call_args[0][0]
        self.assertEqual(len(call_args["findings"]), 2)

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline.shutil.rmtree")
    @patch("pipeline.generate_fixes")
    @patch("pipeline.scan_security_vulnerabilities")
    @patch("pipeline.scan_sql_injection_directory")
    @patch("pipeline.Repo")
    def test_scan_profile_passed_to_security_scanner(
        self,
        mock_repo_cls,
        mock_sql,
        mock_sec,
        mock_fixes,
        mock_rmtree,
    ):
        mock_sql.return_value = {"findings": [], "success": True}
        mock_sec.return_value = {"findings": [], "success": True}
        mock_fixes.return_value = _fix_result([])

        run_pipeline(
            {
                "action": "dry_run",
                "branch": "main",
                "repo_url": "https://github.com/org/repo.git",
                "scan_profile": "secrets",
            }
        )

        call_args = mock_sec.call_args[0][0]
        self.assertEqual(call_args["profile"], "secrets")


# ---------------------------------------------------------------------------
# run_pipeline — run mode
# ---------------------------------------------------------------------------

class TestRunPipelineRunMode(unittest.TestCase):

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline.shutil.rmtree")
    @patch("pipeline.create_pr")
    @patch("pipeline.generate_fixes")
    @patch("pipeline.scan_security_vulnerabilities")
    @patch("pipeline.scan_sql_injection_directory")
    @patch("pipeline.Repo")
    def test_run_mode_calls_create_pr(
        self,
        mock_repo_cls,
        mock_sql,
        mock_sec,
        mock_fixes,
        mock_create_pr,
        mock_rmtree,
    ):
        findings = [_make_finding()]
        mock_sql.return_value = {"findings": findings, "success": True}
        mock_sec.return_value = {"findings": [], "success": True}
        mock_fixes.return_value = _fix_result(findings)
        mock_create_pr.return_value = {
            "pr_url": "https://github.com/org/repo/pull/42",
            "branch_name": "security-fixes-abc123",
            "files_changed": 1,
            "platform": "github",
        }

        result = run_pipeline(
            {
                "action": "run",
                "branch": "main",
                "repo_url": "https://github.com/org/repo.git",
                "auth_token": "ghp_secrettoken",
            }
        )

        mock_create_pr.assert_called_once()
        self.assertEqual(result["pr_url"], "https://github.com/org/repo/pull/42")
        self.assertEqual(result["branch_name"], "security-fixes-abc123")

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline.shutil.rmtree")
    @patch("pipeline.create_pr")
    @patch("pipeline.generate_fixes")
    @patch("pipeline.scan_security_vulnerabilities")
    @patch("pipeline.scan_sql_injection_directory")
    @patch("pipeline.Repo")
    def test_run_mode_passes_auth_token_to_create_pr(
        self,
        mock_repo_cls,
        mock_sql,
        mock_sec,
        mock_fixes,
        mock_create_pr,
        mock_rmtree,
    ):
        findings = [_make_finding()]
        mock_sql.return_value = {"findings": findings, "success": True}
        mock_sec.return_value = {"findings": [], "success": True}
        mock_fixes.return_value = _fix_result(findings)
        mock_create_pr.return_value = {
            "pr_url": "https://github.com/org/repo/pull/1",
            "branch_name": "security-fixes-xyz",
            "files_changed": 0,
            "platform": "github",
        }

        run_pipeline(
            {
                "action": "run",
                "branch": "main",
                "repo_url": "https://github.com/org/repo.git",
                "auth_token": "tok_abc",
            }
        )

        create_pr_args = mock_create_pr.call_args[0][0]
        self.assertEqual(create_pr_args["auth_token"], "tok_abc")

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline.shutil.rmtree")
    @patch("pipeline.create_pr")
    @patch("pipeline.generate_fixes")
    @patch("pipeline.scan_security_vulnerabilities")
    @patch("pipeline.scan_sql_injection_directory")
    @patch("pipeline.Repo")
    def test_run_mode_pr_error_returns_error_with_report(
        self,
        mock_repo_cls,
        mock_sql,
        mock_sec,
        mock_fixes,
        mock_create_pr,
        mock_rmtree,
    ):
        findings = [_make_finding()]
        mock_sql.return_value = {"findings": findings, "success": True}
        mock_sec.return_value = {"findings": [], "success": True}
        mock_fixes.return_value = _fix_result(findings)
        mock_create_pr.return_value = {"error": "Push failed: remote rejected"}

        result = run_pipeline(
            {
                "action": "run",
                "branch": "main",
                "repo_url": "https://github.com/org/repo.git",
                "auth_token": "ghp_token",
            }
        )

        # Error reported but html_report still present
        self.assertIn("error", result)
        self.assertIn("html_report", result)
        self.assertEqual(result["action"], "run")

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline.shutil.rmtree")
    @patch("pipeline.create_pr")
    @patch("pipeline.generate_fixes")
    @patch("pipeline.scan_security_vulnerabilities")
    @patch("pipeline.scan_sql_injection_directory")
    @patch("pipeline.Repo")
    def test_auth_token_not_in_html_report(
        self,
        mock_repo_cls,
        mock_sql,
        mock_sec,
        mock_fixes,
        mock_create_pr,
        mock_rmtree,
    ):
        findings = [_make_finding()]
        mock_sql.return_value = {"findings": findings, "success": True}
        mock_sec.return_value = {"findings": [], "success": True}
        mock_fixes.return_value = _fix_result(findings)
        mock_create_pr.return_value = {
            "pr_url": "https://github.com/org/repo/pull/1",
            "branch_name": "sec-branch",
            "files_changed": 1,
            "platform": "github",
        }

        result = run_pipeline(
            {
                "action": "run",
                "branch": "main",
                "repo_url": "https://github.com/org/repo.git",
                "auth_token": "SUPERSECRETTOKEN",
            }
        )

        self.assertNotIn("SUPERSECRETTOKEN", result.get("html_report", ""))

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline.shutil.rmtree")
    @patch("pipeline.create_pr")
    @patch("pipeline.generate_fixes")
    @patch("pipeline.scan_security_vulnerabilities")
    @patch("pipeline.scan_sql_injection_directory")
    @patch("pipeline.Repo")
    def test_run_mode_html_report_shows_pr_url(
        self,
        mock_repo_cls,
        mock_sql,
        mock_sec,
        mock_fixes,
        mock_create_pr,
        mock_rmtree,
    ):
        mock_sql.return_value = {"findings": [], "success": True}
        mock_sec.return_value = {"findings": [], "success": True}
        mock_fixes.return_value = _fix_result([])
        mock_create_pr.return_value = {
            "pr_url": "https://github.com/org/repo/pull/99",
            "branch_name": "sec-99",
            "files_changed": 0,
            "platform": "github",
        }

        result = run_pipeline(
            {
                "action": "run",
                "branch": "main",
                "repo_url": "https://github.com/org/repo.git",
                "auth_token": "tok",
            }
        )

        self.assertIn("https://github.com/org/repo/pull/99", result["html_report"])

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline.shutil.rmtree")
    @patch("pipeline.create_pr")
    @patch("pipeline.generate_fixes")
    @patch("pipeline.scan_security_vulnerabilities")
    @patch("pipeline.scan_sql_injection_directory")
    @patch("pipeline.Repo")
    def test_custom_pr_title_passed_through(
        self,
        mock_repo_cls,
        mock_sql,
        mock_sec,
        mock_fixes,
        mock_create_pr,
        mock_rmtree,
    ):
        mock_sql.return_value = {"findings": [], "success": True}
        mock_sec.return_value = {"findings": [], "success": True}
        mock_fixes.return_value = _fix_result([])
        mock_create_pr.return_value = {
            "pr_url": "https://github.com/org/repo/pull/1",
            "branch_name": "sec-1",
            "files_changed": 0,
            "platform": "github",
        }

        run_pipeline(
            {
                "action": "run",
                "branch": "main",
                "repo_url": "https://github.com/org/repo.git",
                "auth_token": "tok",
                "pr_title": "My Custom Title",
            }
        )

        call_args = mock_create_pr.call_args[0][0]
        self.assertEqual(call_args["pr_title"], "My Custom Title")

    @patch("pipeline._GIT_AVAILABLE", True)
    @patch("pipeline.shutil.rmtree")
    @patch("pipeline.create_pr")
    @patch("pipeline.generate_fixes")
    @patch("pipeline.scan_security_vulnerabilities")
    @patch("pipeline.scan_sql_injection_directory")
    @patch("pipeline.Repo")
    def test_base_branch_passed_to_create_pr(
        self,
        mock_repo_cls,
        mock_sql,
        mock_sec,
        mock_fixes,
        mock_create_pr,
        mock_rmtree,
    ):
        mock_sql.return_value = {"findings": [], "success": True}
        mock_sec.return_value = {"findings": [], "success": True}
        mock_fixes.return_value = _fix_result([])
        mock_create_pr.return_value = {
            "pr_url": "https://github.com/org/repo/pull/1",
            "branch_name": "sec",
            "files_changed": 0,
            "platform": "github",
        }

        run_pipeline(
            {
                "action": "run",
                "branch": "main",
                "repo_url": "https://github.com/org/repo.git",
                "auth_token": "tok",
                "base_branch": "develop",
            }
        )

        call_args = mock_create_pr.call_args[0][0]
        self.assertEqual(call_args["base_branch"], "develop")


if __name__ == "__main__":
    unittest.main()
