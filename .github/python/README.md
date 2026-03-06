# Python Copilot Customizations

This folder contains GitHub Copilot customizations specific to Python development.

## Available Content

### Skills (Complex Multi-Step Agents)

_No Python-specific skills yet. Check [../shared/skills/](../shared/skills/) for language-agnostic skills._

### Prompts (Slash Commands)

_No Python-specific prompts yet. Check [../shared/prompts/](../shared/prompts/) for language-agnostic prompts._

### Instructions (Auto-Applied Context)

| Instruction | Applies To | Description |
|-------------|------------|-------------|
| [python-style](instructions/python-style.instructions.md) | `**/*.py` | Python coding standards following PEP 8 |

## How to Use

### Using Instructions
Instructions automatically apply when you open matching files:
- Open any `.py` file to activate Python style instructions
- Ask GitHub Copilot for help, and it will follow PEP 8 and best practices

### Using Prompts
1. Open GitHub Copilot Chat
2. Type `/` to see available commands
3. Select a Python-specific prompt from the menu

### Using Skills
1. Open GitHub Copilot Chat in VS Code
2. Type `/skill-name` to invoke a skill
3. Follow the on-screen instructions

## Adding New Content

To add Python-specific customizations:
- **Add a skill**: Create directory in `skills/<skill-name>/` with `SKILL.md`
- **Add a prompt**: Create `.prompt.md` file in `prompts/`
- **Add instructions**: Create `.instructions.md` file in `instructions/` with `applyTo` pattern

See [../../CONTRIBUTING.md](../../CONTRIBUTING.md) for detailed guidance.

## Python Technologies Covered

This section includes customizations for:
- Python 3.8+
- Django / Flask / FastAPI
- pytest / unittest
- pandas / numpy
- async/await patterns
- Type hints and mypy

---

**Need help?** Check the learning guides in [`docs/guides/`](../../docs/guides/)
