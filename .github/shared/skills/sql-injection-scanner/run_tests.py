#!/usr/bin/env python3
"""
SQL Injection Scanner - Automated Test Runner

Runs all test scenarios from evals.json and validates expected behavior.
Produces detailed pass/fail reports with test coverage metrics.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --verbose          # Show detailed output
    python run_tests.py --test-id 1        # Run specific test
    python run_tests.py --report report.html  # Generate HTML report
"""

import asyncio
import json
import os
import sys
from typing import Dict, List, Any, Tuple
from datetime import datetime
from pathlib import Path

# Import the scanner tools
sys.path.insert(0, str(Path(__file__).parent / "tools"))
from securityTool import scan_file_handler, scan_directory_handler


# ============================================================================
# Test Execution
# ============================================================================

async def run_test_case(test: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    """Execute a single test case and return results."""
    test_id = test.get('id')
    files = test.get('files', [])
    expectations = test.get('expectations', [])
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Test #{test_id}: {test.get('prompt')}")
        print(f"{'='*60}")
    
    results = []
    total_findings = 0
    
    for file_path in files:
        # Resolve relative path
        test_file = Path(__file__).parent / file_path
        
        if not test_file.exists():
            return {
                "test_id": test_id,
                "status": "ERROR",
                "error": f"Test file not found: {test_file}",
                "findings": []
            }
        
        # Determine if it's a file or directory
        if test_file.is_dir():
            result = await scan_directory_handler(str(test_file), recursive=True)
        else:
            result = await scan_file_handler(str(test_file))
        
        if not result.get('success'):
            return {
                "test_id": test_id,
                "status": "ERROR",
                "error": result.get('error', 'Unknown error'),
                "findings": []
            }
        
        findings = result.get('findings', [])
        results.append(result)
        total_findings += len(findings)
        
        if verbose:
            print(f"\nFile: {file_path}")
            print(f"Findings: {len(findings)}")
            for finding in findings:
                print(f"  - Line {finding.get('line')}: {finding.get('issue')} [{finding.get('severity')}]")
    
    return {
        "test_id": test_id,
        "prompt": test.get('prompt'),
        "status": "PASS",  # Will be validated later
        "files_tested": files,
        "total_findings": total_findings,
        "expectations": expectations,
        "results": results
    }


def validate_test_result(test: Dict[str, Any], result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate test results against expectations.
    Returns (passed, validation_messages)
    """
    test_id = result.get('test_id')
    expectations = result.get('expectations', [])
    findings = []
    for r in result.get('results', []):
        findings.extend(r.get('findings', []))
    
    validation_messages = []
    passed = True
    
    # Special handling for specific test scenarios
    if test_id == 1:  # Python vulnerable - should find issues
        if result['total_findings'] < 1:
            passed = False
            validation_messages.append("❌ Expected to find vulnerabilities in python_vulnerable.py")
        else:
            validation_messages.append(f"✅ Found {result['total_findings']} vulnerabilities")
        
        # Check for string concatenation detection
        if any('concatenat' in f.get('issue', '').lower() for f in findings):
            validation_messages.append("✅ Detected string concatenation")
        else:
            passed = False
            validation_messages.append("❌ Failed to detect string concatenation")
    
    elif test_id == 2:  # JavaScript vulnerable
        if result['total_findings'] < 1:
            passed = False
            validation_messages.append("❌ Expected to find vulnerabilities in javascript_vulnerable.js")
        else:
            validation_messages.append(f"✅ Found {result['total_findings']} vulnerabilities")
    
    elif test_id == 3:  # C# vulnerable
        if result['total_findings'] < 1:
            passed = False
            validation_messages.append("❌ Expected to find vulnerabilities in csharp_vulnerable.cs")
        else:
            validation_messages.append(f"✅ Found {result['total_findings']} vulnerabilities")
    
    elif test_id == 4:  # Directory scan
        if result['total_findings'] < 1:
            passed = False
            validation_messages.append("❌ Expected to find vulnerabilities in directory scan")
        else:
            validation_messages.append(f"✅ Found {result['total_findings']} total vulnerabilities")
        
        # Should scan multiple file types
        file_extensions = set()
        for r in result.get('results', []):
            for f in r.get('findings', []):
                ext = Path(f.get('file', '')).suffix
                file_extensions.add(ext)
        
        if len(file_extensions) > 1:
            validation_messages.append(f"✅ Scanned multiple file types: {', '.join(file_extensions)}")
        else:
            validation_messages.append(f"⚠️  Only scanned {len(file_extensions)} file type(s)")
    
    elif test_id == 5:  # Safe Python - should find no issues
        if result['total_findings'] == 0:
            validation_messages.append("✅ Correctly identified safe code (0 vulnerabilities)")
        else:
            passed = False
            validation_messages.append(f"❌ False positive: found {result['total_findings']} issues in safe code")
    
    return passed, validation_messages


# ============================================================================
# Reporting
# ============================================================================

def print_summary(test_results: List[Dict[str, Any]], elapsed_time: float):
    """Print test summary to console."""
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r.get('status') == 'PASS')
    failed_tests = sum(1 for r in test_results if r.get('status') == 'FAIL')
    error_tests = sum(1 for r in test_results if r.get('status') == 'ERROR')
    
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total Tests:   {total_tests}")
    print(f"✅ Passed:     {passed_tests}")
    print(f"❌ Failed:     {failed_tests}")
    print(f"⚠️  Errors:     {error_tests}")
    print(f"Success Rate:  {(passed_tests/total_tests*100):.1f}%")
    print(f"Duration:      {elapsed_time:.2f}s")
    print(f"{'='*60}\n")
    
    # Show failed tests
    if failed_tests > 0:
        print("FAILED TESTS:")
        for result in test_results:
            if result.get('status') == 'FAIL':
                print(f"  ❌ Test #{result.get('test_id')}: {result.get('prompt')}")
                for msg in result.get('validation_messages', []):
                    print(f"      {msg}")
        print()


def generate_html_report(test_results: List[Dict[str, Any]], output_file: str, elapsed_time: float):
    """Generate HTML test report."""
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r.get('status') == 'PASS')
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SQL Injection Scanner - Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #007acc; padding-bottom: 10px; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
        .metric {{ background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; }}
        .metric-value {{ font-size: 32px; font-weight: bold; color: #007acc; }}
        .metric-label {{ font-size: 14px; color: #666; margin-top: 5px; }}
        .test-case {{ border: 1px solid #ddd; margin: 20px 0; padding: 20px; border-radius: 6px; }}
        .test-case.pass {{ border-left: 4px solid #28a745; background: #f8fff9; }}
        .test-case.fail {{ border-left: 4px solid #dc3545; background: #fff8f8; }}
        .test-case.error {{ border-left: 4px solid #ffc107; background: #fffef8; }}
        .status {{ display: inline-block; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
        .status.pass {{ background: #28a745; color: white; }}
        .status.fail {{ background: #dc3545; color: white; }}
        .status.error {{ background: #ffc107; color: black; }}
        .findings {{ margin-top: 10px; }}
        .finding {{ background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 4px; font-family: monospace; font-size: 12px; }}
        .timestamp {{ color: #666; font-size: 12px; }}
        ul {{ margin: 10px 0; padding-left: 20px; }}
        li {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 SQL Injection Scanner - Test Report</h1>
        <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary">
            <div class="metric">
                <div class="metric-value">{total_tests}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric">
                <div class="metric-value" style="color: #28a745;">{passed_tests}</div>
                <div class="metric-label">Passed</div>
            </div>
            <div class="metric">
                <div class="metric-value" style="color: #007acc;">{(passed_tests/total_tests*100):.1f}%</div>
                <div class="metric-label">Success Rate</div>
            </div>
            <div class="metric">
                <div class="metric-value">{elapsed_time:.2f}s</div>
                <div class="metric-label">Duration</div>
            </div>
        </div>
        
        <h2>Test Results</h2>
"""
    
    for result in test_results:
        status = result.get('status', 'UNKNOWN').lower()
        test_id = result.get('test_id')
        prompt = result.get('prompt', '')
        files = result.get('files_tested', [])
        total_findings = result.get('total_findings', 0)
        messages = result.get('validation_messages', [])
        
        html += f"""
        <div class="test-case {status}">
            <h3>Test #{test_id}: {prompt} <span class="status {status}">{status.upper()}</span></h3>
            <p><strong>Files tested:</strong> {', '.join(files)}</p>
            <p><strong>Findings:</strong> {total_findings}</p>
            
            <h4>Validation Results:</h4>
            <ul>
"""
        for msg in messages:
            html += f"                <li>{msg}</li>\n"
        
        html += """            </ul>
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML report generated: {output_file}")


# ============================================================================
# Main
# ============================================================================

async def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description='SQL Injection Scanner - Test Runner')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    parser.add_argument('--test-id', type=int, help='Run specific test by ID')
    parser.add_argument('--report', type=str, help='Generate HTML report (specify output file)')
    args = parser.parse_args()
    
    # Load test cases
    evals_file = Path(__file__).parent / 'evals' / 'evals.json'
    if not evals_file.exists():
        print(f"❌ Error: evals.json not found at {evals_file}")
        sys.exit(1)
    
    with open(evals_file, 'r', encoding='utf-8') as f:
        evals_data = json.load(f)
    
    test_cases = evals_data.get('evals', [])
    
    # Filter by test ID if specified
    if args.test_id:
        test_cases = [t for t in test_cases if t.get('id') == args.test_id]
        if not test_cases:
            print(f"❌ Error: Test ID {args.test_id} not found")
            sys.exit(1)
    
    print(f"🔒 SQL Injection Scanner - Test Runner")
    print(f"Running {len(test_cases)} test(s)...\n")
    
    start_time = datetime.now()
    
    # Run tests
    test_results = []
    for test in test_cases:
        result = await run_test_case(test, verbose=args.verbose)
        
        # Validate results
        passed, validation_messages = validate_test_result(test, result)
        result['status'] = 'PASS' if passed else 'FAIL'
        result['validation_messages'] = validation_messages
        
        test_results.append(result)
        
        # Print immediate feedback
        status_icon = "✅" if passed else "❌"
        print(f"{status_icon} Test #{result['test_id']}: {result['status']}")
    
    elapsed_time = (datetime.now() - start_time).total_seconds()
    
    # Print summary
    print_summary(test_results, elapsed_time)
    
    # Generate HTML report if requested
    if args.report:
        generate_html_report(test_results, args.report, elapsed_time)
    
    # Exit with appropriate code
    failed_count = sum(1 for r in test_results if r.get('status') != 'PASS')
    sys.exit(0 if failed_count == 0 else 1)


if __name__ == '__main__':
    asyncio.run(main())
