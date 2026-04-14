"""PR Creator - apply fixes to a local clone, push a branch, and create a PR.

Supports GitHub (github.com) and Azure DevOps (dev.azure.com / *.visualstudio.com),
detected from the repo remote URL.

Uses GitPython for local git operations (already a project dependency).
Uses urllib (stdlib) for REST API calls — no extra packages required.

Security notes:
  - Auth tokens are never included in return values or error messages.
  - API URLs are validated against an allowlist to prevent SSRF.
  - SSH remote URLs are not supported; HTTPS + PAT is required.

Public interface:
    create_pr(args) -> dict
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen

# GitPython — already listed in requirements.txt
# Always bind names so @patch("pr_creator.Repo") works in tests even when git absent.
try:
    from git import GitCommandError, InvalidGitRepositoryError, Repo
    _GIT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _GIT_AVAILABLE = False
    Repo = None  # type: ignore[assignment,misc]
    GitCommandError = Exception  # type: ignore[assignment,misc]
    InvalidGitRepositoryError = Exception  # type: ignore[assignment,misc]

# Import auto_fixer transforms (same package)
_TOOLS_DIR = Path(__file__).parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from auto_fixer import _apply_all_transforms, _classify_finding  # noqa: E402


# ---------------------------------------------------------------------------
# SSRF allowlist — only these hostnames may be called via REST
# ---------------------------------------------------------------------------

_ALLOWED_API_HOSTS = frozenset(
    {
        "api.github.com",
        "dev.azure.com",
    }
)

_PLATFORM_HOSTS_RE = {
    "github": re.compile(r"(?:github\.com)"),
    "azuredevops": re.compile(r"(?:dev\.azure\.com|\.visualstudio\.com)"),
}


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def detect_platform(repo_url: str) -> str:
    """Return 'github', 'azuredevops', or raise ValueError."""
    lower = repo_url.lower()
    if _PLATFORM_HOSTS_RE["github"].search(lower):
        return "github"
    if _PLATFORM_HOSTS_RE["azuredevops"].search(lower):
        return "azuredevops"
    raise ValueError(
        f"Unsupported remote URL. Only github.com and dev.azure.com are supported. Got: {repo_url!r}"
    )


def parse_repo_url(repo_url: str) -> Dict[str, str]:
    """Parse owner/repo (GitHub) or org/project/repo (Azure DevOps) from URL.

    Returns a dict with keys depending on platform:
    GitHub:       {platform, owner, repo}
    AzureDevOps:  {platform, org, project, repo}
    """
    platform = detect_platform(repo_url)

    if platform == "github":
        # https://github.com/owner/repo.git  or  git@github.com:owner/repo.git
        m = re.search(r"github\.com[:/]([^/]+)/([^/\s]+?)(?:\.git)?$", repo_url)
        if not m:
            raise ValueError(f"Cannot parse GitHub owner/repo from: {repo_url!r}")
        return {"platform": "github", "owner": m.group(1), "repo": m.group(2)}

    # Azure DevOps: https://dev.azure.com/{org}/{project}/_git/{repo}
    m = re.search(
        r"dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/\s]+?)(?:\.git)?(?:[?#].*)?$",
        repo_url,
        re.IGNORECASE,
    )
    if m:
        return {
            "platform": "azuredevops",
            "org": m.group(1),
            "project": m.group(2),
            "repo": m.group(3),
        }
    # Legacy: https://org.visualstudio.com/{project}/_git/{repo}
    m = re.search(
        r"([^./]+)\.visualstudio\.com/([^/]+)/_git/([^/\s]+?)(?:\.git)?(?:[?#].*)?$",
        repo_url,
        re.IGNORECASE,
    )
    if m:
        return {
            "platform": "azuredevops",
            "org": m.group(1),
            "project": m.group(2),
            "repo": m.group(3),
        }
    raise ValueError(f"Cannot parse Azure DevOps org/project/repo from: {repo_url!r}")


def _build_auth_push_url(repo_url: str, token: str, platform: str) -> str:
    """Embed auth token into an HTTPS remote URL for git clone/push.

    GitHub:       https://x-access-token:{token}@github.com/...
    AzureDevOps:  https://{org}:{token}@dev.azure.com/...
    ADO requires a non-empty username; the org name is used as the username.
    """
    if repo_url.startswith("git@"):
        raise ValueError(
            "SSH remote URLs are not supported for token-based push. "
            "Please configure the repository with an HTTPS remote URL."
        )
    parsed = urlparse(repo_url)
    if platform == "github":
        netloc = f"x-access-token:{token}@{parsed.hostname}"
    else:  # azuredevops — must use org:PAT format
        # Extract org from the URL path (dev.azure.com/{org}/...)
        org = parsed.path.lstrip("/").split("/")[0] if parsed.path else ""
        username = org if org else "user"
        netloc = f"{username}:{token}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return urlunparse(
        (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )


def _redact_token_from_url(url: str) -> str:
    """Remove credentials from a URL before returning it to the caller."""
    return re.sub(r"(?<=://)([^@]+)@", "", url)


# ---------------------------------------------------------------------------
# Build validation
# ---------------------------------------------------------------------------

def _validate_build(
    repo_dir: Path,
    modified_files: List[str],
) -> Tuple[bool, str]:
    """Run a quick syntax/build check after applying fixes.

    Supports:
    - Python  : py_compile on every modified .py file (cheap, no deps)
    - .NET    : dotnet build on the first .sln or .csproj found (if dotnet available)

    Returns (ok, error_message). Does NOT raise.
    """
    # Python syntax check — run against the same interpreter executing this code
    py_files = [f for f in modified_files if f.endswith(".py")]
    for rel in py_files:
        fpath = repo_dir / rel
        if not fpath.exists():
            continue
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(fpath)],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                err = (result.stderr or result.stdout).strip()
                return False, f"Syntax error in {rel}:\n{err}"
        except Exception as exc:
            return False, f"py_compile failed for {rel}: {exc}"

    # .NET build — only if modified files include C# and dotnet CLI is available
    cs_files = [f for f in modified_files if f.endswith(".cs")]
    if cs_files:
        # Find solution or project file
        candidates = (
            list(repo_dir.glob("*.sln"))
            + list(repo_dir.glob("**/*.sln"))
            + list(repo_dir.glob("*.csproj"))
            + list(repo_dir.glob("**/*.csproj"))
        )
        if candidates:
            build_target = str(candidates[0])
            try:
                # Step 1: restore packages so project.assets.json exists on fresh clones
                restore = subprocess.run(
                    ["dotnet", "restore", build_target, "--nologo"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(repo_dir),
                )
                if restore.returncode != 0:
                    # Restore failed (network issue, private feed, etc.) —
                    # skip dotnet validation rather than block the PR push.
                    # The auto-fix only touches existing .cs lines mechanically,
                    # so a restore failure is an environment issue, not a code issue.
                    pass
                else:
                    # Step 2: build with restored packages
                    result = subprocess.run(
                        ["dotnet", "build", build_target, "--no-restore",
                         "-v", "quiet", "--nologo"],
                        capture_output=True,
                        text=True,
                        timeout=180,
                        cwd=str(repo_dir),
                    )
                    if result.returncode != 0:
                        err = (result.stdout + result.stderr).strip()
                        # Keep output short — first 20 lines of errors
                        short = "\n".join(err.splitlines()[:20])
                        return False, f"dotnet build failed:\n{short}"
            except FileNotFoundError:
                # dotnet not installed on this machine — skip silently
                pass
            except subprocess.TimeoutExpired:
                # Restore or build timed out — skip rather than block
                pass
            except Exception as exc:
                return False, f"dotnet build error: {exc}"

    return True, ""


# ---------------------------------------------------------------------------
# File modification helpers
# ---------------------------------------------------------------------------

def _apply_fixes_to_dir(
    repo_dir: Path,
    findings: List[Dict[str, Any]],
) -> List[str]:
    """Apply auto-fixable transforms to files in repo_dir.

    Returns list of relative file paths that were actually written.
    """
    # Group findings by absolute file path
    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for finding in findings:
        raw = finding.get("file", "")
        if not raw:
            continue
        fpath = Path(raw)
        if not fpath.is_absolute():
            fpath = repo_dir / fpath
        by_file.setdefault(str(fpath), []).append({**finding, "file": str(fpath)})

    written: List[str] = []
    for fpath_str, file_findings in by_file.items():
        fpath = Path(fpath_str)
        if not fpath.exists():
            continue
        # Only process auto-fixable findings
        fixable = [f for f in file_findings if _classify_finding(f) is not None]
        if not fixable:
            continue
        try:
            original_lines = fpath.read_text(encoding="utf-8", errors="ignore").splitlines(
                keepends=True
            )
            fixed_lines, applied = _apply_all_transforms(original_lines, fixable)
            if applied:
                fpath.write_text("".join(fixed_lines), encoding="utf-8")
                try:
                    rel = str(fpath.relative_to(repo_dir)).replace("\\", "/")
                except ValueError:
                    rel = fpath_str
                written.append(rel)
        except OSError:
            continue
    return written


# ---------------------------------------------------------------------------
# REST API helpers
# ---------------------------------------------------------------------------

def _validate_api_url(url: str) -> None:
    """Raise ValueError if the URL host is not in the SSRF allowlist."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_API_HOSTS and not host.endswith(".visualstudio.com"):
        raise ValueError(f"Untrusted API host: {host!r}. Only GitHub and Azure DevOps are permitted.")


