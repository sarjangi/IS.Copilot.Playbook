"""Shared utilities for prompt-creator scripts.

Supports GitHub Copilot customization files:
- .prompt.md (prompt files / slash commands)
- .instructions.md (file-based instructions)
- SKILL.md (Agent Skills)
"""

from pathlib import Path


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from a markdown file.

    Returns (frontmatter_dict, full_content).
    Only handles the simple key: value fields we care about.
    """
    lines = content.split("\n")

    if lines[0].strip() != "---":
        raise ValueError("File missing frontmatter (no opening ---)")

    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        raise ValueError("File missing frontmatter (no closing ---)")

    frontmatter: dict = {}
    frontmatter_lines = lines[1:end_idx]
    i = 0
    while i < len(frontmatter_lines):
        line = frontmatter_lines[i]
        if ":" in line:
            key = line.split(":", 1)[0].strip()
            value = line.split(":", 1)[1].strip()
            # Handle YAML multiline indicators (>, |, >-, |-)
            if value in (">", "|", ">-", "|-"):
                continuation_lines: list[str] = []
                i += 1
                while i < len(frontmatter_lines) and (frontmatter_lines[i].startswith("  ") or frontmatter_lines[i].startswith("\t")):
                    continuation_lines.append(frontmatter_lines[i].strip())
                    i += 1
                frontmatter[key] = " ".join(continuation_lines)
                continue
            else:
                frontmatter[key] = value.strip('"').strip("'")
        i += 1

    return frontmatter, content


def find_prompt_file(prompt_path: Path) -> Path:
    """Find the main customization file in a directory.

    Searches for (in order):
    1. .prompt.md files in .github/prompts/ (prompt files)
    2. SKILL.md in .github/skills/*/ (Agent Skills)
    3. SKILL.md at root (Agent Skills or legacy)
    4. Any .prompt.md file in the directory

    Returns the path to the customization file.
    """
    # Direct file path
    if prompt_path.is_file():
        return prompt_path

    # Check for .github/prompts/ directory (prompt files)
    copilot_prompts = prompt_path / ".github" / "prompts"
    if copilot_prompts.is_dir():
        prompt_files = list(copilot_prompts.glob("*.prompt.md"))
        if prompt_files:
            return prompt_files[0]

    # Check for .github/skills/ directory (Agent Skills)
    skills_dir = prompt_path / ".github" / "skills"
    if skills_dir.is_dir():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    return skill_md

    # Check for SKILL.md at root (Agent Skills or legacy format)
    skill_md = prompt_path / "SKILL.md"
    if skill_md.exists():
        return skill_md

    # Check for any .prompt.md in the directory
    prompt_files = list(prompt_path.glob("*.prompt.md"))
    if prompt_files:
        return prompt_files[0]

    raise FileNotFoundError(
        f"No .prompt.md or SKILL.md found in {prompt_path}. "
        f"Expected .github/prompts/*.prompt.md, .github/skills/*/SKILL.md, or SKILL.md"
    )


def parse_prompt_md(prompt_path: Path) -> tuple[str, str, str]:
    """Parse a .prompt.md, .instructions.md, or SKILL.md file.

    Returns (name, description, full_content).

    Handles all GitHub Copilot customization formats:
    - .prompt.md: name from 'name' field or filename, description from frontmatter
    - .instructions.md: name from 'name' field or filename
    - SKILL.md: name and description from frontmatter (required for Agent Skills)
    """
    prompt_file = find_prompt_file(prompt_path)
    content = prompt_file.read_text()
    frontmatter, _ = _parse_frontmatter(content)

    # Get name: from frontmatter 'name' field, or derive from filename
    name = frontmatter.get("name", "")
    if not name:
        # Derive from filename: my-prompt.prompt.md -> my-prompt
        stem = prompt_file.stem
        if stem.endswith(".prompt"):
            stem = stem[: -len(".prompt")]
        elif stem.endswith(".instructions"):
            stem = stem[: -len(".instructions")]
        name = stem

    description = frontmatter.get("description", "")

    return name, description, content


# Backward compatibility alias
def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:
    """Parse a SKILL.md file, returning (name, description, full_content).

    Backward-compatible wrapper around parse_prompt_md.
    """
    return parse_prompt_md(skill_path)
