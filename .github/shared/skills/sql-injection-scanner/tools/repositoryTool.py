"""
Repository Tools - Git repository cloning and scanning tools
Standalone version with authentication, branch selection, file filtering, and progress tracking
"""

from typing import Dict, Any, List, Optional, Callable
import os
import tempfile
import shutil
from pathlib import Path
from git import Repo, GitCommandError
from urllib.parse import urlparse
import re


# ============================================================================
# Helper Functions
# ============================================================================

def _parse_git_url(repo_url: str) -> Dict[str, str]:
    """
    Parse a Git URL and extract components.
    Supports: https://github.com/user/repo, git@github.com:user/repo.git, etc.
    """
    parsed = urlparse(repo_url)
    
    # Handle SSH URLs (git@github.com:user/repo.git)
    if repo_url.startswith('git@'):
        match = re.match(r'git@([^:]+):([^/]+)/(.+?)(\.git)?$', repo_url)
        if match:
            return {
                'host': match.group(1),
                'owner': match.group(2),
                'repo': match.group(3).replace('.git', ''),
                'protocol': 'ssh'
            }
    
    # Handle HTTPS URLs
    if parsed.scheme in ('https', 'http'):
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2:
            return {
                'host': parsed.netloc,
                'owner': path_parts[0],
                'repo': path_parts[1].replace('.git', ''),
                'protocol': parsed.scheme
            }
    
    return {'host': '', 'owner': '', 'repo': '', 'protocol': ''}


def _inject_auth_token(repo_url: str, auth_token: str) -> str:
    """
    Inject authentication token into HTTPS URL.
    Example: https://github.com/user/repo -> https://TOKEN@github.com/user/repo
    """
    if not auth_token or not repo_url.startswith('http'):
        return repo_url
    
    parsed = urlparse(repo_url)
    # Inject token as username in the URL
    authenticated_url = f"{parsed.scheme}://{auth_token}@{parsed.netloc}{parsed.path}"
    return authenticated_url


def _filter_files(
    directory: str,
    file_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None
) -> List[str]:
    """
    Get list of files matching patterns in a directory.
    
    Args:
        directory: Root directory to search
        file_patterns: List of glob patterns to include (e.g., ['*.py', '*.js'])
        exclude_patterns: List of patterns to exclude (e.g., ['test_*', '*_test.py'])
    
    Returns:
        List of absolute file paths
    """
    if file_patterns is None:
        file_patterns = ['*.py', '*.js', '*.ts', '*.sql', '*.cs', '*.java', '*.php']
    
    if exclude_patterns is None:
        exclude_patterns = []
    
    matched_files = []
    root_path = Path(directory)
    
    for pattern in file_patterns:
        # Use rglob for recursive pattern matching
        for file_path in root_path.rglob(pattern):
            # Check if file should be excluded
            should_exclude = False
            for exclude_pattern in exclude_patterns:
                if file_path.match(exclude_pattern):
                    should_exclude = True
                    break
            
            # Skip excluded directories
            path_str = str(file_path)
            if any(excluded in path_str for excluded in ['venv', 'node_modules', '__pycache__', '.git', 'build', 'dist']):
                should_exclude = True
            
            if not should_exclude and file_path.is_file():
                matched_files.append(str(file_path))
    
    return matched_files


# ============================================================================
# Tool Handlers
# ============================================================================