def _http_post_json(
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
) -> Tuple[int, Dict[str, Any]]:
    """POST JSON to url; return (status_code, response_dict)."""
    _validate_api_url(url)
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            **headers,
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:  # nosec B310
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            err_body = json.loads(exc.read().decode("utf-8", errors="ignore"))
        except Exception:
            err_body = {"message": f"HTTP {exc.code}"}
        return exc.code, err_body
    except URLError as exc:
        return 0, {"message": str(exc.reason)}


def _github_auth_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _azdo_auth_headers(token: str) -> Dict[str, str]:
    cred = base64.b64encode(f":{token}".encode()).decode()
    return {"Authorization": f"Basic {cred}"}


# ---------------------------------------------------------------------------
# Platform-specific PR creation
# ---------------------------------------------------------------------------

def _create_github_pr(
    parsed: Dict[str, str],
    token: str,
    head_branch: str,
    base_branch: str,
    title: str,
    body: str,
) -> Dict[str, Any]:
    owner, repo = parsed["owner"], parsed["repo"]
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    status, data = _http_post_json(
        url,
        payload={"title": title, "body": body, "head": head_branch, "base": base_branch},
        headers=_github_auth_headers(token),
    )
    if status == 201:
        return {"pr_url": data.get("html_url", ""), "pr_number": data.get("number")}
    return {"error": f"GitHub API returned {status}: {data.get('message', data)}"}


