# Vorflux Skills

This repository contains reusable agent skills for common development and document workflows.

## Skill providers

- [`.agents/`](.agents/) includes API documentation, database migration, and Docker skills.
- [`.claude/`](.claude/) includes document generation and README handling skills.
- [`.gemini/`](.gemini/) includes README, changelog, and CI/CD skills.
- [`.opencode/`](.opencode/) includes code review, test generation, and Git commit skills.

## Use a skill

Skills use the `<provider>/skills/<skill-name>/` directory structure. Each skill provides its instructions in a `SKILL.md` file and can include supporting scripts, templates, or examples.

1. Select the skill that matches your task.
2. Read the skill's `SKILL.md` file.
3. Follow its prerequisites and usage instructions in a compatible agent environment.
