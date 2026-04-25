# IS.Copilot.Playbook

A shared playbook of GitHub Copilot **agents**, **instructions**, **prompts**, and **guides** for automating and standardizing engineering tasks at Vancity.

This repository is the single source of truth for reusable AI-assisted workflows across teams, organized by programming language for easy discovery.

---

## 📁 Repository Structure

```
.github/                          # GitHub Copilot customizations
├── copilot-instructions.md       # Always-on workspace instructions
├── agents/                       # Globally deployed autonomous agents
│   └── security-pipeline.agent.md  # Automated security pipeline with per-severity PRs
├── dotnet/                       # .NET / C# specific
│   ├── skills/                   # Complex multi-step agents
│   ├── prompts/                  # Slash commands
│   └── instructions/             # Auto-applied coding standards
├── python/                       # Python specific
│   ├── skills/
│   ├── prompts/
│   └── instructions/
├── javascript/                   # JavaScript / TypeScript specific
│   ├── skills/
│   ├── prompts/
│   └── instructions/
└── shared/                       # Language-agnostic content
    ├── skills/
    ├── prompts/
    └── instructions/

docs/                             # Educational materials
├── guides/                       # Learning tutorials
│   ├── comparison.md             # Understand customization types
│   ├── ai-instructions.md        # Write effective instructions
│   └── agents.md                 # Build autonomous agents
└── images/                       # Diagrams and visualizations

tools/                            # Development utilities
└── skill-creator/                # Tools for building/testing customizations
```

---

## 🚀 Getting Started

### Browse Content by Language

