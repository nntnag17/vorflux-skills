---
name: doc-agent
description: Deep documentation agent for codebases that need more than a basic README. Use this when the user asks to "document this codebase", "explore and document", "write docs for this project", "generate an ARCHITECTURE.md", "document all modules", "create multi-file documentation", or "explain how this codebase works in docs". Unlike readme-gen (which is template-driven and single-README), doc-agent first performs a deep exploration of the codebase — module structure, public API surface, import graph, CLI entry points, env vars — and then produces a filled README plus an optional ARCHITECTURE.md and per-module reference. Use readme-gen for quick single-README generation; use doc-agent when you need thorough, multi-document coverage of a non-trivial codebase.
version: 1.0.0
license: MIT
allowed-tools:
  - read
  - write
  - bash
metadata:
  version: "1.0"
  tags: [documentation, readme, architecture, modules, api-reference, multi-file]
---

# doc-agent — Deep Codebase Documentation Agent

Explore a codebase thoroughly and produce clear, accurate documentation: a filled
README.md and an optional ARCHITECTURE.md. Driven by static analysis of the actual
code — not generic templates.

## How to use

```
/doc-agent [directory or repo path]
```

## Instructions

### Step 1 — Run the codebase explorer

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/explore_codebase.py "$ARGUMENTS"
```

This emits a JSON report to stdout covering:
- Stack (language, framework, runtime, package manager, test runner)
- Public API surface (exported functions, classes, types with signatures and docstrings)
- Directory structure with purpose annotations
- Environment variables (from `.env.example` and source file scanning)
- CLI entry points
- Ports referenced in source
- Documentation coverage audit (README, LICENSE, CONTRIBUTING, CI, Docker, etc.)

**Auto-behaviors to be aware of:**
- For Shell/unknown repos that contain `.py` files (e.g. skill libraries), the script automatically walks and extracts Python API symbols even though the primary language is Shell.
- `describe_structure` includes common dotfile dirs: `.github`, `.claude`, `.gemini`, `.opencode`, `.agents`. Other dotdirs (`.git`, `node_modules`, etc.) are excluded.
- Env var source scanning covers `.py`, `.js`, `.ts`, `.go`, `.rs`, `.rb` only — `.sh` files are intentionally excluded to avoid false positives from shell variable expansions.

Read the JSON carefully. It is the ground truth for everything you write next.

### Step 2 — Render the README skeleton

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/explore_codebase.py "$ARGUMENTS" \
  --render README_generated.md
```

This fills `templates/README_skeleton.md` with all data the script can determine
automatically and writes the result to `README_generated.md` (or the path you
specify). Remaining `<!-- TODO: ... -->` tokens mark sections that require your
judgment — fill them in using what you learned from the JSON report and any
additional file reads.

**Sections you must always fill in manually:**
- `## Overview` — write 2-3 sentences describing what the project does, who it is
  for, and why it exists. Read the main entry point or top-level source files if
  the description field was empty.
- `## Features` — replace the placeholder bullets with 4-8 specific, concrete
  capabilities you observed in the code.
- Any `<!-- TODO: describe ... -->` comments in the API Reference section.

### Step 3 — Generate ARCHITECTURE.md (optional but recommended for non-trivial codebases)

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/explore_codebase.py "$ARGUMENTS" \
  --architecture ARCHITECTURE.md
```

This produces a skeleton ARCHITECTURE.md covering:
- Language / framework / runtime summary
- Per-directory responsibilities
- Key modules and their exported symbols
- Import dependency graph (top 20 edges)
- Placeholder sections for Data Flow and External Dependencies

Fill in the `<!-- TODO: ... -->` sections using your understanding of the code.

### Step 4 — Deep-read key files to fill in TODOs

For each remaining `<!-- TODO: ... -->` token:

1. Identify which source file is most relevant (entry point, main module, core service).
2. Read it.
3. Write a concrete, accurate description — no generic filler.

Typical files to read:
- `main.py` / `index.ts` / `main.go` / `src/main.rs` — entry point and wiring
- `README.md` (if one exists) — existing description to preserve or improve
- The largest source file by line count — usually the core logic
- Any file named `app.py`, `server.ts`, `router.go`, `lib.rs`

### Step 5 — Quality check before writing

Verify the final README and ARCHITECTURE.md:

- [ ] No `<!-- TODO: ... -->` tokens remain (or are intentionally left for the user)
- [ ] All code blocks have language hints (` ```bash `, ` ```python `, etc.)
- [ ] No generic placeholder text (`your-project`, `example.com`, `Feature 1`)
- [ ] Install command matches the actual package manager detected
- [ ] Test command matches the actual test runner detected
- [ ] API Reference entries have real descriptions, not "TODO: describe X"
- [ ] Badges reference the correct repo slug (or are clearly marked as needing update)

### Step 6 — Write output files

Write the completed files:

- `README.md` — if no README exists, write directly. If one exists, write to
  `README_generated.md` and note the difference.
- `ARCHITECTURE.md` — write if generated and non-trivial content was found.

Tell the user:
- Which files were written and where
- Which `<!-- TODO: ... -->` sections (if any) still need human input
- A one-line summary of what the project does, based on your exploration

## Differences from readme-gen

| | readme-gen | doc-agent |
|---|---|---|
| Depth | Single README, template-driven | README + optional ARCHITECTURE.md + module reference |
| API surface | Not extracted | Extracts public functions, classes, types with signatures |
| Import graph | Not analyzed | Built and included in ARCHITECTURE.md |
| Shell/script repos | Falls back to unknown | Detects Shell language, lists plugin categories |
| TODO handling | Leaves generic placeholders | Reads source files to fill in TODOs |
| Best for | Quick README for a known stack | Thorough docs for any codebase |
