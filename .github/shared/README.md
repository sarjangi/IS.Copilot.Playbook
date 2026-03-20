# Shared / Language-Agnostic Copilot Customizations

This folder contains GitHub Copilot customizations that work across all programming languages.

## Available Content

### Skills (Complex Multi-Step Agents)

| Skill | Description | Usage |
|-------|-------------|-------|
| [example-skill](skills/example-skill/SKILL.md) | Template showing proper multi-step agent structure | `/example-skill` |
| [sql-injection-scanner](skills/sql-injection-scanner/SKILL.md) | Autonomous SQL injection vulnerability scanner for Python, JavaScript, TypeScript, C#, Java, PHP, and SQL files | `/sql-injection-scanner` |

### Prompts (Slash Commands)

| Prompt | Description | Usage |
|--------|-------------|-------|
| [code-review](prompts/code-review.prompt.md) | Comprehensive code review with security, performance, and maintainability analysis | `/code-review` |

### Instructions (Auto-Applied Context)

_No shared instructions yet. Shared instructions could include:_
- General coding principles
- Documentation standards
- Git commit message guidelines
- Security review checklist

## How to Use

### Using Skills
1. Open GitHub Copilot Chat in VS Code
2. Type `/example-skill` (or another skill name)
3. Follow the on-screen instructions
4. The agent will work across any language/framework

### Using Prompts
1. Open GitHub Copilot Chat
2. Type `/` to see available commands
3. Select a prompt like `/code-review`
4. Works with any codebase regardless of language

### Using Instructions
Instructions automatically apply when you open matching files:
- Shared instructions can use broad patterns like `**/*` to apply everywhere
- Or use multiple patterns to cover various file types

## Adding New Content

To add language-agnostic customizations:
- **Add a skill**: Create directory in `skills/<skill-name>/` with `SKILL.md`
- **Add a prompt**: Create `.prompt.md` file in `prompts/`
- **Add instructions**: Create `.instructions.md` file in `instructions/` with `applyTo` pattern

See [../../CONTRIBUTING.md](../../CONTRIBUTING.md) for detailed guidance.

## When to Use Shared vs Language-Specific

Use `shared/` when:
- The customization applies to multiple languages
- The logic is language-agnostic (e.g., code review, documentation)
- You want maximum reusability across projects

Use language-specific folders when:
- The customization requires language-specific knowledge
- Instructions reference specific syntax or frameworks
- You want automatic application via `applyTo` patterns

---

**Need help?** Check the learning guides in [`docs/guides/`](../../docs/guides/)
