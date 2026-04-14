#!/usr/bin/env python3
"""
Integration Platform - Command Line Interface
Unified security scanning and repository analysis tools
"""

import argparse
import json
import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.sql_scanner import (
    scan_sql_injection_file,
    scan_sql_injection_directory,
    check_parameterized_query,
    generate_scan_report,
    generate_html_report
)
from tools.repo_analyzer import (
    scan_repository,
    list_repository_branches,
    check_repository_access
)


def main():
    parser = argparse.ArgumentParser(
        description='Integration Platform - Unified security and analysis tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan a single file for SQL injection
  python cli.py scan-file ./app/database.py
  
  # Scan entire directory recursively
  python cli.py scan-dir ./src --recursive
  
  # Check if code uses parameterized queries
  python cli.py check-params "SELECT * FROM users WHERE id = ?"
  
  # Generate HTML report from scan results
  python cli.py scan-dir ./src --html security-report.html
  
  # Scan Azure DevOps repository
  python cli.py scan-repo https://dev.azure.com/Vancity/_git/MyRepo --branch master
  
  # List branches in repository
  python cli.py list-branches https://dev.azure.com/Vancity/_git/MyRepo
  
  # Check repository access
  python cli.py check-access https://github.com/user/repo --token YOUR_TOKEN
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Scan file command
    scan_file_parser = subparsers.add_parser('scan-file', help='Scan a single file for SQL injection')
    scan_file_parser.add_argument('file_path', help='Path to file to scan')
    scan_file_parser.add_argument('--json', action='store_true', help='Output as JSON')
    scan_file_parser.add_argument('--html', type=str, metavar='FILE', help='Generate HTML report to FILE')
    
    # Scan directory command
    scan_dir_parser = subparsers.add_parser('scan-dir', help='Scan a directory for SQL injection')
    scan_dir_parser.add_argument('directory', help='Directory to scan')
    scan_dir_parser.add_argument('--recursive', action='store_true', default=True, help='Recursive scan (default)')
    scan_dir_parser.add_argument('--json', action='store_true', help='Output as JSON')
    scan_dir_parser.add_argument('--html', type=str, metavar='FILE', help='Generate HTML report to FILE')
    
    # Check parameterized queries
    check_params_parser = subparsers.add_parser('check-params', help='Check if code uses safe parameterized queries')
    check_params_parser.add_argument('code', help='SQL code snippet to analyze')
    check_params_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Repository commands
    scan_repo_parser = subparsers.add_parser('scan-repo', help='Scan a Git repository')
    scan_repo_parser.add_argument('repo_url', help='Repository URL (GitHub, Azure DevOps, GitLab, etc.)')
    scan_repo_parser.add_argument('--branch', default='main', help='Branch to scan (default: main)')
    scan_repo_parser.add_argument('--token', help='Authentication token for private repos')
    scan_repo_parser.add_argument('--json', action='store_true', help='Output as JSON')
    scan_repo_parser.add_argument('--html', type=str, metavar='FILE', help='Generate HTML report to FILE')
    
    list_branches_parser = subparsers.add_parser('list-branches', help='List repository branches')
    list_branches_parser.add_argument('repo_url', help='Repository URL')
    list_branches_parser.add_argument('--token', help='Authentication token for private repos')
    
    check_access_parser = subparsers.add_parser('check-access', help='Check repository access')
    check_access_parser.add_argument('repo_url', help='Repository URL')
    check_access_parser.add_argument('--token', help='Authentication token')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        # Execute command
        if args.command == 'scan-file':
            result = scan_sql_injection_file({"file_path": args.file_path})
            
        elif args.command == 'scan-dir':
            result = scan_sql_injection_directory({
                "directory_path": args.directory, 
                "recursive": args.recursive
            })
            
        elif args.command == 'check-params':
            result = check_parameterized_query({"code_snippet": args.code})
        
        elif args.command == 'scan-repo':
            result = scan_repository({
                "repo_url": args.repo_url,
                "branch": args.branch,
                "auth_token": args.token,
                "scan_type": "security"
            })
        
        elif args.command == 'list-branches':
            result = list_repository_branches({
                "repo_url": args.repo_url,
                "auth_token": args.token
            })
        
        elif args.command == 'check-access':
            result = check_repository_access({
                "repo_url": args.repo_url,
                "auth_token": args.token
            })
        
        # Output handling
        if args.command in ['scan-file', 'scan-dir', 'scan-repo']:
            # Generate HTML report if requested
            if hasattr(args, 'html') and args.html:
                findings = result.get('findings', [])
                scan_path = (args.file_path if args.command == 'scan-file' else 
                            args.directory if args.command == 'scan-dir' else 
                            args.repo_url)
                html_result = generate_html_report({
                    "findings": findings,
                    "output_file": args.html,
                    "scan_path": scan_path
                })
                if html_result.get('success'):
                    print(f"✅ HTML report generated: {args.html}")
                    print(f"   Total findings: {html_result.get('total_findings', 0)}")
                else:
                    print(f"❌ Failed to generate HTML: {html_result.get('error')}")
            
            # Output JSON if requested
            if hasattr(args, 'json') and args.json:
                print(json.dumps(result, indent=2))
            # Otherwise console output
            elif not (hasattr(args, 'html') and args.html):
                if isinstance(result, dict):
                    if 'error' in result:
                        print(f"❌ Error: {result['error']}")
                        return 1
                    elif 'message' in result:
                        print(result['message'])
                    elif 'findings' in result:
                        print(f"\nScan Results:")
                        print(f"Files scanned: {result.get('files_scanned', 'N/A')}")
                        print(f"Issues found: {len(result['findings'])}")
                        if result['findings']:
                            print("\nFindings:")
                            for finding in result['findings']:
                                print(f"  [{finding.get('severity', 'UNKNOWN')}] {finding.get('file', 'unknown')}:{finding.get('line', '?')}")
                                issue_desc = finding.get('issue', finding.get('message', finding.get('pattern', 'No description')))
                                print(f"    {issue_desc}")
                    else:
                        print(json.dumps(result, indent=2))
                else:
                    print(result)
        
        elif args.command == 'check-params':
            # Output for parameterized query check
            if hasattr(args, 'json') and args.json:
                print(json.dumps(result, indent=2))
            else:
                if result.get('is_safe'):
                    print(f"✅ Safe: {result.get('message', 'Uses parameterized queries')}")
                else:
                    print(f"⚠️ Unsafe: {result.get('message', 'Does not use parameterized queries')}")
                    if 'recommendations' in result:
                        print("Recommendations:")
                        for rec in result['recommendations']:
                            print(f"  • {rec}")
        
        elif args.command == 'list-branches':
            # Output for list branches
            if isinstance(result, dict):
                if 'error' in result:
                    print(f"❌ Error: {result['error']}")
                    return 1
                elif 'branches' in result:
                    print(f"\nFound {len(result['branches'])} branches:")
                    for branch in result['branches']:
                        print(f"  - {branch}")
                else:
                    print(json.dumps(result, indent=2))
        
        elif args.command == 'check-access':
            # Output for check access
            if isinstance(result, dict):
                if 'error' in result:
                    print(f"❌ Error: {result['error']}")
                    return 1
                elif result.get('accessible'):
                    print(f"✅ {result.get('message', 'Repository is accessible')}")
                else:
                    print(f"⚠️ {result.get('message', 'Repository not accessible')}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def cli_main():
    """Entry point for console_scripts."""
    sys.exit(main())


if __name__ == '__main__':
    cli_main()
