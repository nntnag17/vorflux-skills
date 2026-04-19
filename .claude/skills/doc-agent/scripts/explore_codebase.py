#!/usr/bin/env python3
"""
explore_codebase.py — Deep codebase analysis + README skeleton renderer for doc-agent.

Usage:
    # Analyze only (JSON to stdout):
    python3 explore_codebase.py [directory]

    # Analyze + render README skeleton:
    python3 explore_codebase.py [directory] --render [output_path]

    # Generate ARCHITECTURE.md:
    python3 explore_codebase.py [directory] --architecture [output_path]

The JSON report is also what the AI uses to fill in any remaining {{PLACEHOLDER}} tokens
that require human judgment (features list, overview paragraph, etc.).
"""

import sys
import os
import json
import re
import ast
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "target", "vendor",
}

# Dotdirs included in structure rendering (beyond .github).
INCLUDE_DOTDIRS = {".github", ".claude", ".gemini", ".opencode", ".agents"}

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "README_skeleton.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_safe(path) -> str:
    try:
        return Path(path).read_text(errors="ignore")
    except Exception:
        return ""


def _extract_toml_field(content: str, field: str) -> str | None:
    """Extract a simple top-level TOML scalar field like `name = "foo"`."""
    m = re.search(rf'^{field}\s*=\s*["\']([^"\']+)', content, re.MULTILINE)
    return m.group(1) if m else None


def walk_source(root: Path, exts: tuple, max_files: int = 60):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fname in filenames:
            if any(fname.endswith(e) for e in exts):
                found.append(Path(dirpath) / fname)
                if len(found) >= max_files:
                    return found
    return found


# ---------------------------------------------------------------------------
# Stack detection
# ---------------------------------------------------------------------------

