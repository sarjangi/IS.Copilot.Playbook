---
name: 'Python Coding Standards'
description: 'Coding conventions and best practices for Python files following PEP 8'
applyTo: '**/*.py'
---

<!-- 
This is a reference template for file-based instructions.
Instructions are automatically applied to files matching the applyTo glob pattern.
Teams can customize this file with Vancity-specific Python standards.
-->

# Python Coding Standards

When working with Python code, follow these conventions:

## Naming Conventions
- Use snake_case for functions, variables, and module names
- Use PascalCase for class names
- Use UPPER_CASE for constants
- Use descriptive names that reveal intent

## Code Organization
- Imports at the top: standard library, third-party, local application
- Group imports and separate groups with blank lines
- One blank line between methods, two blank lines between classes
- Maximum line length: 88 characters (Black formatter default)

## Type Hints
- Use type hints for function parameters and return values
- Use `Optional[Type]` for nullable values
- Use `from typing import` for complex types

## Documentation
- Use docstrings for all public modules, classes, and functions
- Follow Google or NumPy docstring format
- Include parameter descriptions and return value descriptions

## Best Practices
- Use f-strings for string formatting
- Use list/dict comprehensions when they improve readability
- Prefer `pathlib.Path` over `os.path` for file operations
- Use context managers (`with` statements) for resource management
- Follow PEP 8 guidelines

## Example
```python
from typing import Optional
from pathlib import Path

class FileProcessor:
    """Processes files and returns processed content.
    
    Args:
        base_dir: The base directory for file operations.
    """
    
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
    
    def process_file(self, filename: str) -> Optional[str]:
        """Process a single file and return its content.
        
        Args:
            filename: Name of the file to process.
            
        Returns:
            The processed file content, or None if file doesn't exist.
        """
        file_path = self.base_dir / filename
        if not file_path.exists():
            return None
            
        with file_path.open('r', encoding='utf-8') as f:
            return f.read().strip()
```
