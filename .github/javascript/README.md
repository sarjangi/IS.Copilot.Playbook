# JavaScript / TypeScript Copilot Customizations

This folder contains GitHub Copilot customizations specific to JavaScript and TypeScript development.

## Available Content

### Skills (Complex Multi-Step Agents)

_No JavaScript-specific skills yet. Check [../shared/skills/](../shared/skills/) for language-agnostic skills._

### Prompts (Slash Commands)

_No JavaScript-specific prompts yet. Check [../shared/prompts/](../shared/prompts/) for language-agnostic prompts._

### Instructions (Auto-Applied Context)

_No JavaScript-specific instructions yet. Consider adding standards for:_
- ESLint configuration preferences
- React/Vue/Angular patterns
- TypeScript conventions
- Node.js best practices

## How to Use

### Using Instructions
Instructions automatically apply when you open matching files:
- Create `.instructions.md` files with `applyTo` patterns like `**/*.js`, `**/*.ts`, `**/*.jsx`, `**/*.tsx`

### Using Prompts
1. Open GitHub Copilot Chat
2. Type `/` to see available commands
3. Select a JavaScript-specific prompt from the menu

### Using Skills
1. Open GitHub Copilot Chat in VS Code
2. Type `/skill-name` to invoke a skill
3. Follow the on-screen instructions

## Adding New Content

To add JavaScript-specific customizations:
- **Add a skill**: Create directory in `skills/<skill-name>/` with `SKILL.md`
- **Add a prompt**: Create `.prompt.md` file in `prompts/`
- **Add instructions**: Create `.instructions.md` file in `instructions/` with `applyTo` pattern

See [../../CONTRIBUTING.md](../../CONTRIBUTING.md) for detailed guidance.

## JavaScript Technologies Covered

This section can include customizations for:
- JavaScript (ES6+)
- TypeScript
- React / Vue / Angular
- Node.js / Express / NestJS
- Jest / Mocha / Vitest
- Webpack / Vite
- npm / yarn / pnpm

---

**Need help?** Check the learning guides in [`docs/guides/`](../../docs/guides/)