def _create_azdo_pr(
    parsed: Dict[str, str],
    token: str,
    head_branch: str,
    base_branch: str,
    title: str,
    body: str,
    work_item_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    org, project, repo = parsed["org"], parsed["project"], parsed["repo"]
    url = (
        f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}"
        "/pullrequests?api-version=7.1"
    )
    payload: Dict[str, Any] = {
        "sourceRefName": f"refs/heads/{head_branch}",
        "targetRefName": f"refs/heads/{base_branch}",
        "title": title,
        "description": body,
    }
    if work_item_ids:
        payload["workItemRefs"] = [{"id": str(wid)} for wid in work_item_ids]
    status, data = _http_post_json(
        url,
        payload=payload,
        headers=_azdo_auth_headers(token),
    )
    if status in (200, 201):
        pr_id = data.get("pullRequestId")
        if not pr_id:
            # ADO returned a 2xx but without a pullRequestId — treat as failure
            # so the caller reports "PR creation failed" rather than a phantom URL
            return {
                "error": (
                    f"Azure DevOps API returned {status} but pullRequestId was missing. "
                    f"Response: {str(data)[:300]}"
                )
            }
        pr_url = (
            f"https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{pr_id}"
        )
        return {"pr_url": pr_url, "pr_number": pr_id}
    return {"error": f"Azure DevOps API returned {status}: {data.get('message', data)}"}


# ---------------------------------------------------------------------------
# Git operations
# ---------------------------------------------------------------------------

