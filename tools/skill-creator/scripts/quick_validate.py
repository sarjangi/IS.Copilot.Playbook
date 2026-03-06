#!/usr/bin/env python3
"""
Quick validation script for Copilot customization files:
- .prompt.md (prompt files / slash commands)
- .instructions.md (file-based instructions)
- SKILL.md (Agent Skills)
"""

import sys
import os
import re
import yaml
from pathlib import Path


def _find_prompt_files(prompt_path):
    """Find customization files to validate."""
    prompt_path = Path(prompt_path)
    files = []

    if prompt_path.is_file() and (prompt_path.suffix == '.md'):
        files.append(prompt_path)
        return files

    # Check .github/prompts/ (prompt files)
    copilot_dir = prompt_path / '.github' / 'prompts'
    if copilot_dir.is_dir():
        files.extend(copilot_dir.glob('*.prompt.md'))

    # Check .github/instructions/ (instructions files)
    instructions_dir = prompt_path / '.github' / 'instructions'
    if instructions_dir.is_dir():
        files.extend(instructions_dir.glob('*.instructions.md'))

    # Check .github/skills/ (Agent Skills)
    skills_dir = prompt_path / '.github' / 'skills'
    if skills_dir.is_dir():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / 'SKILL.md'
                if skill_md.exists():
                    files.append(skill_md)

    # Check for SKILL.md at root (Agent Skills or legacy)
    skill_md = prompt_path / 'SKILL.md'
    if skill_md.exists():
        files.append(skill_md)

    # Check for .prompt.md files in root
    files.extend(prompt_path.glob('*.prompt.md'))

    return list(set(files))


def validate_prompt_file(file_path):
    """Validate a single customization file.

    Supports .prompt.md, .instructions.md, and SKILL.md formats.
    Checks frontmatter fields, structure, and conventions.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return False, f"File not found: {file_path}"

    content = file_path.read_text()
    if not content.startswith('---'):
        return False, "No YAML frontmatter found"

    # Extract frontmatter
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        if not isinstance(frontmatter, dict):
            return False, "Frontmatter must be a YAML dictionary"
    except yaml.YAMLError as e:
        return False, f"Invalid YAML in frontmatter: {e}"

    # Detect format based on filename
    is_prompt_md = file_path.name.endswith('.prompt.md')
    is_instructions_md = file_path.name.endswith('.instructions.md')
    is_skill_md = file_path.name == 'SKILL.md'

    # Prompt file (.prompt.md) allowed properties
    PROMPT_PROPERTIES = {'description', 'name', 'agent', 'tools', 'model', 'argument-hint'}
    # Instructions file (.instructions.md) allowed properties
    INSTRUCTIONS_PROPERTIES = {'name', 'description', 'applyTo'}
    # Agent Skills (SKILL.md) allowed properties
    SKILL_PROPERTIES = {'name', 'description', 'argument-hint', 'user-invocable', 'disable-model-invocation'}
    ALL_ALLOWED = PROMPT_PROPERTIES | INSTRUCTIONS_PROPERTIES | SKILL_PROPERTIES

    if is_prompt_md:
        allowed = PROMPT_PROPERTIES
        format_label = ".prompt.md"
    elif is_instructions_md:
        allowed = INSTRUCTIONS_PROPERTIES
        format_label = ".instructions.md"
    elif is_skill_md:
        allowed = SKILL_PROPERTIES
        format_label = "SKILL.md"
    else:
        allowed = ALL_ALLOWED
        format_label = "customization file"

    unexpected_keys = set(frontmatter.keys()) - allowed
    if unexpected_keys:
        return False, (
            f"Unexpected key(s) in {format_label} frontmatter: {', '.join(sorted(unexpected_keys))}. "
            f"Allowed properties are: {', '.join(sorted(allowed))}"
        )

    # Validate agent field (prompt files)
    agent_val = frontmatter.get('agent', '')
    if agent_val and is_prompt_md:
        valid_agents = ('agent', 'ask', 'plan')
        if agent_val not in valid_agents and not isinstance(agent_val, str):
            return False, f"Invalid agent '{agent_val}'. Must be 'agent', 'ask', 'plan', or a custom agent name."

    # Validate tools (prompt files)
    tools = frontmatter.get('tools', [])
    if tools and not isinstance(tools, list):
        return False, f"Tools must be a list, got {type(tools).__name__}"

    # Validate description
    description = frontmatter.get('description', '')
    if description:
        if not isinstance(description, str):
            return False, f"Description must be a string, got {type(description).__name__}"
        description = description.strip()
        if len(description) > 1024:
            return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters."

    # Validate applyTo (instructions files)
    apply_to = frontmatter.get('applyTo', '')
    if apply_to:
        if is_prompt_md:
            return False, "applyTo is not valid for .prompt.md files. Use .instructions.md files for file-pattern matching."
        if not isinstance(apply_to, str):
            return False, f"applyTo must be a string, got {type(apply_to).__name__}"

    # Agent Skills (SKILL.md) validations
    if is_skill_md:
        if 'name' not in frontmatter:
            return False, "Missing required 'name' in SKILL.md frontmatter"
        if 'description' not in frontmatter:
            return False, "Missing required 'description' in SKILL.md frontmatter"
        name = frontmatter.get('name', '')
        if name and not isinstance(name, str):
            return False, f"Name must be a string, got {type(name).__name__}"
        name = str(name).strip()
        if name:
            if not re.match(r'^[a-z0-9-]+$', name):
                return False, f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)"
            if name.startswith('-') or name.endswith('-') or '--' in name:
                return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
            if len(name) > 64:
                return False, f"Name is too long ({len(name)} characters). Maximum is 64 characters."

    # Check that the file has content beyond frontmatter
    body = content[match.end():].strip()
    if not body:
        return False, "File has no content beyond frontmatter"

    return True, f"Valid {format_label}!"


def validate_skill(skill_path):
    """Validate a prompt/skill directory.

    Finds and validates all prompt files in the directory.
    Backward-compatible with SKILL.md format.
    """
    skill_path = Path(skill_path)
    files = _find_prompt_files(skill_path)

    if not files:
        return False, "No .prompt.md or SKILL.md files found"

    all_valid = True
    messages = []
    for f in files:
        valid, msg = validate_prompt_file(f)
        if not valid:
            all_valid = False
        messages.append(f"{f.name}: {msg}")

    if all_valid:
        return True, "; ".join(messages) if len(messages) > 1 else messages[0]
    else:
        return False, "; ".join(messages)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <prompt_directory_or_file>")
        sys.exit(1)
    
    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)