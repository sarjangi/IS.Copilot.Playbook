"""
Tests for pr_creator.py

Tests URL parsing, platform detection, SSRF validation, and PR creation logic
using mocks for GitPython and urllib so no real network or git calls are made.
"""

import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

_TOOLS_DIR = Path(__file__).parent.parent / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from pr_creator import (
    create_pr,
    detect_platform,
    parse_repo_url,
    _build_auth_push_url,
    _redact_token_from_url,
    _validate_api_url,
    _apply_fixes_to_dir,
    _validate_build,
)


# ---------------------------------------------------------------------------
# detect_platform
# ---------------------------------------------------------------------------

class TestDetectPlatform(unittest.TestCase):

    def test_github_https(self):
        self.assertEqual(detect_platform("https://github.com/owner/repo.git"), "github")

    def test_github_ssh(self):
        self.assertEqual(detect_platform("git@github.com:owner/repo.git"), "github")

    def test_azdo_https(self):
        self.assertEqual(
            detect_platform("https://dev.azure.com/myorg/myproject/_git/myrepo"),
            "azuredevops",
        )

    def test_azdo_visualstudio_legacy(self):
        self.assertEqual(
            detect_platform("https://myorg.visualstudio.com/myproject/_git/repo"),
            "azuredevops",
        )

    def test_unknown_raises(self):
        with self.assertRaises(ValueError):
            detect_platform("https://gitlab.com/owner/repo.git")


# ---------------------------------------------------------------------------
# parse_repo_url
# ---------------------------------------------------------------------------

class TestParseRepoUrl(unittest.TestCase):

    def test_github_https_parsed(self):
        result = parse_repo_url("https://github.com/acme/my-repo.git")
        self.assertEqual(result["platform"], "github")
        self.assertEqual(result["owner"], "acme")
        self.assertEqual(result["repo"], "my-repo")

    def test_github_no_dotgit(self):
        result = parse_repo_url("https://github.com/acme/my-repo")
        self.assertEqual(result["repo"], "my-repo")

    def test_azdo_dev_azure_com(self):
        result = parse_repo_url(
            "https://dev.azure.com/myorg/myproject/_git/myrepo"
        )
        self.assertEqual(result["platform"], "azuredevops")
        self.assertEqual(result["org"], "myorg")
        self.assertEqual(result["project"], "myproject")
        self.assertEqual(result["repo"], "myrepo")

    def test_azdo_visualstudio_legacy(self):
        result = parse_repo_url(
            "https://myorg.visualstudio.com/myproject/_git/myrepo.git"
        )
        self.assertEqual(result["org"], "myorg")
        self.assertEqual(result["project"], "myproject")
        self.assertEqual(result["repo"], "myrepo")

    def test_invalid_github_raises(self):
        with self.assertRaises(ValueError):
            parse_repo_url("https://github.com/no-repo-segment")


# ---------------------------------------------------------------------------
# _build_auth_push_url
# ---------------------------------------------------------------------------

class TestBuildAuthPushUrl(unittest.TestCase):

    def test_github_embeds_token(self):
        url = _build_auth_push_url(
            "https://github.com/owner/repo.git", "mytoken", "github"
        )
        self.assertIn("x-access-token:mytoken@", url)
        self.assertIn("github.com", url)

    def test_azdo_embeds_token(self):
        url = _build_auth_push_url(
            "https://dev.azure.com/org/project/_git/repo", "mytoken", "azuredevops"
        )
        # Azure DevOps requires org:token@ format (non-empty username)
        self.assertIn("org:mytoken@", url)
        self.assertIn("dev.azure.com", url)

    def test_ssh_raises(self):
        with self.assertRaises(ValueError):
            _build_auth_push_url("git@github.com:owner/repo.git", "token", "github")


# ---------------------------------------------------------------------------
# _redact_token_from_url
# ---------------------------------------------------------------------------

class TestRedactToken(unittest.TestCase):

    def test_redacts_user_info(self):
        url = "https://x-access-token:sec123@github.com/owner/repo"
        result = _redact_token_from_url(url)
        self.assertNotIn("sec123", result)
        self.assertIn("github.com", result)

    def test_clean_url_unchanged(self):
        url = "https://github.com/owner/repo"
        self.assertEqual(_redact_token_from_url(url), url)