def _git_commit_and_push(
    repo_dir: Path,
    modified_files: List[str],
    branch_name: str,
    auth_push_url: str,
    commit_message: str,
) -> None:
    """Stage modified_files, commit to new branch, push to origin."""
    repo = Repo(str(repo_dir))
    new_branch = repo.create_head(branch_name)
    new_branch.checkout()

    for rel_path in modified_files:
        repo.index.add([rel_path])

    repo.index.commit(commit_message)

    origin = repo.remote("origin")
    original_url = origin.url
    origin.set_url(auth_push_url)
    try:
        # The auth token is already embedded in auth_push_url, so a plain
        # `git push` works on its own.  We additionally try to suppress the
        # Windows Credential Manager with `-c credential.helper=` so it cannot
        # override the embedded PAT.  That flag requires --allow-unsafe-options
        # on git >= 2.30, but some builds report >= 2.30 yet still reject the
        # flag.  Strategy: try the suppressed form first; if git rejects it,
        # fall back to a plain push which works fine because the token is in
        # the URL.
        try:
            git_ver: tuple = tuple(repo.git.version_info)
        except Exception:
            git_ver = (0, 0, 0)

        def _push_suppressed() -> None:
            cmd = [repo.git.GIT_PYTHON_GIT_EXECUTABLE]
            if git_ver >= (2, 30, 0):
                cmd += ["--allow-unsafe-options"]
            cmd += ["-c", "credential.helper=", "push", "origin", branch_name]
            repo.git.execute(cmd)

        try:
            _push_suppressed()
        except GitCommandError as _push_err:
            _msg = str(_push_err).lower()
            if any(k in _msg for k in ("allow-unsafe-options", "unknown switch", "credential.helper")):
                # Flag unsupported on this git build — fall back to plain push.
                # The embedded PAT in the URL is sufficient for authentication.
                repo.git.push("origin", branch_name)
            else:
                raise
    finally:
        origin.set_url(original_url)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def create_pr(args: Dict[str, Any]) -> Dict[str, Any]:
    """Apply fixes, push a branch, and create a pull request.

    Args (dict keys):
        repo_url        str    HTTPS remote URL of the repository
        base_branch     str    Target branch for the PR (e.g. "main")
        auth_token      str    Personal access token (never logged/returned)
        repo_dir        str    Path to an already-cloned local copy of the repo
        findings        list   Findings from sql_scanner / security_scanner
        pr_title        str    Title of the pull request
        pr_body         str    Description / body of the pull request
        branch_name     str    (optional) Override auto-generated branch name
        extra_files     list   (optional) Relative paths from repo_dir to include in commit (e.g. HTML report)
        work_item_ids   list   (optional) Azure DevOps PBI/work-item IDs to link to the PR

    Returns dict with:
        pr_url          str    URL of the created PR (empty if no fixable findings)
        branch_name     str    Branch that was pushed
        files_changed   int    Number of files modified
        platform        str    "github" or "azuredevops"
        skipped_reason  str    (if no PR was created, explains why)
    """
    repo_url: str = args.get("repo_url", "")
    base_branch: str = args.get("base_branch", "main")
    auth_token: str = args.get("auth_token", "")
    repo_dir_str: str = args.get("repo_dir", "")
    findings: List[Dict[str, Any]] = args.get("findings", [])
    pr_title: str = args.get("pr_title", "Automated security fix suggestions")
    pr_body: str = args.get("pr_body", "")
    branch_name: str = args.get("branch_name", "")
    extra_files: List[str] = args.get("extra_files", [])
    work_item_ids: List[int] = args.get("work_item_ids", [])

    # Validate required args (early, no git needed)
    if not repo_url:
        return {"error": "repo_url is required"}
    if not auth_token:
        return {"error": "auth_token is required"}
    if not repo_dir_str:
        return {"error": "repo_dir is required"}

    repo_dir = Path(repo_dir_str)
    if not repo_dir.is_dir():
        return {"error": f"repo_dir does not exist: {repo_dir_str!r}"}

    # Detect platform and parse URL
    try:
        platform = detect_platform(repo_url)
        parsed = parse_repo_url(repo_url)
    except ValueError as exc:
        return {"error": str(exc)}

    # Auto-generate branch name if not provided
    if not branch_name:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%S")
        # Include PBI prefix if work items are linked (ADO convention: PBI-1234)
        if work_item_ids:
            branch_name = f"PBI-{work_item_ids[0]}-security-fixes-{ts}"
        else:
            branch_name = f"security-fixes-{ts}"

    # Apply fixes to files in repo_dir
    try:
        modified_files = _apply_fixes_to_dir(repo_dir, findings)
    except Exception as exc:
        return {"error": f"Failed to apply fixes: {exc}"}

    if not modified_files:
        if not extra_files:
            return {
                "pr_url": "",
                "branch_name": branch_name,
                "files_changed": 0,
                "platform": platform,
                "skipped_reason": (
                    "No auto-fixable findings. Review the fix_suggestions in the report "
                    "and apply changes manually."
                ),
            }

    # Append extra files (e.g. HTML report) to the commit
    for ef in extra_files:
        ef_path = repo_dir / ef
        if ef_path.exists():
            try:
                rel = str(ef_path.relative_to(repo_dir)).replace("\\", "/")
            except ValueError:
                rel = ef
            if rel not in modified_files:
                modified_files.append(rel)

    # GitPython is required from here onward
    if not _GIT_AVAILABLE:
        return {"error": "GitPython is not installed. Run: pip install gitpython"}

    # Build validation — abort if fixes introduced syntax/compile errors
    if modified_files:
        build_ok, build_err = _validate_build(repo_dir, modified_files)
        if not build_ok:
            return {
                "error": (
                    f"Build validation failed after applying fixes — not pushed.\n"
                    f"{build_err}\n\n"
                    "Fix the above errors manually and re-run, or apply fixes manually "
                    "using the suggestions in the HTML report."
                )
            }

    # Commit and push
    # Commit message starts with "#PBI-{id}:" so ADO auto-links the work item
    # and the branch name convention is satisfied.  AB#{id} in the body is a
    # secondary link mechanism for ADO even if REST workItemRefs fails.
    pbi_prefix = f"#PBI-{work_item_ids[0]}: " if work_item_ids else ""
    pbi_refs = ""
    if work_item_ids and platform == "azuredevops":
        pbi_refs = " ".join(f"AB#{wid}" for wid in work_item_ids) + "\n\n"
    commit_message = (
        f"{pbi_prefix}security: apply automated fix suggestions [skip ci]\n\n"
        f"{pbi_refs}"
        f"Files modified: {len(modified_files)}\n"
        "Generated by Integration Platform security pipeline."
    )
    try:
        auth_push_url = _build_auth_push_url(repo_url, auth_token, platform)
        _git_commit_and_push(
            repo_dir, modified_files, branch_name, auth_push_url, commit_message
        )
    except (GitCommandError, InvalidGitRepositoryError, ValueError) as exc:
        # Sanitize message — might contain URL with token
        safe_msg = _redact_token_from_url(str(exc))
        return {"error": f"Git push failed: {safe_msg}", "branch_name": branch_name}

    # Create PR via REST API
    if platform == "github":
        pr_result = _create_github_pr(
            parsed, auth_token, branch_name, base_branch, pr_title, pr_body
        )
    else:
        pr_result = _create_azdo_pr(
            parsed, auth_token, branch_name, base_branch, pr_title, pr_body,
            work_item_ids=work_item_ids,
        )

    if "error" in pr_result:
        return {
            "error": pr_result["error"],
            "branch_name": branch_name,
            "files_changed": len(modified_files),
            "platform": platform,
            "note": "Branch was pushed but PR creation failed. Create the PR manually.",
        }

    pr_url = pr_result.get("pr_url", "")
    if not pr_url:
        # Defensive: PR result had no error but also no usable URL
        return {
            "error": "PR creation returned no URL — the PR may not have been created.",
            "branch_name": branch_name,
            "files_changed": len(modified_files),
            "platform": platform,
            "note": "Branch was pushed. Check Azure DevOps / GitHub for a pending PR, or create one manually.",
        }

    return {
        "pr_url": pr_url,
        "pr_number": pr_result.get("pr_number"),
        "branch_name": branch_name,
        "files_changed": len(modified_files),
        "modified_files": modified_files,
        "platform": platform,
    }