async def scan_repository_handler(
    repo_url: str,
    branch: str = "main",
    auth_token: Optional[str] = None,
    file_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    scan_type: str = "security",
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Dict[str, Any]:
    """
    Clone a Git repository and scan it for security vulnerabilities.
    
    Args:
        repo_url: HTTPS Git URL (e.g., https://github.com/user/repo)
        branch: Branch, tag, or commit to scan (default: "main")
        auth_token: GitHub Personal Access Token for private repos (optional)
        file_patterns: List of file patterns to scan (default: ['.py', '.js', '.ts', etc.])
        exclude_patterns: List of patterns to exclude (default: None)
        scan_type: Type of scan - 'security' or 'full' (default: 'security')
        progress_callback: Callback function(message: str, percent: int) for progress updates
    
    Returns:
        Dictionary with scan results, statistics, and findings
    """
    temp_dir = None
    
    def report_progress(message: str, percent: int):
        """Helper to report progress if callback provided"""
        if progress_callback:
            progress_callback(message, percent)
    
    try:
        # Parse repository URL
        repo_info = _parse_git_url(repo_url)
        if not repo_info['repo']:
            return {
                "success": False,
                "error": f"Invalid repository URL: {repo_url}",
                "repository": repo_url
            }
        
        report_progress(f"Preparing to clone {repo_info['owner']}/{repo_info['repo']}...", 5)
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix=f"aifcoder_scan_{repo_info['repo']}_")
        report_progress(f"Created temporary directory: {temp_dir}", 10)
        
        # Prepare clone URL with authentication if provided
        clone_url = repo_url
        if auth_token and repo_url.startswith('http'):
            clone_url = _inject_auth_token(repo_url, auth_token)
            report_progress("Authentication token injected", 15)
        
        # Clone repository
        report_progress(f"Cloning repository from {branch} branch...", 20)
        try:
            repo = Repo.clone_from(
                clone_url,
                temp_dir,
                branch=branch,
                depth=1,  # Shallow clone for speed
                single_branch=True  # Only fetch specified branch
            )
            report_progress(f"Successfully cloned repository", 40)
        except GitCommandError as e:
            error_msg = str(e)
            # Don't expose token in error message
            if auth_token:
                error_msg = error_msg.replace(auth_token, '***')
            return {
                "success": False,
                "error": f"Git clone failed: {error_msg}",
                "repository": repo_url,
                "branch": branch
            }
        
        # Get repository statistics
        report_progress("Analyzing repository structure...", 50)
        commit_info = {
            "sha": repo.head.commit.hexsha[:8],
            "message": repo.head.commit.message.strip(),
            "author": str(repo.head.commit.author),
            "date": repo.head.commit.committed_datetime.isoformat()
        }
        
        # Filter files based on patterns
        report_progress("Finding files to scan...", 55)
        files_to_scan = _filter_files(temp_dir, file_patterns, exclude_patterns)
        report_progress(f"Found {len(files_to_scan)} files to scan", 60)
        
        if not files_to_scan:
            return {
                "success": True,
                "repository": repo_url,
                "branch": branch,
                "commit": commit_info,
                "message": "No files matched the scan criteria",
                "files_scanned": 0,
                "findings": []
            }
        
        # Perform security scan using existing security tools
        report_progress("Scanning for security vulnerabilities...", 65)
        
        if scan_type == "security":
            # Import here to avoid circular dependency
            from .securityTool import scan_directory_handler
            
            scan_results = await scan_directory_handler(
                directory_path=temp_dir,
                recursive=True
            )
            
            # Filter results to only include files we want
            if scan_results.get('success'):
                all_findings = scan_results.get('findings', [])
                filtered_findings = [
                    f for f in all_findings 
                   if any(f.get('file', '').endswith(os.path.basename(scan_file)) 
                          for scan_file in files_to_scan)
                ]
                scan_results['findings'] = filtered_findings
                scan_results['total_vulnerabilities'] = len(filtered_findings)
            
            report_progress("Scan completed", 95)
            
            return {
                "success": True,
                "repository": repo_url,
                "branch": branch,
                "commit": commit_info,
                "temp_directory": temp_dir,
                "files_scanned": len(files_to_scan),
                "files_with_issues": scan_results.get('files_with_issues', 0),
                "total_vulnerabilities": scan_results.get('total_vulnerabilities', 0),
                "findings": scan_results.get('findings', []),
                "scan_summary": scan_results.get('summary', '')
            }
        
        else:  # full scan - just file enumeration for now
            report_progress("Analyzing file structure...", 90)
            file_stats = {}
            for file_path in files_to_scan:
                ext = os.path.splitext(file_path)[1]
                file_stats[ext] = file_stats.get(ext, 0) + 1
            
            report_progress("Analysis completed", 100)
            
            return {
                "success": True,
                "repository": repo_url,
                "branch": branch,
                "commit": commit_info,
                "temp_directory": temp_dir,
                "files_found": len(files_to_scan),
                "file_types": file_stats,
                "scan_type": "full"
            }
    
    except Exception as e:
        error_msg = str(e)
        # Don't expose sensitive information
        if auth_token:
            error_msg = error_msg.replace(auth_token, '***')
        
        return {
            "success": False,
            "error": error_msg,
            "repository": repo_url,
            "branch": branch if branch else "main"
        }
    
    finally:
        # Cleanup temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                report_progress("Cleaning up temporary files...", 98)
                shutil.rmtree(temp_dir, ignore_errors=True)
                report_progress("Cleanup completed", 100)
            except Exception as cleanup_error:
                # Log but don't fail the operation
                print(f"Warning: Failed to cleanup temp directory: {cleanup_error}")


