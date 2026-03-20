# SQL Injection Scanner Skill

An autonomous GitHub Copilot skill for detecting SQL injection vulnerabilities across multiple programming languages.

## Overview

This skill provides comprehensive SQL injection vulnerability scanning with:
- **Multi-language support**: Python, JavaScript, TypeScript, C#, Java, PHP, SQL
- **Pattern detection**: 6 regex patterns for unsafe SQL construction
- **Severity assessment**: CRITICAL, HIGH, MEDIUM risk ratings
- **Actionable remediation**: Language-specific safe code examples
- **Automated workflow**: 5-phase autonomous operation

## How to Use

### In GitHub Copilot Chat

1. Open GitHub Copilot Chat in VS Code
2. Type: `/sql-injection-scanner`
3. Provide a file path or directory when prompted
4. Review the generated security report

### Example Usage

```
User: /sql-injection-scanner
Agent: I'll scan your code for SQL injection vulnerabilities. What file or directory should I scan?
User: src/database/
Agent: Scanning 15 Python files... Found 3 vulnerabilities...
```

## What It Detects

### Unsafe Patterns

- **String concatenation**: `execute("SELECT * FROM users WHERE id = " + user_id)`
- **F-strings**: `execute(f"SELECT * FROM {table} WHERE id = {id}")`
- **%-format**: `execute("SELECT * FROM users WHERE name = '%s'" % name)`
- **`.format()`**: `execute("SELECT * FROM {} WHERE id = {}".format(table, id))`
- **Direct variable concatenation**: `query = "SELECT * FROM users WHERE " + condition`
- **str() concatenation**: `execute("SELECT * FROM users WHERE id = " + str(user_input))`

### Safe Patterns (Will Not Flag)

- **Parameterized queries**: `execute("SELECT * FROM users WHERE id = ?", (user_id,))`
- **Named parameters**: `execute("SELECT * FROM users WHERE id = :id", {"id": user_id})`
- **ORM methods**: `User.query.filter(User.id == user_id).first()`

## Report Output

The skill generates detailed reports including:

### Summary Statistics
- Total files scanned
- Total vulnerabilities found
- Severity breakdown (CRITICAL/HIGH/MEDIUM)

### Detailed Findings
For each vulnerability:
- File path and line number
- Vulnerable code snippet
- Severity with icon (🔴/🟠/🟡)
- Security risk explanation
- Concrete fix example
- OWASP CWE-89 reference

### Remediation Guidance
- Priority order for fixes
- Language-specific best practices
- ORM recommendations
- Input validation strategies

## Output Formats

- **text** (default): Full detailed report with explanations
- **summary**: High-level statistics only
- **json**: Machine-readable format for tool integration

## Supported File Types

- `.py` - Python (with optional Bandit integration)
- `.js` - JavaScript
- `.ts` - TypeScript
- `.sql` - SQL files
- `.cs` - C#
- `.java` - Java
- `.php` - PHP

## Behavioral Features

### Automatic Operations
- Recursively scans directories
- Skips excluded directories (`venv`, `node_modules`, `__pycache__`, `.git`)
- Validates findings to reduce false positives
- Provides context-aware risk assessment

### Safety Constraints
- Path validation (rejects `..` directory traversal)
- File size limits (10MB per file)
- Timeout protection (30s per file, 5m total)
- Resource limits (max 10,000 files, 10 levels deep)

### Security Principles
- Read-only operation (never modifies files)
- No query execution or exploitation attempts
- Redacts credentials found in code
- Privacy-conscious reporting

## Best Practices Enforced

1. ✅ **Always use parameterized queries**
2. ✅ **Prefer ORMs over raw SQL**
3. ✅ **Validate all user input**
4. ✅ **Use allow-lists for dynamic identifiers**
5. ✅ **Apply least-privilege database accounts**
6. ❌ **Never trust user input**
7. ❌ **Don't build SQL with string concatenation**

## Testing

### Validate Installation

```bash
# From workspace root
python tools/skill-creator/scripts/quick_validate.py
```

### Test Cases

1. **Single vulnerable file**: Scan a Python file with known SQL injection
2. **Clean code**: Scan a file using only parameterized queries (should report 0 issues)
3. **Mixed directory**: Scan a directory with both vulnerable and safe code
4. **Unsupported files**: Verify non-SQL files are skipped appropriately

## Source Implementation

This skill is based on the AIFCoder security agent implementation:

- **Original Project**: [AIFCoder](https://github.com/sarjangi/AIFCoder)
- **Implementation**: Python agent using `agent-framework-github-copilot`
- **Tools**: 4 security scanning tools (scan_file, scan_directory, check_parameterized, generate_report)
- **Testing**: 15 comprehensive unit tests with 100% detection accuracy

## Limitations

This skill focuses **exclusively on SQL injection vulnerabilities**. It does not detect:
- NoSQL injection
- LDAP injection
- XML injection
- Command injection
- XSS vulnerabilities
- CSRF issues
- Authentication/authorization flaws

For comprehensive security audits, combine with other tools like:
- SonarQube
- Snyk
- Bandit (Python)
- ESLint security plugins
- OWASP ZAP

## When to Use

✅ **Recommended**:
- Pre-deployment security checks
- Code review for database operations
- Security training and education
- Establishing security baseline
- Validating security fixes

❌ **Not Recommended**:
- Replacing comprehensive security audits
- Real-time protection (use WAF)
- Finding all vulnerability types
- Production monitoring

## Contributing

To improve this skill:

1. **Report false positives**: Help refine detection patterns
2. **Add language support**: Contribute patterns for additional languages
3. **Improve remediation**: Suggest better fix examples
4. **Enhance reporting**: Propose new output formats

See [CONTRIBUTING.md](../../../../CONTRIBUTING.md) for guidelines.

## References

- **OWASP Top 10**: A03:2021 - Injection
- **CWE-89**: SQL Injection
- **OWASP SQL Injection Prevention Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- **Bandit Security Tool**: https://bandit.readthedocs.io/

## License

Part of the IS.Copilot.Playbook project. See repository LICENSE file.

---

**Version**: 1.0  
**Created**: March 19, 2026  
**Maintained by**: Vancity Engineering  
**Questions?**: Open an issue in the repository
