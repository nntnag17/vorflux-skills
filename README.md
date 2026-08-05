# Vorflux Skills

A curated collection of AI agent skills for [Vorflux](https://vorflux.com) -- reusable, production-ready playbooks that give AI coding assistants superpowers. Each skill is a self-contained module with instructions, scripts, and templates that an agent can invoke on demand.

---

## What Are Skills?

Skills are **pre-written expert playbooks** that plug into AI coding agents. Instead of figuring things out from scratch every time, an agent can invoke a skill and get:

- **Step-by-step instructions** tailored to the task
- **Scripts** that automate the heavy lifting (Python, Bash)
- **Templates** for consistent, high-quality output (JSON, YAML, SQL, Jinja2)

Think of them as reusable recipes -- "generate a PDF report", "scaffold unit tests", "create a Dockerfile" -- that any compatible agent can call.

---

## Skills Catalog

### Document Generation

| Skill | Description | Trigger Phrases |
|-------|-------------|-----------------|
| **pdf** | Generate PDF reports, invoices, and documents from data | `create a PDF`, `generate a PDF report`, `export as PDF` |
| **pptx** | Build PowerPoint slide decks with themes and layouts | `create a presentation`, `make slides`, `generate PPTX` |
| **xlsx** | Create Excel spreadsheets with formulas and formatting | `create an Excel file`, `make a spreadsheet`, `export to Excel` |

### DevOps & Infrastructure

| Skill | Description | Trigger Phrases |
|-------|-------------|-----------------|
| **docker-setup** | Dockerize applications with Dockerfile and Compose configs | `dockerize this`, `create a Dockerfile`, `add Docker Compose` |
| **ci-cd** | Set up GitHub Actions workflows and CI/CD pipelines | `set up CI/CD`, `create GitHub Actions`, `add a CI pipeline` |
| **db-migrate** | Generate database migration files (Alembic, Prisma, raw SQL) | `create a migration`, `add a column`, `migrate the database` |

### Code Quality & Workflow

| Skill | Description | Trigger Phrases |
|-------|-------------|-----------------|
| **code-review** | Automated code review with static analysis and checklists | `review this code`, `find bugs`, `check for security issues` |
| **test-gen** | Scaffold unit and integration tests (pytest, Jest) | `generate tests`, `write unit tests`, `add test coverage` |
| **git-commit** | Analyze changes and craft conventional commit messages | `commit my changes`, `write a commit message`, `stage and commit` |

### Documentation

| Skill | Description | Trigger Phrases |
|-------|-------------|-----------------|
| **api-docs** | Generate OpenAPI/Swagger specs from source code | `generate API docs`, `create OpenAPI spec`, `document my API` |
| **readme-gen** | Analyze a project and generate a comprehensive README | `generate a README`, `create README.md`, `document my project` |
| **changelog** | Generate changelogs and release notes from git history | `generate changelog`, `create release notes`, `what changed` |

---

## Repository Structure

```
vorflux-skills/
├── .agents/skills/          # Shared agent skills (platform-agnostic)
│   ├── api-docs/
│   ├── db-migrate/
│   └── docker-setup/
├── .claude/skills/          # Claude Code skills
│   ├── handle_readme/
│   ├── pdf/
│   ├── pptx/
│   └── xlsx/
├── .gemini/skills/          # Gemini skills
│   ├── changelog/
│   ├── ci-cd/
│   └── readme-gen/
└── .opencode/skills/        # OpenCode skills
    ├── code-review/
    ├── git-commit/
    └── test-gen/
```

Each skill directory follows the same layout:

```
skill-name/
├── SKILL.md           # Metadata + instructions for the agent
├── scripts/           # Python or Bash scripts that do the work
└── templates/         # JSON, YAML, SQL, Jinja2 templates
```

---

## How It Works

1. **Agent detects intent** -- The user says something like _"create a Dockerfile"_
2. **Skill is matched** -- The agent finds the `docker-setup` skill via trigger phrases
3. **SKILL.md is read** -- The agent loads the instructions and understands what to do
4. **Scripts run** -- Automation scripts handle scaffolding, generation, or analysis
5. **Output is delivered** -- The user gets a ready-to-use artifact (file, config, report)

---

## Supported Platforms

Skills are organized by the AI coding assistant they target:

| Directory | Platform | Skills |
|-----------|----------|--------|
| `.agents/` | Any agent | api-docs, db-migrate, docker-setup |
| `.claude/` | Claude Code | handle_readme, pdf, pptx, xlsx |
| `.gemini/` | Gemini | changelog, ci-cd, readme-gen |
| `.opencode/` | OpenCode | code-review, git-commit, test-gen |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Bash

### Install Dependencies

Skills self-install their dependencies at runtime, but you can pre-install everything for faster execution:

```bash
pip install weasyprint jinja2 markdown python-pptx openpyxl pyyaml
```

### Using a Skill

Skills are invoked automatically by compatible AI agents. To use one manually:

```bash
# Generate a PDF report
python3 .claude/skills/pdf/scripts/generate_pdf.py data.json output.pdf

# Create a PowerPoint deck
python3 .claude/skills/pptx/scripts/generate_pptx.py manifest.json output.pptx

# Generate an Excel spreadsheet
python3 .claude/skills/xlsx/scripts/generate_xlsx.py data.json

# Generate an OpenAPI spec
python3 .agents/skills/api-docs/scripts/gen_openapi.py routes_dir/ openapi.yaml

# Set up Docker for a project
bash .agents/skills/docker-setup/scripts/setup_docker.sh node 3000
```

---

## Adding a New Skill

1. Choose the right directory based on the target platform (`.agents/`, `.claude/`, `.gemini/`, or `.opencode/`)
2. Create a new folder: `skills/<skill-name>/`
3. Add a `SKILL.md` with frontmatter metadata and step-by-step instructions
4. Add scripts in `scripts/` and templates in `templates/`
5. Test the skill end-to-end with the target agent

### SKILL.md Frontmatter

```yaml
---
name: my-skill
description: What this skill does and when to trigger it.
version: 1.0.0
license: MIT
user-invocable: true
argument-hint: [what the user passes]
allowed-tools: Read, Bash, Write
---
```

---

## License

MIT