- **[.NET / C#](.github/dotnet/)** - Skills, prompts, and instructions for .NET development
- **[Python](.github/python/)** - Python-specific customizations
- **[JavaScript](.github/javascript/)** - JavaScript/TypeScript customizations
- **[Shared](.github/shared/)** - Language-agnostic customizations

### Test a Prompt or Skill

1. Open **GitHub Copilot Chat** in VS Code
2. Type `/` to see available commands
3. Select a command (e.g., `/dotnet-upgrade`, `/code-review`)
4. Follow the on-screen instructions

### See Instructions in Action

Instructions automatically apply to matching files:
- Open a `.cs` file → C# style instructions activate
- Open a `.py` file → Python style instructions activate
- Ask GitHub Copilot for help, and it follows these guidelines

---

## 📚 Learning Path

New to GitHub Copilot customizations? Follow this progression:

1. **[Understand the Types](docs/guides/comparison.md)** - Learn the difference between prompts, instructions, agents, and skills
2. **[Write Instructions](docs/guides/ai-instructions.md)** - Master the art of writing effective AI instructions
3. **[Build Agents](docs/guides/agents.md)** - Create autonomous multi-step agents with proper orchestration

Complete documentation: [**docs/**](docs/)

---

## 🎯 What's in This Playbook?

| Type | Description | Where to Find | How to Use |
|------|-------------|---------------|------------|
| **Agents** | Autonomous end-to-end pipelines | `.github/agents/*.agent.md` | Select from the agent picker in Copilot Chat |
| **Skills** | Complex multi-step autonomous agents | `.github/<language>/skills/*/SKILL.md` | Type `/skill-name` in Copilot Chat |
| **Prompts** | Simple slash commands for quick tasks | `.github/<language>/prompts/*.prompt.md` | Type `/prompt-name` in Copilot Chat |
| **Instructions** | Auto-applied context for specific file types | `.github/<language>/instructions/*.instructions.md` | Automatically activates when opening matching files |
| **Guides** | Learning materials and best practices | `docs/guides/*.md` | Read for understanding |

---

## 📝 Available Content

### .NET / C#

- **Skills**: [`dotnet-upgrade`](.github/dotnet/skills/dotnet-upgrade/SKILL.md) - Automatic .NET framework upgrades
- **Instructions**: C# coding standards for all `.cs` files

### Python

- **Instructions**: PEP 8 coding standards for all `.py` files

### Shared / Language-Agnostic

- **Skills**: 
  - [`example-skill`](.github/shared/skills/example-skill/SKILL.md) - Template for building new skills
  - [`integration-platform`](.github/shared/skills/integration-platform/SKILL.md) - Unified security and repository analysis tools (SQL scanning plus repo analysis)
- **Agents**:
  - [`security-pipeline`](.github/agents/security-pipeline.agent.md) - End-to-end automated security pipeline: clone → scan → fix → open one PR per severity category (CRITICAL, HIGH, MEDIUM, LOW). Provide only the repo URL — branch defaults to `main`/`master` and PBI# is auto-generated.
- **Prompts**: [`code-review`](.github/shared/prompts/code-review.prompt.md) - Comprehensive code reviews

_More content coming soon as teams contribute!_

---

## ✨ Contributing

Want to add your own agents, prompts, or instructions?

1. **Choose the right folder**: Use `.github/<language>/` for language-specific content, or `.github/shared/` for multi-language content
2. **Follow format requirements**: See [CONTRIBUTING.md](CONTRIBUTING.md) for YAML frontmatter schemas
3. **Validate**: Run `python tools/skill-creator/scripts/quick_validate.py`
4. **Test**: Try it in VS Code with GitHub Copilot
5. **Submit**: Create a pull request

Detailed guide: [**CONTRIBUTING.md**](CONTRIBUTING.md)

---

## 🛠️ Development Tools

### skill-creator Framework

The [`tools/skill-creator/`](tools/skill-creator/) directory contains utilities for building and improving customizations:

- **Validation**: `quick_validate.py` - Check frontmatter and structure
- **Packaging**: `package_skill.py` - Create distributable .skill.zip files
- **Evaluation**: Specialized agents for testing and comparing outputs
- **Reporting**: Generate HTML review pages for iteration feedback

**Documentation**: [tools/skill-creator/SKILL.md](tools/skill-creator/SKILL.md)

### Validation Before Committing

```bash
# Install dependencies
pip install -r requirements.txt

# Validate all customization files
python tools/skill-creator/scripts/quick_validate.py
```

---

## 🔍 How It Works

### Workspace Instructions
[`.github/copilot-instructions.md`](.github/copilot-instructions.md) contains always-on instructions that apply to the entire workspace.

### Language-Specific Instructions
Instructions in `.github/<language>/instructions/*.instructions.md` automatically apply when you open files matching their `applyTo` glob pattern.

### Prompts and Skills
Prompts and skills appear in the `/` command menu in GitHub Copilot Chat. Type `/` followed by the customization name to invoke them.

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | This file - repository overview |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to add content |
| [docs/README.md](docs/README.md) | Learning path guide |
| [docs/guides/comparison.md](docs/guides/comparison.md) | Customization types explained |
| [docs/guides/ai-instructions.md](docs/guides/ai-instructions.md) | Writing instructions guide |
| [docs/guides/agents.md](docs/guides/agents.md) | Building agents guide |
| [tools/skill-creator/SKILL.md](tools/skill-creator/SKILL.md) | Development tools documentation |
| [tools/skill-creator/references/schemas.md](tools/skill-creator/references/schemas.md) | Complete format specifications |

---

## 🏢 About Vancity

This playbook is maintained by the Vancity engineering organization to share knowledge and promote consistency across development teams.

---

## 🔗 Quick Links

- [Browse .NET Customizations](.github/dotnet/)
- [Browse Python Customizations](.github/python/)
- [Browse JavaScript Customizations](.github/javascript/)
- [Browse Shared Customizations](.github/shared/)
- [Learn How to Contribute](CONTRIBUTING.md)
- [Explore Learning Guides](docs/)
- [Development Tools](tools/skill-creator/)

---

**Ready to get started?** Pick a language folder and explore the available customizations!