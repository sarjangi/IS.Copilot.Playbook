# Vancity GitHub Copilot Workspace Instructions

<!-- 
These instructions are always active when GitHub Copilot is used in this workspace.
Customize this file with Vancity-specific preferences and standards.
-->

When working in this workspace:

## General Guidelines
- Follow language-specific coding standards defined in `.github/<language>/instructions/`
- Prioritize code readability and maintainability
- Write clear, descriptive commit messages
- Include appropriate error handling and logging

## Navigation
- This workspace organizes GitHub Copilot customizations by language
- .NET content: `.github/dotnet/`
- Python content: `.github/python/`
- JavaScript content: `.github/javascript/`
- Language-agnostic content: `.github/shared/`

## Documentation
- Learning guides available in `docs/guides/`
- skill-creator development tools in `tools/skill-creator/`

## Testing New Content
- Validate frontmatter with: `python tools/skill-creator/scripts/quick_validate.py`
- Test prompts by typing `/promptName` in GitHub Copilot Chat
- Test skills by typing `/skillName` in GitHub Copilot Chat

## Vancity Standards
<!-- Teams should customize this section with organization-specific preferences -->

- Use async/await patterns for I/O operations
- Include comprehensive error handling
- Add logging for debugging and monitoring
- Write unit tests for business logic
- Document public APIs and complex logic
