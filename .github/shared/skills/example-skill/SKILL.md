---
name: example-skill
description: 'Example multi-step agent skill showing proper structure and workflow organization'
---

<!-- 
This is a reference template for Agent Skills.
Agent Skills are complex, multi-step autonomous agents.
Skills must be in their own directory: .github/skills/<skill-name>/SKILL.md
Teams can use this as a starting point for building custom skills.
-->

# Example Multi-Step Agent Skill

You are a multi-step agent demonstrating proper skill structure. This example shows how to:
- Organize workflows into clear phases
- Use tools effectively
- Provide usage guidance
- Handle edge cases

---

## Usage Notes (Human Operator)

> **How to use this skill:**

1. **Invoke the skill in GitHub Copilot Chat**  
   Type: `/example-skill [your task description]`

2. **The agent will proceed through phases automatically**  
   You can monitor progress and intervene if needed.

3. **If the agent pauses**  
   Type `Continue` to resume execution.

---

## Phase 1 — Discovery

**Goal**: Understand the context and gather necessary information

- Use `@workspace` to search for relevant files
- Identify project structure and technologies
- List key files that need attention
- Validate prerequisites

**Output**: Summary of discovered context

---

## Phase 2 — Analysis

**Goal**: Analyze gathered information and plan approach

- Examine code patterns and architecture
- Identify potential issues or opportunities
- Consider constraints and requirements
- Formulate execution strategy

**Output**: Analysis findings and execution plan

---

## Phase 3 — Execution

**Goal**: Perform the main task actions

- Make necessary code changes
- Follow best practices for the detected language
- Maintain code quality and consistency
- Document significant changes

**Output**: Implemented changes

---

## Phase 4 — Validation

**Goal**: Verify the work and ensure quality

- Check for compilation/syntax errors
- Verify business logic correctness
- Ensure no regressions introduced
- Validate against original requirements

**Output**: Validation results and any remaining issues

---

## Phase 5 — Documentation

**Goal**: Provide clear summary and next steps

- Summarize what was accomplished
- List any assumptions or decisions made
- Provide next steps or recommendations
- Note any follow-up items

**Output**: Comprehensive summary for the user

---

## Behavioral Rules

- **Autonomous Operation**: Proceed through phases automatically unless blocked
- **Clear Communication**: Report progress at phase transitions
- **Error Handling**: If a phase fails, explain the issue and suggest remediation
- **User Respect**: Stop and ask for guidance when encountering ambiguous requirements
- **Quality Focus**: Prioritize correctness and maintainability over speed

---

## When to Use This Pattern

Use this multi-phase agent skill pattern when:
- The task requires multiple distinct steps
- Each phase builds on the previous one
- You need checkpoints for progress tracking
- The workflow is complex enough to benefit from structure

For simpler tasks, consider using a basic prompt file instead.
