# Contributing to IS.Copilot.Playbook

Thank you for contributing to Vancity's shared GitHub Copilot playbook! This guide will help you add new agents, prompts, and instructions.

---

## Table of Contents
- [Getting Started](#getting-started)
- [Adding New Content](#adding-new-content)
- [File Format Requirements](#file-format-requirements)
- [Testing Your Content](#testing-your-content)
- [Language Organization](#language-organization)
- [Using skill-creator Tools](#using-skill-creator-tools)
- [Validation](#validation)

---

## Getting Started

### Prerequisites
- Visual Studio Code with GitHub Copilot extension
- Python 3.8+ (for validation tools)
- Git for version control

### Setup
1. Clone the repository
2. Install Python dependencies: `pip install -r requirements.txt`
3. Open workspace in VS Code with GitHub Copilot enabled

---

## Adding New Content

### Adding a Prompt (Slash Command)

Prompts are simple slash commands that appear in the `/` menu of GitHub Copilot Chat.

**Steps:**
1. Choose the appropriate language folder or use `shared/` for language-agnostic prompts
2. Create a new `.prompt.md` file in `.github/<language>/prompts/`
3. Add YAML frontmatter (see format below)
4. Write the prompt instructions
5. Test by typing `/promptName` in GitHub Copilot Chat

**Example location:**
- .NET specific: `.github/dotnet/prompts/my-prompt.prompt.md`
- Python specific: `.github/python/prompts/my-prompt.prompt.md`
- Language-agnostic: `.github/shared/prompts/my-prompt.prompt.md`

### Adding an Instruction (Auto-Applied Context)

Instructions automatically apply to files matching a glob pattern.

**Steps:**
1. Choose the appropriate language folder
2. Create a new `.instructions.md` file in `.github/<language>/instructions/`
3. Add YAML frontmatter with `applyTo` glob pattern
4. Write the instruction content
5. Test by opening a file that matches the pattern

**Example location:**
- C# standards: `.github/dotnet/instructions/csharp-style.instructions.md`
- Python standards: `.github/python/instructions/python-style.instructions.md`

### Adding an Agent Skill (Complex Multi-Step Agent)

Agent Skills are sophisticated autonomous agents with multiple phases.

**Steps:**
1. Choose the appropriate language folder
2. Create a directory: `.github/<language>/skills/<skill-name>/`
3. Create `SKILL.md` inside the directory
4. Add YAML frontmatter (name must match directory name)
5. Organize content into phases with clear workflow
6. Include usage notes for human operators
7. Test by typing `/skill-name` in GitHub Copilot Chat

**Example location:**
- .NET skill: `.github/dotnet/skills/dotnet-upgrade/SKILL.md`
- Python skill: `.github/python/skills/python-linting/SKILL.md`

---

## File Format Requirements

### Prompt File Frontmatter (`.prompt.md`)

```yaml
---
description: Brief description shown in / menu (max 1024 chars)
agent: agent      # Options: agent, ask, plan, or custom agent name
tools:            # Optional: tools available
  - codebase
  - terminal
  - github
model: claude-sonnet  # Optional: model override
argument-hint: 'Enter file path'  # Optional: hint text
---
```

### Instructions File Frontmatter (`.instructions.md`)

```yaml
---
name: 'Display Name'
description: 'Short description for hover text'
applyTo: '**/*.py'  # Glob pattern for file matching
---
```

### Agent Skill Frontmatter (`SKILL.md`)

```yaml
---
name: skill-name  # Required, must match directory name, kebab-case
description: 'What the skill does (max 1024 chars)'  # Required
argument-hint: 'hint text'  # Optional
user-invocable: true  # Optional, default true
---
```

**Complete format documentation:** See [`tools/skill-creator/references/schemas.md`](tools/skill-creator/references/schemas.md)

---

## Testing Your Content

### Manual Testing in VS Code

1. **Test Prompts:**
   - Open GitHub Copilot Chat
   - Type `/` to see the command menu
   - Find your prompt name and select it
   - Verify it behaves as expected

2. **Test Instructions:**
   - Open a file matching the `applyTo` pattern
   - Ask GitHub Copilot to perform a task
   - Verify the instructions are being followed

3. **Test Agent Skills:**
   - Type `/skill-name` in GitHub Copilot Chat
   - Follow the usage notes in the SKILL.md
   - Observe the multi-phase workflow

### Validation Script

Run validation before committing:

```bash
python tools/skill-creator/scripts/quick_validate.py
```

This checks:
- YAML frontmatter syntax
- Required fields presence
- Naming conventions
- Directory structure compliance

---

## Language Organization

Choose the right folder for your content:

| Folder | Use For |
|--------|---------|
| `.github/dotnet/` | C#, F#, .NET-specific content |
| `.github/python/` | Python-specific content |
| `.github/javascript/` | JavaScript, TypeScript, Node.js content |
| `.github/shared/` | Language-agnostic content that works across all languages |

**When in doubt:** Use `shared/` if the content applies to multiple languages.

---

## Using skill-creator Tools

The `tools/skill-creator/` directory contains utilities for building and evaluating customizations.

### Available Tools

1. **quick_validate.py** - Validate frontmatter and structure
   ```bash
   python tools/skill-creator/scripts/quick_validate.py
   ```

2. **aggregate_benchmark.py** - Aggregate test results into statistics
   ```bash
   python tools/skill-creator/scripts/aggregate_benchmark.py <directory>
   ```

3. **generate_report.py** - Generate HTML review pages
   ```bash
   python tools/skill-creator/scripts/generate_report.py <loop-output-dir>
   ```

4. **package_skill.py** - Create distributable .skill.zip files
   ```bash
   python tools/skill-creator/scripts/package_skill.py <skill-directory>
   ```

### Evaluation Agents

Use the specialized evaluation agents in `tools/skill-creator/agents/`:

- **grader.md** - Evaluate outputs against expectations
- **comparator.md** - Blind A/B comparison of two outputs
- **analyzer.md** - Post-hoc analysis of results

See [`tools/skill-creator/SKILL.md`](tools/skill-creator/SKILL.md) for detailed workflow.

---

## Validation

### Before Committing

1. Run validation script:
   ```bash
   python tools/skill-creator/scripts/quick_validate.py
   ```

2. Test your content manually in VS Code

3. Verify files are in correct language folders

4. Check that YAML frontmatter is properly formatted

### Common Issues

**Issue:** Prompt doesn't appear in `/` menu  
**Solution:** Check `description` field exists in frontmatter, restart VS Code

**Issue:** Instruction not applying to files  
**Solution:** Verify `applyTo` glob pattern matches your target files

**Issue:** Skill name mismatch error  
**Solution:** Ensure frontmatter `name` matches directory name exactly

**Issue:** YAML syntax error  
**Solution:** Check for proper indentation, quotes, and colons

---

## Questions or Issues?

- Review the learning guides in [`docs/guides/`](docs/guides/)
- Check [`tools/skill-creator/references/schemas.md`](tools/skill-creator/references/schemas.md) for format details
- Consult with the Vancity AI Engineering team

---

Thank you for helping build a comprehensive GitHub Copilot playbook for Vancity teams!