# ---------------------------------------------------------------------------
# _validate_api_url
# ---------------------------------------------------------------------------

class TestValidateApiUrl(unittest.TestCase):

    def test_github_api_allowed(self):
        _validate_api_url("https://api.github.com/repos/owner/repo/pulls")  # should not raise

    def test_azdo_api_allowed(self):
        _validate_api_url(
            "https://dev.azure.com/org/proj/_apis/git/repositories/repo/pullrequests"
        )  # should not raise

    def test_untrusted_host_raises(self):
        with self.assertRaises(ValueError):
            _validate_api_url("https://evil.example.com/steal")

    def test_internal_ip_raises(self):
        with self.assertRaises(ValueError):
            _validate_api_url("http://169.254.169.254/latest/meta-data")


# ---------------------------------------------------------------------------
# _apply_fixes_to_dir
# ---------------------------------------------------------------------------

class TestApplyFixesToDir(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._files: list = []

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _write(self, name: str, content: str) -> Path:
        p = Path(self._tmp_dir) / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_yaml_load_fixed_in_file(self):
        p = self._write("config.py", "import yaml\ndata = yaml.load(f)\n")
        findings = [
            {
                "file": str(p),
                "line": 2,
                "cwe": "CWE-502",
                "issue": "yaml unsafe",
                "severity": "MEDIUM",
                "code": "yaml.load(f)",
            }
        ]
        result = _apply_fixes_to_dir(Path(self._tmp_dir), findings)
        self.assertEqual(len(result), 1)
        self.assertIn("yaml.safe_load", p.read_text(encoding="utf-8"))

    def test_non_fixable_cwe_not_written(self):
        p = self._write("query.py", 'orm.query("FROM User WHERE id = " + user_id)\n')
        findings = [
            {
                "file": str(p),
                "line": 1,
                "cwe": "CWE-564",  # ORM SQL injection — still suggestion-only
                "issue": "ORM SQL injection",
                "severity": "CRITICAL",
                "code": "",
            }
        ]
        result = _apply_fixes_to_dir(Path(self._tmp_dir), findings)
        self.assertEqual(result, [], "Suggestion-only CWE must not produce a file write")

    def test_missing_file_skipped(self):
        findings = [
            {
                "file": str(Path(self._tmp_dir) / "nonexistent.py"),
                "line": 1,
                "cwe": "CWE-502",
                "issue": "yaml",
                "code": "yaml.load",
                "severity": "MEDIUM",
            }
        ]
        result = _apply_fixes_to_dir(Path(self._tmp_dir), findings)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# create_pr — input validation
# ---------------------------------------------------------------------------

class TestCreatePrValidation(unittest.TestCase):

    def test_missing_repo_url(self):
        result = create_pr({"auth_token": "tok", "repo_dir": "/tmp"})
        self.assertIn("error", result)

    def test_missing_auth_token(self):
        result = create_pr({"repo_url": "https://github.com/a/b", "repo_dir": "/tmp"})
        self.assertIn("error", result)

    def test_missing_repo_dir(self):
        result = create_pr({"repo_url": "https://github.com/a/b", "auth_token": "tok"})
        self.assertIn("error", result)

    def test_nonexistent_repo_dir(self):
        result = create_pr({
            "repo_url": "https://github.com/a/b",
            "auth_token": "tok",
            "repo_dir": "/definitely/does/not/exist",
        })
        self.assertIn("error", result)

    def test_unsupported_platform(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = create_pr({
                "repo_url": "https://gitlab.com/owner/repo",
                "auth_token": "tok",
                "repo_dir": tmpdir,
            })
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# create_pr — no fixable findings → no PR, clear reason given
# ---------------------------------------------------------------------------

class TestCreatePrNoFixableFindings(unittest.TestCase):

    def test_returns_skipped_when_no_auto_fixable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write a file with an ORM SQL finding that is still suggestion-only
            p = Path(tmpdir) / "q.py"
            p.write_text('orm.query("FROM User WHERE id = " + uid)\n', encoding="utf-8")
            result = create_pr({
                "repo_url": "https://github.com/owner/repo",
                "auth_token": "tok",
                "repo_dir": tmpdir,
                "findings": [
                    {
                        "file": str(p),
                        "line": 1,
                        "cwe": "CWE-564",  # ORM SQL — suggestion-only
                        "issue": "ORM SQL injection",
                        "severity": "CRITICAL",
                        "code": "",
                    }
                ],
                "pr_title": "Test PR",
            })
        self.assertNotIn("error", result, result)
        self.assertIn("skipped_reason", result)
        self.assertEqual(result["files_changed"], 0)


# ---------------------------------------------------------------------------
# create_pr — successful GitHub PR (mocked git + HTTP)
# ---------------------------------------------------------------------------

class TestCreatePrGitHubMocked(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._py_file = Path(self._tmp_dir) / "app.py"
        self._py_file.write_text("import yaml\ndata = yaml.load(f)\n", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _make_mock_repo(self):
        mock_repo = MagicMock()
        mock_branch = MagicMock()
        mock_repo.create_head.return_value = mock_branch
        mock_branch.checkout = MagicMock()
        mock_repo.index.add = MagicMock()
        mock_repo.index.commit = MagicMock()
        mock_origin = MagicMock()
        mock_origin.url = "https://github.com/owner/repo.git"
        mock_repo.remote.return_value = mock_origin
        mock_repo.git.execute = MagicMock()
        return mock_repo

    def _github_response(self):
        """Fake GitHub API response for PR creation."""
        data = {"html_url": "https://github.com/owner/repo/pull/42", "number": 42}
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 201
        mock_resp.read.return_value = json.dumps(data).encode()
        return mock_resp

    @patch("pr_creator.urlopen")
    @patch("pr_creator.Repo")
    @patch("pr_creator._GIT_AVAILABLE", True)
    def test_successful_github_pr(self, mock_repo_cls, mock_urlopen):
        mock_repo_cls.return_value = self._make_mock_repo()
        mock_urlopen.return_value = self._github_response()

        result = create_pr({
            "repo_url": "https://github.com/owner/repo",
            "base_branch": "main",
            "auth_token": "secret_token",
            "repo_dir": self._tmp_dir,
            "findings": [
                {
                    "file": str(self._py_file),
                    "line": 2,
                    "cwe": "CWE-502",
                    "issue": "yaml unsafe",
                    "severity": "MEDIUM",
                    "code": "yaml.load",
                }
            ],
            "pr_title": "Fix yaml.load",
            "pr_body": "Replaces unsafe yaml.load with yaml.safe_load",
        })

        self.assertNotIn("error", result, result)
        self.assertEqual(result["pr_url"], "https://github.com/owner/repo/pull/42")
        self.assertEqual(result["pr_number"], 42)
        self.assertEqual(result["platform"], "github")
        self.assertGreaterEqual(result["files_changed"], 1)

    @patch("pr_creator.urlopen")
    @patch("pr_creator.Repo")
    @patch("pr_creator._GIT_AVAILABLE", True)
    def test_token_not_in_return_value(self, mock_repo_cls, mock_urlopen):
        """Auth token must never appear in the returned dict."""
        mock_repo_cls.return_value = self._make_mock_repo()
        mock_urlopen.return_value = self._github_response()

        result = create_pr({
            "repo_url": "https://github.com/owner/repo",
            "base_branch": "main",
            "auth_token": "supersecrettoken999",
            "repo_dir": self._tmp_dir,
            "findings": [
                {
                    "file": str(self._py_file),
                    "line": 2,
                    "cwe": "CWE-502",
                    "issue": "yaml",
                    "severity": "MEDIUM",
                    "code": "yaml.load",
                }
            ],
            "pr_title": "Test",
        })

        result_str = json.dumps(result)
        self.assertNotIn("supersecrettoken999", result_str,
                         "Auth token must not appear in return value")


# ---------------------------------------------------------------------------
# _validate_build
# ---------------------------------------------------------------------------

class TestValidateBuild(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._repo_dir = Path(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_valid_python_file_passes(self):
        f = self._repo_dir / "ok.py"
        f.write_text("x = 1\n", encoding="utf-8")
        ok, err = _validate_build(self._repo_dir, ["ok.py"])
        self.assertTrue(ok)
        self.assertEqual(err, "")

    def test_invalid_python_syntax_fails(self):
        f = self._repo_dir / "bad.py"
        f.write_text("def foo(:\n    pass\n", encoding="utf-8")
        ok, err = _validate_build(self._repo_dir, ["bad.py"])
        self.assertFalse(ok)
        self.assertIn("bad.py", err)

    def test_no_files_passes(self):
        ok, err = _validate_build(self._repo_dir, [])
        self.assertTrue(ok)
        self.assertEqual(err, "")

    def test_non_py_non_cs_file_skipped(self):
        f = self._repo_dir / "report.html"
        f.write_text("<html></html>", encoding="utf-8")
        ok, err = _validate_build(self._repo_dir, ["report.html"])
        self.assertTrue(ok)

    def test_create_pr_aborts_on_build_failure(self):
        """create_pr must return error and NOT push if build validation fails."""
        repo_dir = Path(self._tmp)
        bad_py = repo_dir / "bad.py"
        bad_py.write_text("def foo(:\n    pass\n", encoding="utf-8")

        mock_repo = MagicMock()
        mock_branch = MagicMock()
        mock_repo.create_head.return_value = mock_branch
        mock_repo.git.execute = MagicMock()

        with patch("pr_creator._validate_build", return_value=(False, "SyntaxError: bad.py:1")), \
             patch("pr_creator._GIT_AVAILABLE", True), \
             patch("pr_creator.Repo", return_value=mock_repo):

            result = create_pr({
                "repo_url": "https://github.com/owner/repo",
                "base_branch": "main",
                "auth_token": "token",
                "repo_dir": str(repo_dir),
                "findings": [],
                "extra_files": ["bad.py"],
            })

            self.assertIn("error", result)
            self.assertIn("Build validation failed", result["error"])
            mock_repo.git.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Push fallback test
# ---------------------------------------------------------------------------

class TestPushFallback(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        py_file = Path(self._tmp_dir) / "app.py"
        py_file.write_text("import yaml\ndata = yaml.load(f)\n", encoding="utf-8")
        self._py_file = py_file

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _make_mock_repo(self):
        mock_repo = MagicMock()
        mock_branch = MagicMock()
        mock_repo.create_head.return_value = mock_branch
        mock_branch.checkout = MagicMock()
        mock_repo.index.add = MagicMock()
        mock_repo.index.commit = MagicMock()
        mock_origin = MagicMock()
        mock_origin.url = "https://github.com/owner/repo.git"
        mock_repo.remote.return_value = mock_origin
        mock_repo.git.execute = MagicMock()
        return mock_repo

    def _github_response(self):
        data = {"html_url": "https://github.com/owner/repo/pull/42", "number": 42}
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 201
        mock_resp.read.return_value = json.dumps(data).encode()
        return mock_resp

    @patch("pr_creator.urlopen")
    @patch("pr_creator.Repo")
    @patch("pr_creator._GIT_AVAILABLE", True)
    def test_push_falls_back_when_allow_unsafe_rejected(self, mock_repo_cls, mock_urlopen):
        """If git rejects --allow-unsafe-options, fall back to plain push."""
        from git import GitCommandError as _GCE

        mock_repo = self._make_mock_repo()
        mock_repo.git.execute = MagicMock(
            side_effect=_GCE("git push", "unknown switch `allow-unsafe-options'")
        )
        mock_repo.git.push = MagicMock()
        mock_repo.git.version_info = (2, 39, 0)
        mock_repo_cls.return_value = mock_repo
        mock_urlopen.return_value = self._github_response()

        result = create_pr({
            "repo_url": "https://github.com/owner/repo",
            "base_branch": "main",
            "auth_token": "secret_token",
            "repo_dir": self._tmp_dir,
            "findings": [
                {
                    "file": str(self._py_file),
                    "line": 2,
                    "cwe": "CWE-502",
                    "issue": "yaml unsafe",
                    "severity": "MEDIUM",
                    "code": "yaml.load",
                }
            ],
        })

        self.assertNotIn("error", result, result)
        mock_repo.git.push.assert_called_once_with("origin", result["branch_name"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
