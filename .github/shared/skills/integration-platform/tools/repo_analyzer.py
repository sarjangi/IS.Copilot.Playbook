"""
Repository Analyzer - Git repository cloning and scanning tools
MCP tool handlers for repository analysis and security scanning
"""

from typing import Dict, Any, List, Optional, Callable
import os
import tempfile
import shutil
from pathlib import Path
from urllib.parse import urlparse
import re
import logging

# Try to import GitPython - make it optional for graceful degradation
try:
    from git import Repo, GitCommandError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    # Provide dummy classes if git is not available
    class Repo:
        pass
    class GitCommandError(Exception):
        pass

# Disable logging to avoid interfering with MCP stdio protocol
logging.disable(logging.CRITICAL)

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def _parse_git_url(repo_url: str) -> Dict[str, str]:
    """
    Parse a Git URL and extract components.
    Supports: Azure DevOps, GitHub, GitLab, Bitbucket, and any Git server with HTTPS.
    Examples: https://dev.azure.com/org/_git/repo, https://github.com/user/repo
    """
    parsed = urlparse(repo_url)
    
    # Handle SSH URLs (git@github.com:user/repo.git or similar)
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
    Example: https://dev.azure.com/org/_git/repo -> https://TOKEN@dev.azure.com/org/_git/repo
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
# MCP Tool Handlers
# ============================================================================

def scan_repository(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clone a Git repository and scan it for security vulnerabilities.
    
    MCP Tool Handler - expects args dictionary with:
        repo_url: HTTPS Git URL (e.g., https://dev.azure.com/Vancity/_git/MyRepo)
        branch: Branch, tag, or commit to scan (default: "main")
        auth_token: Personal Access Token for private repos (optional)
        file_patterns: List of file patterns to scan (default: ['.py', '.js', '.ts', etc.])
        exclude_patterns: List of patterns to exclude (default: None)
        scan_type: Type of scan - 'security' or 'full' (default: 'security')
    
    Returns:
        Dictionary with scan results, statistics, and findings
    """
    # Check if GitPython is available
    if not GIT_AVAILABLE:
        return {
            "success": False,
            "error": "GitPython is not installed. Run: pip install GitPython>=3.1.40",
            "message": "Repository scanning requires GitPython library"
        }
    
    # Extract arguments
    repo_url = args.get("repo_url")
    branch = args.get("branch", "main")
    auth_token = args.get("auth_token")
    file_patterns = args.get("file_patterns")
    exclude_patterns = args.get("exclude_patterns")
    scan_type = args.get("scan_type", "security")
    
    if not repo_url:
        return {
            "success": False,
            "error": "repo_url is required"
        }
    
    temp_dir = None
    
    try:
        # Parse repository URL
        repo_info = _parse_git_url(repo_url)
        if not repo_info['repo']:
            return {
                "success": False,
                "error": f"Invalid repository URL: {repo_url}",
                "repository": repo_url
            }
        
        logger.info(f"Preparing to clone {repo_info['owner']}/{repo_info['repo']}...")
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix=f"integration_platform_scan_{repo_info['repo']}_")
        logger.info(f"Created temporary directory: {temp_dir}")
        
        # Prepare clone URL with authentication if provided
        clone_url = repo_url
        if auth_token and repo_url.startswith('http'):
            clone_url = _inject_auth_token(repo_url, auth_token)
            logger.info("Authentication token injected")
        
        # Clone repository
        logger.info(f"Cloning repository from {branch} branch...")
        try:
            repo = Repo.clone_from(
                clone_url,
                temp_dir,
                branch=branch,
                depth=1,  # Shallow clone for speed
                single_branch=True  # Only fetch specified branch
            )
            logger.info("Successfully cloned repository")
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
        logger.info("Analyzing repository structure...")
        commit_info = {
            "sha": repo.head.commit.hexsha[:8],
            "message": repo.head.commit.message.strip(),
            "author": str(repo.head.commit.author),
            "date": repo.head.commit.committed_datetime.isoformat()
        }
        
        # Filter files based on patterns
        logger.info("Finding files to scan...")
        files_to_scan = _filter_files(temp_dir, file_patterns, exclude_patterns)
        logger.info(f"Found {len(files_to_scan)} files to scan")
        
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
        logger.info("Scanning for security vulnerabilities...")
        
        if scan_type == "security":
            # Import SQL scanner
            from .sql_scanner import scan_sql_injection_directory
            
            scan_results = scan_sql_injection_directory({
                "directory_path": temp_dir,
                "recursive": True
            })
            
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
            
            logger.info("Scan completed")
            
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
        
        else:  # full scan - file enumeration
            logger.info("Analyzing file structure...")
            file_stats = {}
            for file_path in files_to_scan:
                ext = os.path.splitext(file_path)[1]
                file_stats[ext] = file_stats.get(ext, 0) + 1
            
            logger.info("Analysis completed")
            
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
        
        logger.error(f"Repository scan failed: {error_msg}")
        
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
                logger.info("Cleaning up temporary files...")
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info("Cleanup completed")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp directory: {cleanup_error}")


def list_repository_branches(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    List all branches in a remote Git repository.
    
    MCP Tool Handler - expects args dictionary with:
        repo_url: HTTPS Git URL (e.g., https://dev.azure.com/Vancity/_git/MyRepo)
        auth_token: Personal Access Token for private repos (optional)
    
    Returns:
        Dictionary with list of branch names
    """
    if not GIT_AVAILABLE:
        return {
            "success": False,
            "error": "GitPython is not installed. Run: pip install GitPython>=3.1.40"
        }
    
    repo_url = args.get("repo_url")
    auth_token = args.get("auth_token")
    
    if not repo_url:
        return {
            "success": False,
            "error": "repo_url is required"
        }
    
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


def check_repository_access(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if a repository is accessible (exists and user has permissions).
    
    MCP Tool Handler - expects args dictionary with:
        repo_url: HTTPS Git URL (e.g., https://dev.azure.com/Vancity/_git/MyRepo)
        auth_token: Personal Access Token for private repos (optional)
    
    Returns:
        Dictionary indicating if repository is accessible
    """
    if not GIT_AVAILABLE:
        return {
            "success": False,
            "error": "GitPython is not installed. Run: pip install GitPython>=3.1.40"
        }
    
    repo_url = args.get("repo_url")
    auth_token = args.get("auth_token")
    
    if not repo_url:
        return {
            "success": False,
            "error": "repo_url is required"
        }
    
    try:
        # Try to list branches to verify access
        result = list_repository_branches({"repo_url": repo_url, "auth_token": auth_token})
        
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
