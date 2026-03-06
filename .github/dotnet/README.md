# .NET / C# Copilot Customizations

This folder contains GitHub Copilot customizations specific to .NET and C# development.

## Available Content

### Skills (Complex Multi-Step Agents)

| Skill | Description | Usage |
|-------|-------------|-------|
| [dotnet-upgrade](skills/dotnet-upgrade/SKILL.md) | Fully autonomous .NET upgrade agent for in-place framework upgrades | `/dotnet-upgrade` |

### Prompts (Slash Commands)

_No .NET-specific prompts yet. Check [../shared/prompts/](../shared/prompts/) for language-agnostic prompts._

### Instructions (Auto-Applied Context)

| Instruction | Applies To | Description |
|-------------|------------|-------------|
| [csharp-style](instructions/csharp-style.instructions.md) | `**/*.cs` | C# coding standards and best practices |

## How to Use

### Using Skills
1. Open GitHub Copilot Chat in VS Code
2. Type `/dotnet-upgrade` (or the skill name)
3. Follow the on-screen instructions

### Using Instructions
Instructions automatically apply when you open matching files:
- Open any `.cs` file to activate C# style instructions
- Ask GitHub Copilot for help, and it will follow these guidelines

### Using Prompts
1. Open GitHub Copilot Chat
2. Type `/` to see available commands
3. Select a .NET-specific prompt from the menu

## Adding New Content

To add .NET-specific customizations:
- **Add a skill**: Create directory in `skills/<skill-name>/` with `SKI LL.md`
- **Add a prompt**: Create `.prompt.md` file in `prompts/`
- **Add instructions**: Create `.instructions.md` file in `instructions/` with `applyTo` pattern

See [../../CONTRIBUTING.md](../../CONTRIBUTING.md) for detailed guidance.

## .NET Technologies Covered

This section includes customizations for:
- C# (all versions)
- .NET Framework, .NET Core, .NET 5+
- ASP.NET Core
- Entity Framework Core
- Xamarin / MAUI
- Blazor

---

**Need help?** Check the learning guides in [`docs/guides/`](../../docs/guides/)
