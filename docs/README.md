# Learning Guides

Welcome to the IS.Copilot.Playbook learning materials! This directory contains comprehensive guides for understanding and building GitHub Copilot customizations.

---

## 📚 Recommended Learning Path

Follow this progression to master GitHub Copilot customizations:

### 1. Start Here: [Comparison Guide](guides/comparison.md)
**What you'll learn:** Understand the differences between prompts, instructions, agents, and agent skills.

**Why read this:** Before creating customizations, you need to know which type fits your use case.

**Time:** 5-10 minutes

---

### 2. Next: [AI Instructions Guide](guides/ai-instructions.md)
**What you'll learn:** How to write clear, effective instructions that guide AI behavior.

**Why read this:** All customizations rely on well-written instructions. Master this foundational skill first.

**Key topics:**
- Instruction structure and patterns
- What makes instructions effective
- Common mistakes to avoid
- Best practices

**Time:** 15-20 minutes

---

### 3. Advanced: [Agents Guide](guides/agents.md)
**What you'll learn:** How to build autonomous multi-step agents with proper orchestration patterns.

**Why read this:** For complex workflows that require decision-making, tool usage, and multi-phase execution.

**Key topics:**
- What is an agent vs a simple prompt
- Single-agent vs multi-agent systems
- Manager and decentralized orchestration patterns
- Guardrails and safety
- Human intervention strategies

**Time:** 25-30 minutes

---

## 🎯 Quick Reference: When to Use What

| Customization Type | Use When | Example |
|-------------------|----------|---------|
| **Prompt** (`.prompt.md`) | You want a simple slash command for a focused task | `/code-review` - Run a quick code review |
| **Instruction** (`.instructions.md`) | You want context automatically applied to specific files | Auto-apply Python PEP 8 standards to `.py` files |
| **Agent Skill** (`SKILL.md`) | You need a multi-step autonomous workflow with tools | `/dotnet-upgrade` - Perform full framework upgrade |

---

## 📖 Guide Details

### [Comparison: Prompts vs Instructions vs Agents](guides/comparison.md)
Explains the four main types of GitHub Copilot customizations:
- Prompts (user-triggered)
- Instructions (auto-applied context)
- Agents (autonomous decision-makers)
- Agent Instructions (rules that govern agent behavior)

**Best for:** Newcomers deciding which customization type to create

---

### [Writing Effective AI Instructions](guides/ai-instructions.md)
Complete tutorial on crafting instructions that produce consistent, high-quality AI responses.

**Covers:**
- Essential components of good instructions
- Structural patterns (persona, task, context, constraints, examples)
- Progressive disclosure techniques
- Versioning and iteration strategies

**Best for:** Anyone creating prompts, instructions, or agent skills

---

### [Building Autonomous Agents](guides/agents.md)
Comprehensive guide to agent design, from simple workflows to complex multi-agent orchestration.

**Covers:**
- Agent foundations (models, tools, instructions)
- When to use single-agent vs multi-agent patterns
- Manager pattern for centralized control
- Decentralized pattern for handoffs
- Guardrails and safety layers
- Human-in-the-loop strategies

**Best for:** Developers building complex multi-step agents

---

## 💡 Practical Application

After reading the guides, put your knowledge into practice:

1. **Explore Examples**
   - Browse [`.github/shared/prompts/`](../.github/shared/prompts/) for prompt examples
   - Review [`.github/dotnet/skills/dotnet-upgrade/`](../.github/dotnet/skills/dotnet-upgrade/) for a real agent skill
   - Examine [`.github/python/instructions/`](../.github/python/instructions/) for instruction examples

2. **Create Your Own**
   - Follow the [CONTRIBUTING.md](../CONTRIBUTING.md) guide
   - Use [`.github/shared/skills/example-skill/`](../.github/shared/skills/example-skill/) as a template
   - Validate with `python tools/skill-creator/scripts/quick_validate.py`

3. **Test and Iterate**
   - Test in VS Code with GitHub Copilot
   - Use skill-creator evaluation agents for improvement
   - Share with your team for feedback

---

## 🔧 Advanced Topics

### For Tool Builders

If you want to build or evaluate customizations systematically:

- **[skill-creator Documentation](../tools/skill-creator/SKILL.md)** - Development framework for creating and testing customizations
- **[Schema Reference](../tools/skill-creator/references/schemas.md)** - Complete YAML frontmatter specifications
- **Evaluation Agents** - Use grader, comparator, and analyzer agents for rigorous testing

---

## 📊 Visual Aids

The guides include diagrams to illustrate key concepts:

![Single Agent Systems](images/SingleAgentSystems.png)
*Simple agent loop: decide → act → observe*

![Manager Pattern](images/ManagerPattern.png)
*Centralized multi-agent orchestration*

![Decentralized Pattern](images/DecentralizedPattern.png)
*Peer-to-peer agent handoffs*

![Guardrails](images/SafeResponses.png)
*Layered safety controls*

---

## 🆘 Need Help?

- **Confused about which customization type to use?** Read [comparison.md](guides/comparison.md)
- **Struggling to write clear instructions?** Study [ai-instructions.md](guides/ai-instructions.md)
- **Building a complex agent?** Follow [agents.md](guides/agents.md)
- **Want to contribute?** See [../CONTRIBUTING.md](../CONTRIBUTING.md)
- **Technical format questions?** Check [../tools/skill-creator/references/schemas.md](../tools/skill-creator/references/schemas.md)

---

## 🗺️ Navigation

- [← Back to Main README](../README.md)
- [Browse .NET Customizations](../.github/dotnet/)
- [Browse Python Customizations](../.github/python/)
- [Browse Shared Customizations](../.github/shared/)
- [Development Tools](../tools/skill-creator/)

---

**Happy learning!** Start with the comparison guide and work your way through the learning path.