async def list_repository_branches_handler(
    repo_url: str,
    auth_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    List all branches in a remote Git repository.
    
    Args:
        repo_url: HTTPS Git URL
        auth_token: GitHub Personal Access Token for private repos (optional)
    
    Returns:
        Dictionary with list of branch names
    """
    try:
        # Prepare URL with authentication
        clone_url = repo_url
        if auth_token and repo_url.startswith('http'):
            clone_url = _inject_auth_token(repo_url, auth_token)
        
        # Use git ls-remote to list branches without cloning
        from git.cmd import Git
        g = Git()
        
        output = g.ls_remote('--heads', clone_url)
        
        branches = []
        for line in output.splitlines():
            if line:
                # Parse: "sha\trefs/heads/branch-name"
                parts = line.split('\t')
                if len(parts) == 2 and 'refs/heads/' in parts[1]:
                    branch_name = parts[1].replace('refs/heads/', '')
                    branches.append(branch_name)
        
        return {
            "success": True,
            "repository": repo_url,
            "branches": branches,
            "total_branches": len(branches)
        }
    
    except Exception as e:
        error_msg = str(e)
        if auth_token:
            error_msg = error_msg.replace(auth_token, '***')
        
        return {
            "success": False,
            "error": error_msg,
            "repository": repo_url
        }


async def check_repository_access_handler(
    repo_url: str,
    auth_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check if a repository is accessible (exists and user has permissions).
    
    Args:
        repo_url: HTTPS Git URL
        auth_token: GitHub Personal Access Token for private repos (optional)
    
    Returns:
        Dictionary indicating if repository is accessible
    """
    try:
        # Try to list branches to verify access
        result = await list_repository_branches_handler(repo_url, auth_token)
        
        if result.get('success'):
            return {
                "success": True,
                "accessible": True,
                "repository": repo_url,
                "message": f"Repository is accessible. Found {result.get('total_branches', 0)} branches."
            }
        else:
            return {
                "success": True,
                "accessible": False,
                "repository": repo_url,
                "message": f"Repository not accessible: {result.get('error', 'Unknown error')}"
            }
    
    except Exception as e:
        return {
            "success": False,
            "accessible": False,
            "repository": repo_url,
            "error": str(e)
        }


# ============================================================================
# Tool Definitions (For Agent Framework) - NOT USED IN STANDALONE VERSION
# ============================================================================
# The following FunctionTool definitions are only used when integrated with
# agent-framework-github-copilot. For standalone CLI usage, use the handler
# functions directly (scan_repository_handler, etc.)

if False:  # Disabled for standalone usage
    SCAN_REPOSITORY_TOOL = FunctionTool(
    name="scan_repository",
    description="""Clone a Git repository and scan it for SQL injection vulnerabilities.

Supports ALL Git hosting providers:
- GitHub: https://github.com/owner/repo
- Azure DevOps: https://dev.azure.com/org/project/_git/repo
- GitLab: https://gitlab.com/owner/repo
- Bitbucket: https://bitbucket.org/owner/repo
- Any Git server with HTTPS access

Authentication:
- Uses existing Git credentials by default (Windows auth, cached credentials)
- auth_token is OPTIONAL - only needed if automatic authentication fails
- Most corporate environments work without explicit tokens

Features:
- Automatic or token-based authentication
- Branch/tag/commit selection
- File pattern filtering
- Progress tracking

Use this when user asks to scan ANY Git repository URL. 
Try WITHOUT auth_token first - only use token if authentication fails.""",
    parameters={
        "type": "object",
        "properties": {
            "repo_url": {
                "type": "string",
                "description": "HTTPS Git URL (e.g., https://github.com/user/repo)"
            },
            "branch": {
                "type": "string",
                "description": "Branch, tag, or commit to scan (default: 'main')"
            },
            "auth_token": {
                "type": "string",
                "description": "GitHub Personal Access Token for private repos (optional)"
            },
            "file_patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of file patterns to scan (e.g., ['*.py', '*.js'])"
            },
            "exclude_patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of patterns to exclude (e.g., ['test_*.py'])"
            },
            "scan_type": {
                "type": "string",
                "enum": ["security", "full"],
                "description": "Type of scan - 'security' or 'full' (default: 'security')"
            }
        },
        "required": ["repo_url"]
    },
    handler=scan_repository_handler
)

    LIST_BRANCHES_TOOL = FunctionTool(
    name="list_repository_branches",
    description="""List all branches in a remote Git repository (GitHub, Azure DevOps, GitLab, etc.).

Works with any Git hosting provider. Useful to see available branches before scanning.

Use this when user asks: 'what branches are in...', 'list branches', 'show branches'.""",
    parameters={
        "type": "object",
        "properties": {
            "repo_url": {
                "type": "string",
                "description": "HTTPS Git URL"
            },
            "auth_token": {
                "type": "string",
                "description": "GitHub Personal Access Token for private repos (optional)"
            }
        },
        "required": ["repo_url"]
    },
    handler=list_repository_branches_handler
)

    CHECK_ACCESS_TOOL = FunctionTool(
    name="check_repository_access",
    description="""Check if a Git repository (GitHub, Azure DevOps, GitLab, etc.) is accessible.

Verifies:
- Repository exists
- Authentication works (if token provided)
- User has read permissions

Use this to validate access before scanning, especially for private repos.""",
    parameters={
        "type": "object",
        "properties": {
            "repo_url": {
                "type": "string",
                "description": "HTTPS Git URL"
            },
            "auth_token": {
                "type": "string",
                "description": "GitHub Personal Access Token for private repos (optional)"
            }
        },
        "required": ["repo_url"]
    },
    handler=check_repository_access_handler
)

# Export all tools
    ALL_REPOSITORY_TOOLS = [
    SCAN_REPOSITORY_TOOL,
    LIST_BRANCHES_TOOL,
    CHECK_ACCESS_TOOL,
]
