# SQL Injection Examples

This directory contains example code demonstrating both **vulnerable** and **safe** SQL injection patterns across multiple languages.

## ⚠️ WARNING

The code in `vulnerable/` is intentionally insecure for educational purposes only.  
**NEVER use these patterns in production code!**

## Directory Structure

```
examples/
├── vulnerable/       # UNSAFE code examples (for learning)
│   ├── python_concatenation.py
│   ├── javascript_template_literal.js
│   ├── csharp_string_interpolation.cs
│   ├── java_statement.java
│   └── php_interpolation.php
│
└── safe/            # SECURE code examples (use these!)
    ├── python_parameterized.py
    ├── javascript_parameterized.js
    ├── csharp_parameters.cs
    ├── java_prepared_statement.java
    └── php_pdo.php
```

## Learning Path

1. **Study vulnerable examples** - Understand what NOT to do
2. **Review safe examples** - Learn proper techniques
3. **Compare side-by-side** - See the differences
4. **Apply to your code** - Use safe patterns everywhere

## Quick Reference

| Language | Vulnerable Pattern | Safe Pattern |
|----------|-------------------|--------------|
| Python | `"SELECT * WHERE id = " + user_id` | `"SELECT * WHERE id = ?"` with params |
| JavaScript | `` `SELECT * WHERE id = ${userId}` `` | `"SELECT * WHERE id = ?"` with array |
| C# | `$"SELECT * WHERE id = {userId}"` | `@"SELECT * WHERE id = @id"` with SqlParameter |
| Java | `"SELECT * WHERE id = " + userId` | `"SELECT * WHERE id = ?"` with PreparedStatement |
| PHP | `"SELECT * WHERE id = $userId"` | `"SELECT * WHERE id = ?"` with PDO |

## Testing These Examples

You can use the SQL injection scanner to test these files:

```bash
# Scan vulnerable examples (should find issues)
python cli.py scan-dir examples/vulnerable/

# Scan safe examples (should find no issues)
python cli.py scan-dir examples/safe/
```