def detect_stack(root: Path) -> dict:
    info: dict[str, Any] = {
        "language": "unknown",
        "framework": "unknown",
        "runtime": "unknown",
        "test_runner": "unknown",
        "package_manager": "unknown",
        "name": root.name,
        "version": "0.1.0",
        "description": "",
        "scripts": [],
        "license": None,
    }

    # ---- Node / JS / TS ----
    pkg_path = root / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(read_safe(pkg_path) or "{}")
        except json.JSONDecodeError:
            pkg = {}
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        info["language"] = "TypeScript" if (root / "tsconfig.json").exists() else "JavaScript"
        info["runtime"] = "Node.js " + pkg.get("engines", {}).get("node", "18+")
        info["name"] = pkg.get("name", root.name)
        info["version"] = pkg.get("version", "0.1.0")
        info["description"] = pkg.get("description", "")
        info["scripts"] = list(pkg.get("scripts", {}).keys())
        info["license"] = pkg.get("license")
        info["package_manager"] = (
            "pnpm" if (root / "pnpm-lock.yaml").exists() else
            "yarn" if (root / "yarn.lock").exists() else "npm"
        )
        for fw, key in [("Next.js", "next"), ("React", "react"), ("Vue.js", "vue"),
                        ("Svelte", "svelte"), ("Fastify", "fastify"),
                        ("Express", "express"), ("NestJS", "@nestjs/core"),
                        ("Hono", "hono"), ("Elysia", "elysia")]:
            if key in deps:
                info["framework"] = fw
                break
        for tr, key in [("jest", "jest"), ("vitest", "vitest"), ("mocha", "mocha")]:
            if key in deps:
                info["test_runner"] = tr
                break

    # ---- Python ----
    elif (root / "pyproject.toml").exists() or (root / "requirements.txt").exists() \
            or (root / "setup.py").exists():
        info["language"] = "Python"
        info["package_manager"] = "pip"
        info["test_runner"] = "pytest"
        if (root / "pyproject.toml").exists():
            content = read_safe(root / "pyproject.toml")
            for field in ("name", "version", "description"):
                val = _extract_toml_field(content, field)
                if val:
                    info[field] = val
            for fw in ["fastapi", "django", "flask", "starlette", "litestar", "tornado"]:
                if fw in content.lower():
                    info["framework"] = fw.capitalize()
                    break
            if "poetry" in content.lower():
                info["package_manager"] = "poetry"
            elif "hatch" in content.lower():
                info["package_manager"] = "hatch"
        info["runtime"] = "Python 3.10+"

    # ---- Go ----
    elif (root / "go.mod").exists():
        info["language"] = "Go"
        info["package_manager"] = "go modules"
        info["test_runner"] = "go test"
        content = read_safe(root / "go.mod")
        m = re.search(r"^module (.+)$", content, re.MULTILINE)
        info["name"] = Path(m.group(1)).name if m else root.name
        m = re.search(r"^go (.+)$", content, re.MULTILINE)
        info["runtime"] = "Go " + m.group(1).strip() if m else "Go 1.21+"

    # ---- Rust ----
    elif (root / "Cargo.toml").exists():
        info["language"] = "Rust"
        info["package_manager"] = "cargo"
        info["test_runner"] = "cargo test"
        content = read_safe(root / "Cargo.toml")
        info["name"] = _extract_toml_field(content, "name") or root.name
        info["version"] = _extract_toml_field(content, "version") or "0.1.0"
        info["runtime"] = "Rust (stable)"

    # ---- Java / Kotlin ----
    elif (root / "pom.xml").exists():
        info["language"] = "Java"
        info["package_manager"] = "Maven"
        info["test_runner"] = "mvn test"
        info["runtime"] = "Java 17+"
    elif (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        info["language"] = "Kotlin" if (root / "build.gradle.kts").exists() else "Java"
        info["package_manager"] = "Gradle"
        info["test_runner"] = "gradle test"
        info["runtime"] = "JVM 17+"

    # ---- Ruby ----
    elif (root / "Gemfile").exists():
        info["language"] = "Ruby"
        info["package_manager"] = "bundler"
        info["test_runner"] = "rspec"
        info["runtime"] = "Ruby 3.2+"

    # ---- Shell / script collection (fallback) ----
    else:
        sh_files = list(root.rglob("*.sh"))
        py_files = list(root.rglob("*.py"))
        rb_files = list(root.rglob("*.rb"))
        if sh_files:
            info["language"] = "Shell"
            info["runtime"] = "bash / zsh"
            info["test_runner"] = "bats"
        elif py_files:
            info["language"] = "Python"
            info["runtime"] = "Python 3+"
            info["test_runner"] = "pytest"
        elif rb_files:
            info["language"] = "Ruby"
            info["runtime"] = "Ruby 3+"
            info["test_runner"] = "rspec"

    # ---- License ----
    for lic_file in ["LICENSE", "LICENSE.md", "LICENSE.txt"]:
        if (root / lic_file).exists():
            content = read_safe(root / lic_file)
            if "MIT" in content:
                info["license"] = "MIT"
            elif "Apache" in content:
                info["license"] = "Apache-2.0"
            elif "GPL" in content:
                info["license"] = "GPL-3.0"
            else:
                info["license"] = "See LICENSE"
            break

    return info


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

def extract_python_api(files: list) -> list:
    symbols = []
    for fpath in sorted(files)[:30]:
        src = read_safe(fpath)
        if not src:
            continue
        try:
            import warnings as _warnings
            with _warnings.catch_warnings():
                _warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(src)
        except SyntaxError:
            continue
        # Only walk top-level items — don't descend into private classes.
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                doc = ast.get_docstring(node) or ""
                args = [a.arg for a in node.args.args if a.arg != "self"]
                sig = f"{node.name}({', '.join(args)})"
                symbols.append({
                    "module": Path(fpath).stem,
                    "name": node.name,
                    "kind": "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                    "signature": sig,
                    "docstring": doc[:200] if doc else "",
                })
            elif isinstance(node, ast.ClassDef):
                if node.name.startswith("_"):
                    continue
                doc = ast.get_docstring(node) or ""
                symbols.append({
                    "module": Path(fpath).stem,
                    "name": node.name,
                    "kind": "class",
                    "signature": node.name,
                    "docstring": doc[:200] if doc else "",
                })
    return symbols[:40]


def extract_js_api(files: list) -> list:
    symbols = []
    export_re = re.compile(
        r"export\s+(?:async\s+)?(?:function|class|const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)"
    )
    for fpath in sorted(files)[:20]:
        src = read_safe(fpath)
        if not src:
            continue
        for m in export_re.finditer(src):
            symbols.append({
                "module": Path(fpath).stem,
                "name": m.group(1),
                "kind": "export",
                "signature": m.group(1),
                "docstring": "",
            })
    return symbols[:40]


def extract_go_api(files: list) -> list:
    symbols = []
    func_re = re.compile(r"^func ([A-Z][A-Za-z0-9_]*)\(([^)]*)\)", re.MULTILINE)
    type_re = re.compile(r"^type ([A-Z][A-Za-z0-9_]*) ", re.MULTILINE)
    for fpath in sorted(files)[:20]:
        src = read_safe(fpath)
        for m in func_re.finditer(src):
            symbols.append({
                "module": Path(fpath).stem,
                "name": m.group(1),
                "kind": "function",
                "signature": f"{m.group(1)}({m.group(2)})",
                "docstring": "",
            })
        for m in type_re.finditer(src):
            symbols.append({
                "module": Path(fpath).stem,
                "name": m.group(1),
                "kind": "type",
                "signature": m.group(1),
                "docstring": "",
            })
    return symbols[:40]


# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------

def extract_env_vars(root: Path) -> list:
    vars_found: dict[str, dict] = {}

    for env_file in [".env.example", ".env.sample", ".env.template", ".env.defaults"]:
        content = read_safe(root / env_file)
        if content:
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                m = re.match(r"^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)", line)
                if m:
                    key, default = m.group(1), m.group(2).strip().strip('"').strip("'")
                    vars_found[key] = {
                        "key": key,
                        "required": not bool(default),
                        "default": default or None,
                        "description": "",
                    }

    # Scan source files for additional env vars not in .env.example.
    # Dict-key dedup prevents duplicates with .env.example entries.
    # Only non-shell source extensions are scanned, avoiding shell variable false positives.
    patterns = [
        r'os\.environ\.get\(["\']([A-Z_][A-Z0-9_]+)',
        r'os\.environ\[["\']([A-Z_][A-Z0-9_]+)',
        r'process\.env\.([A-Z_][A-Z0-9_]+)',
        r'os\.Getenv\(["\']([A-Z_][A-Z0-9_]+)',
        r'std::env::var\(["\']([A-Z_][A-Z0-9_]+)',
        r'ENV\[["\']([A-Z_][A-Z0-9_]+)',
    ]
    combined = re.compile("|".join(patterns))
    for fpath in walk_source(root, (".py", ".js", ".ts", ".go", ".rs", ".rb"), max_files=40):
        src = read_safe(fpath)
        for m in combined.finditer(src):
            key = next(g for g in m.groups() if g)
            if key not in vars_found:
                vars_found[key] = {"key": key, "required": True, "default": None, "description": ""}

    return list(vars_found.values())[:25]


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------

def detect_cli_entrypoints(root: Path, stack: dict) -> list:
    entrypoints = []
    lang = stack.get("language", "")

    if lang == "Python":
        content = read_safe(root / "pyproject.toml")
        # Only scan the [project.scripts] / [project.gui-scripts] / [tool.poetry.scripts]
        # tables — scanning the whole file catches unrelated keys like name/version.
        scripts_section_re = re.compile(
            r'^\[(?:project\.(?:gui-)?scripts|tool\.poetry\.scripts)\]\s*\n(.*?)(?=^\[|\Z)',
            re.MULTILINE | re.DOTALL,
        )
        entry_re = re.compile(
            r'^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*["\']([^"\']+)["\']',
            re.MULTILINE,
        )
        for section in scripts_section_re.finditer(content):
            for m in entry_re.finditer(section.group(1)):
                entrypoints.append({"command": m.group(1), "target": m.group(2)})
        setup_content = read_safe(root / "setup.py")
        for m in re.finditer(r'"([a-z][a-z0-9_-]*)=([^"]+)"', setup_content):
            entrypoints.append({"command": m.group(1), "target": m.group(2)})
        for f in root.rglob("__main__.py"):
            if not any(p in str(f) for p in IGNORE_DIRS):
                entrypoints.append({"command": f"python -m {f.parent.name}", "target": str(f)})

    elif lang in ("JavaScript", "TypeScript"):
        pkg = {}
        try:
            pkg = json.loads(read_safe(root / "package.json") or "{}")
        except Exception:
            pass
        bin_section = pkg.get("bin", {})
        if isinstance(bin_section, str):
            entrypoints.append({"command": pkg.get("name", root.name), "target": bin_section})
        elif isinstance(bin_section, dict):
            for cmd, target in bin_section.items():
                entrypoints.append({"command": cmd, "target": target})

    elif lang == "Go":
        cmd_dir = root / "cmd"
        if cmd_dir.exists():
            for f in cmd_dir.glob("*/main.go"):
                entrypoints.append({"command": f"go run ./cmd/{f.parent.name}", "target": str(f)})
        if (root / "main.go").exists():
            entrypoints.append({"command": "go run .", "target": "main.go"})

    elif lang == "Rust":
        content = read_safe(root / "Cargo.toml")
        for m in re.finditer(r'\[\[bin\]\].*?name\s*=\s*"([^"]+)"', content, re.DOTALL):
            entrypoints.append({"command": f"cargo run --bin {m.group(1)}", "target": m.group(1)})
        if (root / "src" / "main.rs").exists():
            entrypoints.append({"command": "cargo run", "target": "src/main.rs"})

    return entrypoints[:6]


# ---------------------------------------------------------------------------
# Module / directory structure
# ---------------------------------------------------------------------------

PURPOSE_MAP = {
    "src": "main source code",
    "lib": "library / shared utilities",
    "app": "application code",
    "api": "API layer",
    "cmd": "CLI entry points",
    "pkg": "reusable packages",
    "internal": "internal packages (not exported)",
    "tests": "test suite",
    "test": "test suite",
    "__tests__": "test suite",
    "spec": "test specifications",
    "docs": "documentation",
    "scripts": "build / utility scripts",
    "config": "configuration files",
    "migrations": "database migrations",
    "static": "static assets",
    "public": "public assets",
    "assets": "assets (images, fonts, etc.)",
    "components": "UI components",
    "pages": "page components / routes",
    "hooks": "React hooks",
    "utils": "utility functions",
    "helpers": "helper functions",
    "models": "data models",
    "schemas": "data schemas / validation",
    "services": "business logic / services",
    "controllers": "request handlers",
    "routes": "route definitions",
    "middleware": "middleware",
    "handlers": "request handlers",
    "store": "state management",
    "types": "TypeScript type definitions",
    "interfaces": "interface definitions",
    "proto": "protobuf definitions",
    "deploy": "deployment configs",
    "infra": "infrastructure as code",
    "k8s": "Kubernetes manifests",
    "docker": "Docker configuration",
    ".github": "GitHub Actions / templates",
}


def describe_structure(root: Path) -> list:
    dirs = []
    files = []
    try:
        for item in sorted(root.iterdir()):
            if item.name.startswith(".") and item.name not in INCLUDE_DOTDIRS:
                continue
            if item.name in IGNORE_DIRS:
                continue
            if item.is_dir():
                purpose = PURPOSE_MAP.get(item.name, "")
                dirs.append({"name": item.name, "purpose": purpose, "is_dir": True})
            else:
                files.append({"name": item.name, "purpose": "", "is_dir": False})
    except PermissionError:
        pass
    # Dirs first so they are never crowded out by files when the cap is hit.
    return (dirs + files)[:40]


# ---------------------------------------------------------------------------
# Existing documentation coverage
# ---------------------------------------------------------------------------

def _exists_any(root: Path, names: list) -> bool:
    return any((root / n).exists() for n in names)


def audit_docs(root: Path) -> dict:
    return {
        "has_readme": _exists_any(root, ["README.md", "README.rst", "README.txt"]),
        "has_license": _exists_any(root, ["LICENSE", "LICENSE.md", "LICENSE.txt"]),
        "has_contributing": (root / "CONTRIBUTING.md").exists(),
        "has_changelog": _exists_any(root, ["CHANGELOG.md", "CHANGELOG.rst", "HISTORY.md"]),
        "has_code_of_conduct": (root / "CODE_OF_CONDUCT.md").exists(),
        "has_security": (root / "SECURITY.md").exists(),
        "has_docker": _exists_any(root, ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"]),
        "has_ci": _exists_any(root, [".github/workflows", ".gitlab-ci.yml", ".circleci", "Jenkinsfile"]),
        "has_makefile": (root / "Makefile").exists(),
        "has_devcontainer": (root / ".devcontainer").exists(),
    }


# ---------------------------------------------------------------------------
# Detect ports
# ---------------------------------------------------------------------------

MAX_PORTS_REPORTED = 5


def detect_ports(root: Path) -> list:
    ports: set[int] = set()
    # \b anchors avoid false matches like `report(40404)` containing `port`.
    port_re = re.compile(r'\b(?:PORT|port|listen)\b[^\d]*(\d{4,5})')
    for fpath in walk_source(root, (".py", ".js", ".ts", ".go", ".rs"), max_files=30):
        src = read_safe(fpath)
        for m in port_re.finditer(src):
            p = int(m.group(1))
            if 1000 < p < 65535:
                ports.add(p)
    return sorted(ports)[:MAX_PORTS_REPORTED]


# ---------------------------------------------------------------------------
# Module dependency graph (lightweight)
# ---------------------------------------------------------------------------

def build_module_graph(root: Path, stack: dict) -> list:
    """Return a list of {from, to} import edges for ARCHITECTURE.md.

    Only in-repo edges are reported — stdlib and third-party modules are
    filtered out so the graph shows actual internal coupling.
    """
    lang = stack.get("language", "")
    edges = []

    if lang == "Python":
        files = walk_source(root, (".py",), max_files=30)
        local_modules = {Path(f).stem for f in files}
        for fpath in files:
            src = read_safe(fpath)
            module = Path(fpath).stem
            for m in re.finditer(r"^(?:from|import)\s+([\w.]+)", src, re.MULTILINE):
                dep = m.group(1).split(".")[0]
                if dep == module or dep.startswith("_"):
                    continue
                if dep not in local_modules:
                    continue
                edges.append({"from": module, "to": dep})

    elif lang in ("JavaScript", "TypeScript"):
        files = walk_source(root, (".js", ".ts", ".tsx", ".jsx"), max_files=30)
        local_modules = {Path(f).stem for f in files}
        for fpath in files:
            src = read_safe(fpath)
            module = Path(fpath).stem
            for m in re.finditer(r'(?:import|require)\s*\(?["\']([^"\']+)["\']', src):
                dep = m.group(1)
                # Only relative (in-repo) imports are considered.
                if not dep.startswith("."):
                    continue
                dep_stem = Path(dep).stem
                if dep_stem and dep_stem != module and dep_stem in local_modules:
                    edges.append({"from": module, "to": dep_stem})

    # Deduplicate and limit
    seen = set()
    unique = []
    for e in edges:
        key = (e["from"], e["to"])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique[:50]


# ---------------------------------------------------------------------------
# README renderer
# ---------------------------------------------------------------------------

def _install_command(stack: dict) -> str:
    pm = stack.get("package_manager", "unknown")
    commands = {
        "npm": "npm install",
        "pnpm": "pnpm install",
        "yarn": "yarn install",
        "pip": "pip install -r requirements.txt",
        "poetry": "poetry install",
        "hatch": "hatch env create",
        "go modules": "go mod download",
        "cargo": "cargo build",
        "bundler": "bundle install",
        "Maven": "mvn install -DskipTests",
        "Gradle": "./gradlew build -x test",
    }
    return commands.get(pm, "# see package manager docs")


def _test_commands(stack: dict) -> str:
    tr = stack.get("test_runner", "unknown")
    pm = stack.get("package_manager", "npm")
    commands = {
        "jest":       f"{pm} test\n{pm} test -- --coverage",
        "vitest":     f"{pm} test\n{pm} test -- --coverage",
        "mocha":      f"{pm} test",
        "pytest":     "pytest\npytest --cov=. --cov-report=term-missing",
        "go test":    "go test ./...\ngo test ./... -cover",
        "cargo test": "cargo test",
        "rspec":      "bundle exec rspec",
        "mvn test":   "mvn test",
        "gradle test":"./gradlew test",
        "bats":       "bats tests/",
    }
    return commands.get(tr, "# TODO: add test command")


def _badges(stack: dict, docs: dict) -> str:
    parts = []
    name = stack.get("name", "project")
    if docs.get("has_ci"):
        parts.append(f"[![CI](https://github.com/your-org/{name}/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/{name}/actions)")
    version = stack.get("version", "")
    if version:
        parts.append(f"[![Version](https://img.shields.io/badge/version-{version}-blue)]()")
    lic = stack.get("license")
    if lic:
        safe = lic.replace("-", "--")
        parts.append(f"[![License: {lic}](https://img.shields.io/badge/License-{safe}-yellow.svg)](./LICENSE)")
    lang = stack.get("language", "")
    runtime = stack.get("runtime", "")
    if lang and lang != "unknown":
        parts.append(f"[![{lang}](https://img.shields.io/badge/{lang}-{runtime.replace(' ', '_')}-informational)]()")
    return "\n".join(parts) if parts else "<!-- add badges here -->"


def _structure_tree(structure: list, docs: dict, stack: dict) -> str:
    lines = []
    # Track filenames already emitted so trailer entries don't duplicate them.
    emitted: set[str] = set()

    dirs = [e for e in structure if e["is_dir"]]
    files = [e for e in structure if not e["is_dir"]]
    for entry in dirs:
        comment = f"  # {entry['purpose']}" if entry["purpose"] else ""
        lines.append(f"├── {entry['name']}/{comment}")
    for entry in files:
        name_lower = entry["name"].lower()
        # Skip files that the trailer section will add unconditionally.
        if name_lower in ("readme.md", "readme.rst", "readme.txt",
                          "dockerfile", "docker-compose.yml", "docker-compose.yaml",
                          "license", "license.md", "license.txt"):
            emitted.add(name_lower)
            continue
        lines.append(f"├── {entry['name']}")

    # Trailer: only add entries not already listed above.
    if docs.get("has_docker"):
        if "dockerfile" not in emitted:
            lines.append("├── Dockerfile")
        if "docker-compose.yml" not in emitted:
            lines.append("├── docker-compose.yml")
    if docs.get("has_license"):
        if "license" not in emitted and "license.md" not in emitted:
            lines.append("├── LICENSE")
    lines.append("└── README.md")
    return "\n".join(lines)


def _api_section(public_api: list) -> str:
    if not public_api:
        return ""
    lines = ["## API Reference", ""]
    current_module = None
    for sym in public_api:
        if sym["module"] != current_module:
            current_module = sym["module"]
            lines.append(f"### `{current_module}`")
            lines.append("")
        lines.append(f"#### `{sym['signature']}`")
        lines.append("")
        if sym["docstring"]:
            lines.append(sym["docstring"])
        else:
            lines.append(f"<!-- TODO: describe {sym['name']} -->")
        lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _config_section(env_vars: list) -> str:
    if not env_vars:
        return ""
    lines = [
        "## Configuration",
        "",
        "| Variable | Required | Default | Description |",
        "|----------|:--------:|---------|-------------|",
    ]
    for v in env_vars:
        req = "Yes" if v["required"] else "No"
        default = f"`{v['default']}`" if v["default"] else "—"
        desc = v["description"] or "TODO: describe this variable"
        lines.append(f"| `{v['key']}` | {req} | {default} | {desc} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _usage_section(stack: dict, cli_entrypoints: list, ports: list, docs: dict) -> str:
    pm = stack.get("package_manager", "npm")
    scripts = stack.get("scripts", [])
    lang = stack.get("language", "")
    lines = []

    if cli_entrypoints:
        lines.append("### CLI")
        lines.append("")
        for ep in cli_entrypoints:
            lines.append(f"```bash\n{ep['command']}\n```")
            lines.append("")

    lines.append("### Development server")
    lines.append("")
    lines.append("```bash")
    if "dev" in scripts:
        lines.append(f"{pm} run dev")
    elif "start:dev" in scripts:
        lines.append(f"{pm} run start:dev")
    elif lang == "Python":
        lines.append("uvicorn main:app --reload")
    elif lang == "Go":
        lines.append("go run .")
    elif lang == "Rust":
        lines.append("cargo run")
    elif lang == "Shell":
        lines.append("# run individual scripts directly, e.g.:\nbash <script>.sh")
    else:
        lines.append(f"{pm} start")
    lines.append("```")
    lines.append("")

    # Show referenced ports for non-shell stacks. Use neutral framing since we can't
    # always confirm these are the server's own listen ports.
    if ports and lang not in ("Shell",):
        port_str = ", ".join(str(p) for p in ports)
        lines.append(f"Ports referenced in source: **{port_str}**.")
        lines.append("")

    if "build" in scripts:
        lines.append("### Production build")
        lines.append("")
        lines.append("```bash")
        lines.append(f"{pm} run build")
        if "start" in scripts:
            lines.append(f"{pm} start")
        lines.append("```")
        lines.append("")

    if docs.get("has_docker"):
        lines.append("### Docker")
        lines.append("")
        lines.append("```bash")
        lines.append("# Build and start all services")
        lines.append("docker compose up -d")
        lines.append("")
        lines.append("# Follow logs")
        lines.append("docker compose logs -f")
        lines.append("")
        lines.append("# Stop")
        lines.append("docker compose down")
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def render_readme(report: dict, template_path: Path = TEMPLATE_PATH) -> str:
    """Fill README_skeleton.md placeholders with data from the analysis report."""
    template = read_safe(template_path)
    if not template:
        raise FileNotFoundError(f"Template not found: {template_path}")

    stack = report["stack"]
    docs = report["docs_audit"]
    env_vars = report["env_vars"]
    public_api = report["public_api"]
    structure = report["structure"]
    cli_entrypoints = report["cli_entrypoints"]
    ports = report["ports"]

    name = stack.get("name", "project")
    description = stack.get("description", "") or "<!-- TODO: one-line description -->"
    runtime = stack.get("runtime", "")
    lang = stack.get("language", "unknown")
    pm = stack.get("package_manager", "unknown")

    # Prerequisites
    prereqs = []
    if runtime and runtime != "unknown":
        prereqs.append(f"- [{runtime}](https://{lang.lower()}.org)")
    if pm not in ("unknown", "go modules"):
        prereqs.append(f"- {pm}")
    if docs.get("has_docker"):
        prereqs.append("- [Docker](https://docs.docker.com/get-docker/) ≥ 24 (optional)")
    prereqs_str = "\n".join(prereqs) if prereqs else "<!-- TODO: list prerequisites -->"

    # Env setup step
    env_setup = "\n# 3. Configure environment variables\ncp .env.example .env\n# Edit .env with your values" if env_vars else ""

    # TOC entries
    config_toc = "- [Configuration](#configuration)\n" if env_vars else ""
    api_toc = "- [API Reference](#api-reference)\n" if public_api else ""

    replacements = {
        "{{PROJECT_NAME}}": name,
        "{{ONE_LINE_DESCRIPTION}}": description,
        "{{BADGES}}": _badges(stack, docs),
        "{{CONFIG_TOC_ENTRY}}": config_toc,
        "{{API_TOC_ENTRY}}": api_toc,
        "{{OVERVIEW_PARAGRAPH}}": "<!-- TODO: Write 2-3 sentences describing what this project does, who it is for, and why it exists. -->",
        "{{FEATURES_LIST}}": "<!-- TODO: Replace with 4-8 specific, concrete features of this project. -->\n- **Feature 1** — describe a key capability\n- **Feature 2** — describe another capability\n- **Feature 3** — describe another capability",
        "{{PREREQUISITES_LIST}}": prereqs_str,
        "{{INSTALL_COMMAND}}": _install_command(stack),
        "{{ENV_SETUP_STEP}}": env_setup,
        "{{CONFIGURATION_SECTION}}": _config_section(env_vars),
        "{{USAGE_SECTION}}": _usage_section(stack, cli_entrypoints, ports, docs),
        "{{API_REFERENCE_SECTION}}": _api_section(public_api),
        "{{STRUCTURE_TREE}}": _structure_tree(structure, docs, stack),
        "{{TEST_COMMANDS}}": _test_commands(stack),
        "{{CONTRIBUTING_SECTION}}": (
            "See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines."
            if docs.get("has_contributing") else
            "1. Fork the repository\n"
            "2. Create a feature branch: `git checkout -b feat/my-feature`\n"
            "3. Commit using [Conventional Commits](https://www.conventionalcommits.org/): `git commit -m \"feat: add my feature\"`\n"
            "4. Push and open a Pull Request"
        ),
        "{{LICENSE_SECTION}}": (
            f"Distributed under the **{stack['license']}** license."
            + (" See [LICENSE](./LICENSE) for details." if docs.get("has_license") else "")
            if stack.get("license") else
            "<!-- TODO: add license information -->"
        ),
    }

    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    return result


# ---------------------------------------------------------------------------
# ARCHITECTURE.md renderer
# ---------------------------------------------------------------------------

def render_architecture(report: dict) -> str:
    stack = report["stack"]
    structure = report["structure"]
    module_graph = report.get("module_graph", [])
    public_api = report["public_api"]
    name = stack.get("name", "project")
    lang = stack.get("language", "unknown")
    framework = stack.get("framework", "unknown")

    lines = [
        f"# {name} — Architecture",
        "",
        "## Overview",
        "",
        f"- **Language:** {lang}",
        *([] if framework == "unknown" else [f"- **Framework:** {framework}"]),
        f"- **Runtime:** {stack.get('runtime', 'unknown')}",
        "",
        "<!-- TODO: Add a 2-3 sentence architectural summary. -->",
        "",
        "---",
        "",
        "## Directory Structure",
        "",
    ]

    for entry in structure:
        if entry["is_dir"]:
            comment = f" — {entry['purpose']}" if entry["purpose"] else ""
            lines.append(f"### `{entry['name']}/`{comment}")
            lines.append("")
            lines.append("<!-- TODO: describe the contents and responsibilities of this directory. -->")
            lines.append("")

    lines += [
        "---",
        "",
        "## Key Modules",
        "",
    ]

    if public_api:
        modules = {}
        for sym in public_api:
            modules.setdefault(sym["module"], []).append(sym)
        for mod, syms in list(modules.items())[:10]:
            lines.append(f"### `{mod}`")
            lines.append("")
            for sym in syms[:5]:
                lines.append(f"- `{sym['signature']}` — {sym['docstring'] or 'TODO: describe'}")
            lines.append("")
    else:
        lines.append("<!-- TODO: describe key modules and their responsibilities. -->")
        lines.append("")

    if module_graph:
        lines += [
            "---",
            "",
            "## Dependency Graph (top imports)",
            "",
            "```",
        ]
        for edge in module_graph[:20]:
            lines.append(f"{edge['from']} → {edge['to']}")
        lines.append("```")
        lines.append("")

    lines += [
        "---",
        "",
        "## Data Flow",
        "",
        "<!-- TODO: describe how data flows through the system (request → handler → service → storage). -->",
        "",
        "---",
        "",
        "## External Dependencies",
        "",
        "<!-- TODO: list key third-party libraries and why they are used. -->",
    ]

    return "\n".join(l for l in lines if l is not None)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    # First positional arg is the root directory; flags start with "--".
    root_arg = args[0] if args and not args[0].startswith("--") else "."
    root = Path(root_arg).resolve()

    render_mode = "--render" in args
    arch_mode = "--architecture" in args

    render_output = None
    arch_output = None
    if render_mode:
        idx = args.index("--render")
        next_arg = args[idx + 1] if idx + 1 < len(args) else None
        render_output = next_arg if next_arg and not next_arg.startswith("--") else str(root / "README_generated.md")

    if arch_mode:
        idx = args.index("--architecture")
        next_arg = args[idx + 1] if idx + 1 < len(args) else None
        arch_output = next_arg if next_arg and not next_arg.startswith("--") else str(root / "ARCHITECTURE.md")

    stack = detect_stack(root)
    lang = stack["language"]

    ext_map = {
        "Python": (".py",),
        "JavaScript": (".js", ".mjs"),
        "TypeScript": (".ts", ".tsx"),
        "Go": (".go",),
        "Rust": (".rs",),
    }
    exts = ext_map.get(lang, (".py", ".js", ".ts", ".sh", ".rb"))
    source_files = sorted(walk_source(root, exts, max_files=60))

    if lang == "Python":
        api = extract_python_api(source_files)
    elif lang in ("JavaScript", "TypeScript"):
        api = extract_js_api(source_files)
    elif lang == "Go":
        api = extract_go_api(source_files)
    else:
        # For Shell/unknown repos, attempt Python API extraction if .py files exist
        # (e.g. skill libraries where scripts live under dotfile dirs).
        py_files = sorted(walk_source(root, (".py",), max_files=60))
        if py_files:
            api = extract_python_api(py_files)
            # Merge so source_file_count reflects what was actually analyzed.
            source_files = sorted(set(source_files) | set(py_files))
        else:
            api = []

    report = {
        "root": str(root),
        "stack": stack,
        "structure": describe_structure(root),
        "env_vars": extract_env_vars(root),
        "cli_entrypoints": detect_cli_entrypoints(root, stack),
        "ports": detect_ports(root),
        "public_api": api,
        "docs_audit": audit_docs(root),
        "source_file_count": len(source_files),
        "module_graph": build_module_graph(root, stack) if arch_mode else [],
    }

    if render_mode:
        readme = render_readme(report)
        Path(render_output).write_text(readme)
        print(f"README written to: {render_output}", file=sys.stderr)

    if arch_mode:
        arch = render_architecture(report)
        Path(arch_output).write_text(arch)
        print(f"ARCHITECTURE.md written to: {arch_output}", file=sys.stderr)

    if not render_mode and not arch_mode:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
