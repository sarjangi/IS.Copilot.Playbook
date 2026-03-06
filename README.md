# IS.Copilot.Playbook

A shared playbook of GitHub Copilot **agents**, **agent instructions**, **prompts**, and **guides** for automating and standardising engineering tasks at Vancity.

This repository is the single source of truth for reusable AI-assisted workflows across teams.

---

## What's in This Playbook?

| Type | Description | Where to Find |
|---|---|---|
| **Agents** | `.agent.md` files that run autonomously via GitHub Copilot agent mode | `Agents/` folder |
| **Agent Instructions** | Rules and behavior definitions that drive each agent | Inside each `.agent.md` file |
| **Instructions** | Reusable guidelines that shape how the AI responds — format, tone, style, constraints | `Instructions/` folder |
| **Prompts** | Ready-to-use prompts to trigger agents or get consistent AI responses | Listed in each agent's **Usage Notes** section |
| **Guides** | Learning material on AI instructions, prompt engineering, and agent design | Root folder `.md` files |

> **New to this playbook?** Start here:
> 1. Read [`Prompt-Instruction-Agent-Comparison.md`](Prompt-Instruction-Agent-Comparison.md) to understand the difference between a prompt, instruction, agent, and agent instruction.
> 2. Read [`AI-Instructions.md`](AI-Instructions.md) to learn how to write effective instructions.
> 3. Read [`Agents.md`](Agents.md) to understand how agents work and when to use them.
> 4. Open an agent from the `Agents/` folder and follow its **Usage Notes** to run it.

---

## Getting Started

### How to Run an Agent

1. Open the agent file (e.g., `Agents/dotnet-upgrade.agent.md`) in Visual Studio Code.
2. Make sure the agent file is the **active/focused document** in your editor.
3. Open **GitHub Copilot Chat** and switch to **Agent mode**.
4. Type the prompt listed in the agent's **Usage Notes** section to begin.

> Each agent file contains its own usage instructions and the exact prompt to use.

---

## Contribute

### Adding a New Agent
1. Create a new `.agent.md` file under the `Agents/` folder.
2. Add the YAML front-matter (`name`, `description`, `tools`).
3. Add a **Usage Notes** section with the prompt to start and any operator instructions.

### Adding a New Instruction
1. Create a new `.md` file under the `Instructions/` folder.

### Adding a New Guide or Prompt
1. Create a new `.md` file in the root folder.