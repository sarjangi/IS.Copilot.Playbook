#!/usr/bin/env python3
"""
SQL Injection Scanner - Command Line Interface
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from tools import (
    scan_file_handler,
    scan_directory_handler,
    scan_repository_handler,
    list_repository_branches_handler,
    check_repository_access_handler
)
from tools.securityTool import generate_html_report_handler


async def main():
    parser = argparse.ArgumentParser(
        description='SQL Injection Scanner - Automated security scanning',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan a single file
  python cli.py scan-file ./app/database.py
  
  # Scan entire directory
  python cli.py scan-dir ./src
  
  # Scan Azure DevOps repository
  python cli.py scan-repo https://dev.azure.com/Vancity/_git/MyRepo --branch master
  
  # List branches in repository
  python cli.py list-branches https://dev.azure.com/Vancity/_git/MyRepo
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Scan file command
    scan_file_parser = subparsers.add_parser('scan-file', help='Scan a single file')
    scan_file_parser.add_argument('file_path', help='Path to file to scan')
    scan_file_parser.add_argument('--json', action='store_true', help='Output as JSON')
    scan_file_parser.add_argument('--html', type=str, metavar='FILE', help='Generate HTML report to FILE')
    
    # Scan directory command
    scan_dir_parser = subparsers.add_parser('scan-dir', help='Scan a directory')
    scan_dir_parser.add_argument('directory', help='Directory to scan')
    scan_dir_parser.add_argument('--recursive', action='store_true', default=True, help='Recursive scan (default)')
    scan_dir_parser.add_argument('--json', action='store_true', help='Output as JSON')
    scan_dir_parser.add_argument('--html', type=str, metavar='FILE', help='Generate HTML report to FILE')
    
    # Scan repository command
    scan_repo_parser = subparsers.add_parser('scan-repo', help='Scan a Git repository')
    scan_repo_parser.add_argument('repo_url', help='Repository URL (GitHub, Azure DevOps, GitLab, etc.)')
    scan_repo_parser.add_argument('--branch', default='main', help='Branch to scan (default: main)')
    scan_repo_parser.add_argument('--token', help='Authentication token for private repos')
    scan_repo_parser.add_argument('--json', action='store_true', help='Output as JSON')
    scan_repo_parser.add_argument('--html', type=str, metavar='FILE', help='Generate HTML report to FILE')
    
    # List branches command
    list_branches_parser = subparsers.add_parser('list-branches', help='List repository branches')
    list_branches_parser.add_argument('repo_url', help='Repository URL')
    list_branches_parser.add_argument('--token', help='Authentication token for private repos')
    
    # Check access command
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
            result = await scan_file_handler(args.file_path)
            
        elif args.command == 'scan-dir':
            result = await scan_directory_handler(args.directory, args.recursive)
            
        elif args.command == 'scan-repo':
            result = await scan_repository_handler(
                args.repo_url,
                branch=args.branch,
                auth_token=args.token
            )
            
        elif args.command == 'list-branches':
            result = await list_repository_branches_handler(args.repo_url, args.token)
            
        elif args.command == 'check-access':
            result = await check_repository_access_handler(args.repo_url, args.token)
        
        # Output result
        if args.command in ['scan-file', 'scan-dir', 'scan-repo']:
            # Generate HTML report if requested
            if hasattr(args, 'html') and args.html:
                findings = result.get('findings', [])
                scan_path = args.file_path if args.command == 'scan-file' else (
                    args.directory if args.command == 'scan-dir' else args.repo_url
                )
                html_result = await generate_html_report_handler(findings, args.html, scan_path)
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
        else:
            # For non-scan commands
            if isinstance(result, dict):
                if 'error' in result:
                    print(f"❌ Error: {result['error']}")
                    return 1
                elif 'message' in result:
                    print(result['message'])
                elif 'branches' in result:
                    print(f"\nFound {len(result['branches'])} branches:")
                    for branch in result['branches']:
                        print(f"  - {branch}")
                else:
                    print(json.dumps(result, indent=2))
            else:
                print(result)
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def cli_main():
    """Entry point for console_scripts."""
    sys.exit(asyncio.run(main()))


if __name__ == '__main__':
    cli_main()
