# README Section Writing Guide

This guide tells you what to write in each section of the README and how to write it well.
Every section must be filled with information you confirmed by reading the actual source code.

---

## Section 1: Title + One-Line Description

**Format:**
```
# <project-name>

> <one sentence that says what the project does and who it is for>
```

**Rules:**
- The description must say what the project *does*, not what it *is*. "Converts Markdown files to PDF" is good. "A Markdown tool" is not.
- If the project has a `description` field in `package.json` / `pyproject.toml`, use it as a starting point — but rewrite it to be concrete and active.
- If no description exists, derive it from the entry point's docstring or the first comment block in the main file.

---

## Section 2: Badges

Only include badges for things that actually exist in the repo:

| Badge | Include when |
|-------|-------------|
| CI status | `.github/workflows/` exists |
| Version | `package.json` or `pyproject.toml` has a version field |
| License | `LICENSE` file exists |
| Language | Include with the detected language slug |
| Coverage | A coverage config or badge URL exists |

Use real slugs. If you cannot determine the GitHub org/repo, leave the badge URL as `https://github.com/OWNER/REPO/...` and note it needs updating.

---

## Section 3: Features

List 3–7 specific capabilities. Each bullet must:
- Name a real feature you found in the code (a function, a route, a CLI flag, a class)
- Say what it does in plain language
- Be concrete enough that a developer knows what they get

**Good:** `- **Batch processing** — process up to 1,000 records per job via the \`/api/batch\` endpoint`
**Bad:** `- **Scalable** — designed for scale`

---

## Section 4: Prerequisites

List only what is actually required to run the project:
- Runtime version (from `go.mod`, `package.json` engines, `requires-python`, etc.)
- External services (database, Redis, etc.) — only if you found connection code or env vars for them
- Docker — only if `Dockerfile` or `docker-compose.yml` exists

Do not list tools that are optional or only needed for development unless you mark them `(optional)`.

---

## Section 5: Installation

Provide the exact sequence of commands a developer runs to go from zero to running:

```bash
git clone <repo-url>
cd <project-name>
<install dependencies>
<copy env file if .env.example exists>
<any required setup steps>
```

Every command must be real. If you are not sure of the repo URL, use `https://github.com/OWNER/REPO.git` and note it.

---

## Section 6: Configuration

If the project has environment variables, show them in a table:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VAR_NAME` | Yes / No | `value` or — | What it controls |

- Mark a variable Required if it has no default and the app will crash or misbehave without it.
- Derive descriptions from: variable names, comments in `.env.example`, how the variable is used in source code.
- If `.env.example` exists, tell the user to copy it: `cp .env.example .env`

If there are no environment variables, omit this section entirely.

---

## Section 7: Usage

Show the most common way to use the project. Pick the interface type:

**CLI project:** Show the primary command with its most important flags.
```bash
<binary> [flags] <args>
```
List the flags you found in the source (from `argparse`, `cobra`, `commander`, etc.).

**Library:** Show an import + the most important function call with real argument names.
```python
from mylib import do_thing
result = do_thing(input="value", option=True)
```

**HTTP API:** Show the base URL and 2–3 representative endpoints you found in the route definitions.
```bash
curl http://localhost:<port>/api/endpoint
```

**Web app:** Show the dev server command and the URL it serves.

---

## Section 8: API Reference (only for libraries and HTTP APIs)

For **libraries**: list the public functions/classes you found in the API surface extraction. For each:
- Function signature with real parameter names
- One-sentence description (from docstring if available, otherwise inferred from the name and body)
- Return type if determinable

For **HTTP APIs**: list the routes you found. For each:
- Method + path
- What it does
- Request body shape (if you found it in the code)
- Response shape (if you found it in the code)

Skip this section for CLI tools and web apps.

---

## Section 9: Testing

Show the exact commands to run tests. Use the test runner you detected:

```bash
# Run all tests
<test command>

# Run with coverage
<test command with coverage flag>
```

If you found test files, mention what they cover (e.g., "Tests cover the authentication flow and data validation layer").

---

## Section 10: Project Structure

Show a directory tree of the top-level directories and key files. Use the `source_dirs` from the exploration output. Annotate each directory with what it contains.

<!-- Example only — replace every entry with a directory or file that actually
     exists in the repo, derived from `source_dirs` in the exploration output. -->
```
project-name/
├── src/          # Application source code
├── tests/        # Test suite
├── docs/         # Documentation
├── .env.example  # Environment variable template
└── README.md
```

Only include directories that actually exist.

---

## Section 11: Contributing

If `CONTRIBUTING.md` exists: link to it.
If not, write a short standard guide:
1. Fork the repo
2. Create a branch: `git checkout -b feat/my-feature`
3. Commit with Conventional Commits: `git commit -m "feat: add my feature"`
4. Open a Pull Request

---

## Section 12: License

If `LICENSE` exists: state the license name and link to the file.
If not: write `License not specified.` — do not invent a license.

---

## Gaps to Report

After writing the README, check for these gaps and report them to the user:

| Gap | Why it matters |
|-----|---------------|
| No `LICENSE` file | Contributors and users cannot know their rights |
| No `.env.example` | New developers cannot know what env vars to set |
| No `CONTRIBUTING.md` | Unclear how to submit changes |
| Entry point has no docstring | Hard to understand what the program does |
| No test files found | Cannot show usage examples from tests |
| `README.md` already exists | Note what was kept vs. regenerated |
