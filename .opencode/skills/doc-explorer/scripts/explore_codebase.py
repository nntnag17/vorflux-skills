#!/usr/bin/env python3
"""
explore_codebase.py — Deep code exploration for documentation generation.

Reads actual source files to extract the real public API surface, entry points,
usage patterns, and configuration — not just file-level metadata.

Usage: python3 explore_codebase.py [directory or file]
Outputs JSON to stdout.
"""

import sys
import json
import re
import ast
from pathlib import Path


# ── Module-level constants ────────────────────────────────────────────────────

# Directories to skip when iterating source trees. Authoritative list, shared
# by every extractor via _iter_source_files.
SKIP_DIR_PARTS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
    ".mypy_cache", "target", "vendor",
}

# File-scan limits. Extracted so truncation policy is auditable in one place.
MAX_FILES_SCANNED = 200
MAX_API_SYMBOLS = 40
MAX_ROUTES = 20
MAX_CLI_FLAGS = 15
MAX_ENV_VARS = 25
MAX_DEPS = 10
MAX_TEST_EXAMPLES = 3
MAX_ENTRY_POINTS = 8
MAX_SOURCE_DIRS = 10
MAX_PORTS = 5

# Framework / test-runner registries for detect_stack. Module-level so they
# are not rebuilt on every call.
PY_FRAMEWORKS = [
    ("FastAPI",   "fastapi"),
    ("Django",    "django"),
    ("Flask",     "flask"),
    ("Starlette", "starlette"),
    ("Tornado",   "tornado"),
    ("aiohttp",   "aiohttp"),
]

JS_FRAMEWORKS = [
    ("Next.js",  "next"),
    ("React",    "react"),
    ("Vue.js",   "vue"),
    ("Fastify",  "fastify"),
    ("Express",  "express"),
    ("NestJS",   "@nestjs/core"),
    ("Svelte",   "svelte"),
    ("Astro",    "astro"),
]

JS_TEST_RUNNERS = [
    ("jest",   "jest"),
    ("vitest", "vitest"),
    ("mocha",  "mocha"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_safe(path) -> str:
    try:
        return Path(path).read_text(errors="ignore")
    except Exception:
        return ""


def _is_skipped(path: Path) -> bool:
    """True if any path component matches SKIP_DIR_PARTS."""
    return any(part in SKIP_DIR_PARTS for part in path.parts)


def _is_test_file(path: Path, lang: str) -> bool:
    """Language-aware test-file detection using suffix rules, not substring."""
    name = path.name
    if lang == "Python":
        return name.startswith("test_") or name.endswith("_test.py")
    if lang in ("JavaScript", "TypeScript"):
        # Recognise .test.*, .spec.*, or residing inside a __tests__ directory.
        stem_parts = name.split(".")
        if len(stem_parts) >= 3 and stem_parts[-2] in ("test", "spec"):
            return True
        return "__tests__" in path.parts
    if lang == "Go":
        return name.endswith("_test.go")
    return False


def _iter_source_files(root: Path, suffixes, limit=None, exclude_tests_lang=None):
    """
    Walk ``root`` yielding files whose suffix is in ``suffixes``.

    - Skips any file under a SKIP_DIR_PARTS directory.
    - If ``exclude_tests_lang`` is set, also filters out test files for that
      language.
    - ``limit`` caps the number yielded (filter-then-slice).
    """
    suffix_set = set(suffixes)
    count = 0
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix not in suffix_set:
            continue
        if _is_skipped(f):
            continue
        if exclude_tests_lang and _is_test_file(f, exclude_tests_lang):
            continue
        yield f
        count += 1
        if limit is not None and count >= limit:
            return


def _word_in(needle: str, haystack: str) -> bool:
    """
    Containment check with package-name boundaries.

    Unlike ``\\b``, this rejects neighbours that are word characters OR a
    hyphen, so ``flask`` won't match ``flask-admin`` and ``redis`` won't
    match ``redis-om`` / ``redisearch``.
    """
    pattern = rf"(?<![\w-]){re.escape(needle)}(?![\w-])"
    return re.search(pattern, haystack) is not None


# ── Stack detection ───────────────────────────────────────────────────────────

def detect_stack(root: Path) -> dict:
    result = {
        "language": "unknown",
        "framework": "unknown",
        "runtime": "unknown",
        "test_runner": "unknown",
        "package_manager": "unknown",
        "name": root.name,
        "version": "0.1.0",
        "description": "",
        "scripts": [],
        "repo_url": "",
    }

    # Node / JS / TS
    if (root / "package.json").exists():
        pkg = json.loads(read_safe(root / "package.json") or "{}")
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        result["language"] = "TypeScript" if (root / "tsconfig.json").exists() else "JavaScript"
        result["runtime"] = "Node.js " + pkg.get("engines", {}).get("node", "18+")
        result["name"] = pkg.get("name", root.name)
        result["version"] = pkg.get("version", "0.1.0")
        result["description"] = pkg.get("description", "")
        result["scripts"] = list(pkg.get("scripts", {}).keys())
        result["package_manager"] = (
            "pnpm" if (root / "pnpm-lock.yaml").exists() else
            "yarn" if (root / "yarn.lock").exists() else "npm"
        )
        repo = pkg.get("repository")
        result["repo_url"] = repo.get("url", "") if isinstance(repo, dict) else (repo or "")
        result["framework"]  = next((fw for fw, key in JS_FRAMEWORKS   if key in deps), "unknown")
        result["test_runner"] = next((tr for tr, key in JS_TEST_RUNNERS if key in deps), "unknown")

    # Python
    elif (root / "pyproject.toml").exists() or (root / "requirements.txt").exists() or (root / "setup.py").exists():
        result["language"] = "Python"
        result["package_manager"] = "pip"
        result["test_runner"] = "pytest"
        result["runtime"] = "Python 3"
        if (root / "pyproject.toml").exists():
            content = read_safe(root / "pyproject.toml")
            m = re.search(r'name\s*=\s*"([^"]+)"', content)
            result["name"] = m.group(1) if m else root.name
            m = re.search(r'version\s*=\s*"([^"]+)"', content)
            result["version"] = m.group(1) if m else "0.1.0"
            m = re.search(r'description\s*=\s*"([^"]+)"', content)
            result["description"] = m.group(1) if m else ""
            m = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
            if m:
                result["runtime"] = f"Python {m.group(1)}"
            lowered = content.lower()
            result["framework"] = next(
                (fw for fw, key in PY_FRAMEWORKS if _word_in(key, lowered)),
                "unknown",
            )
            if _word_in("poetry", lowered):
                result["package_manager"] = "poetry"
            elif _word_in("hatch", lowered):
                result["package_manager"] = "hatch"
        elif (root / "setup.py").exists():
            content = read_safe(root / "setup.py")
            m = re.search(r'name\s*=\s*["\']([^"\']+)', content)
            result["name"] = m.group(1) if m else root.name

    # Go
    elif (root / "go.mod").exists():
        result["language"] = "Go"
        result["package_manager"] = "go modules"
        result["test_runner"] = "go test"
        content = read_safe(root / "go.mod")
        m = re.search(r"^module (.+)$", content, re.MULTILINE)
        result["name"] = Path(m.group(1)).name if m else root.name
        m = re.search(r"^go (.+)$", content, re.MULTILINE)
        result["runtime"] = f"Go {m.group(1).strip()}" if m else "Go 1.21+"

    # Rust
    elif (root / "Cargo.toml").exists():
        result["language"] = "Rust"
        result["package_manager"] = "cargo"
        result["test_runner"] = "cargo test"
        result["runtime"] = "Rust (stable)"
        content = read_safe(root / "Cargo.toml")
        m = re.search(r'^name\s*=\s*"([^"]+)"', content, re.MULTILINE)
        result["name"] = m.group(1) if m else root.name
        m = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        result["version"] = m.group(1) if m else "0.1.0"
        m = re.search(r'^description\s*=\s*"([^"]+)"', content, re.MULTILINE)
        result["description"] = m.group(1) if m else ""

    # Ruby
    elif (root / "Gemfile").exists():
        result["language"] = "Ruby"
        result["package_manager"] = "bundler"
        result["test_runner"] = "rspec"
        result["runtime"] = "Ruby"
        if (root / "config" / "application.rb").exists():
            result["framework"] = "Rails"

    # Java / Kotlin
    elif (root / "pom.xml").exists():
        result["language"] = "Java"
        result["package_manager"] = "maven"
        result["test_runner"] = "junit"
        result["runtime"] = "Java 17+"
    elif (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        result["language"] = "Kotlin" if (root / "build.gradle.kts").exists() else "Java"
        result["package_manager"] = "gradle"
        result["test_runner"] = "junit"
        result["runtime"] = "JVM 17+"

    else:
        # No manifest found — fall back to scanning source files so that
        # single-directory / source-only inputs are still useful.
        result["language"] = _detect_language_from_sources(root)
        if result["language"] == "Python":
            result["runtime"] = "Python 3"
            result["test_runner"] = "pytest"
        elif result["language"] == "Go":
            result["runtime"] = "Go"
            result["test_runner"] = "go test"
        result["name"] = root.name

    return result


def _detect_language_from_sources(root: Path) -> str:
    """
    Inspect source-file extensions in ``root`` and return the most common
    language, or ``"unknown"`` if nothing is found.

    Only used when no manifest (package.json, pyproject.toml, go.mod, ...)
    is present — this keeps the explorer useful for raw source directories
    and small code samples.
    """
    ext_to_lang = {
        ".py":  "Python",
        ".js":  "JavaScript",
        ".jsx": "JavaScript",
        ".ts":  "TypeScript",
        ".tsx": "TypeScript",
        ".go":  "Go",
        ".rs":  "Rust",
        ".rb":  "Ruby",
        ".java": "Java",
        ".kt":  "Kotlin",
    }
    counts = {}
    for f in _iter_source_files(root, ext_to_lang.keys(), limit=MAX_FILES_SCANNED):
        lang = ext_to_lang.get(f.suffix)
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    if not counts:
        return "unknown"
    return max(counts.items(), key=lambda kv: kv[1])[0]


# ── Entry point detection ─────────────────────────────────────────────────────

def find_entry_points(root: Path, lang: str) -> list:
    """Find the files a developer would run first."""
    candidates = []

    patterns = {
        "Python": ["main.py", "app.py", "server.py", "run.py", "cli.py",
                   "__main__.py", "manage.py", "wsgi.py", "asgi.py"],
        "JavaScript": ["index.js", "server.js", "app.js", "main.js", "cli.js"],
        "TypeScript": ["index.ts", "server.ts", "app.ts", "main.ts", "cli.ts",
                       "src/index.ts", "src/server.ts", "src/app.ts", "src/main.ts"],
        "Go": ["main.go", "cmd/main.go"],
        "Rust": ["src/main.rs", "src/lib.rs"],
    }

    for name in patterns.get(lang, []):
        p = root / name
        if p.exists():
            candidates.append(str(p.relative_to(root)))

    # Recursively scan conventional entry-point dirs. Go projects in particular
    # use `cmd/<name>/main.go`, which a flat iterdir would miss.
    src_exts = {".py", ".js", ".ts", ".go", ".rs"}
    entry_hints = {"main", "index", "server", "app", "cli", "run", "__main__"}
    for subdir in ("bin", "cmd", "src", "lib"):
        d = root / subdir
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*")):
            if not f.is_file() or f.suffix not in src_exts:
                continue
            if _is_skipped(f):
                continue
            # Depth limit: don't go more than 3 levels under the subdir.
            if len(f.relative_to(d).parts) > 3:
                continue
            if f.stem not in entry_hints and subdir not in ("bin", "cmd"):
                # For generic src/lib, only keep well-known entry-point names.
                continue
            rel = str(f.relative_to(root))
            if rel not in candidates:
                candidates.append(rel)

    return candidates[:MAX_ENTRY_POINTS]


# ── Python API surface extraction ─────────────────────────────────────────────

def extract_python_api(root: Path) -> list:
    """Extract public functions and classes from Python source files.

    Note: methods defined inside a class are reported under the class's
    ``public_methods`` list — they are **not** also emitted as standalone
    ``function`` entries.
    """
    api = []
    py_files = list(_iter_source_files(
        root, {".py"}, limit=MAX_FILES_SCANNED, exclude_tests_lang="Python",
    ))[:20]

    for fpath in py_files:
        content = read_safe(fpath)
        if not content:
            continue
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        rel = str(fpath.relative_to(root))
        # Walk only module-level nodes so class methods are not re-emitted as
        # free functions. For each class, collect its own public methods.
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                docstring = ast.get_docstring(node) or ""
                args = [a.arg for a in node.args.args if a.arg != "self"]
                api.append({
                    "file": rel,
                    "type": "function",
                    "name": node.name,
                    "args": args,
                    "docstring": docstring[:120] if docstring else "",
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                })
            elif isinstance(node, ast.ClassDef):
                if node.name.startswith("_"):
                    continue
                docstring = ast.get_docstring(node) or ""
                methods = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not n.name.startswith("_")
                ]
                api.append({
                    "file": rel,
                    "type": "class",
                    "name": node.name,
                    "docstring": docstring[:120] if docstring else "",
                    "public_methods": methods[:10],
                })

    return api[:MAX_API_SYMBOLS]


# ── JS/TS API surface extraction ──────────────────────────────────────────────

def extract_js_api(root: Path) -> list:
    """Extract exported symbols from JS/TS source files using regex."""
    api = []
    exts = {".js", ".ts", ".jsx", ".tsx"}
    files = [
        f for f in _iter_source_files(
            root, exts, limit=MAX_FILES_SCANNED, exclude_tests_lang="TypeScript",
        )
        if ".d.ts" not in f.name
    ][:20]

    for fpath in files:
        content = read_safe(fpath)
        rel = str(fpath.relative_to(root))
        # Named exports: export function foo, export class Bar, export const baz
        for m in re.finditer(
            r"export\s+(?:async\s+)?(?:function|class|const|let|var)\s+(\w+)",
            content,
        ):
            api.append({"file": rel, "name": m.group(1), "type": "export"})
        # Default export
        if re.search(r"export\s+default\s+", content):
            api.append({"file": rel, "name": "default", "type": "default-export"})

    return api[:MAX_API_SYMBOLS]


# ── Go API surface extraction ─────────────────────────────────────────────────

def extract_go_api(root: Path) -> list:
    api = []
    go_files = list(_iter_source_files(
        root, {".go"}, limit=MAX_FILES_SCANNED, exclude_tests_lang="Go",
    ))[:20]
    for fpath in go_files:
        content = read_safe(fpath)
        rel = str(fpath.relative_to(root))
        # Exported functions (start with uppercase)
        for m in re.finditer(r"^func\s+([A-Z]\w*)\s*\(", content, re.MULTILINE):
            api.append({"file": rel, "name": m.group(1), "type": "function"})
        # Exported types
        for m in re.finditer(r"^type\s+([A-Z]\w*)\s+(?:struct|interface)", content, re.MULTILINE):
            api.append({"file": rel, "name": m.group(1), "type": "type"})
    return api[:MAX_API_SYMBOLS]


# Registry used by main() to dispatch to the right extractor per language.
API_EXTRACTORS = {
    "Python":     extract_python_api,
    "JavaScript": extract_js_api,
    "TypeScript": extract_js_api,
    "Go":         extract_go_api,
}


# ── HTTP route detection ──────────────────────────────────────────────────────

def extract_routes(root: Path, lang: str) -> list:
    routes = []
    patterns = {
        "Python": [
            (r'@(?:app|router)\.(?:get|post|put|patch|delete)\(["\']([^"\']+)', "decorator"),
            (r'(?:app|router)\.(?:add_api_route|route)\(["\']([^"\']+)', "method"),
        ],
        "JavaScript": [
            (r'(?:app|router)\.(?:get|post|put|patch|delete)\(["\']([^"\']+)', "express"),
        ],
        "TypeScript": [
            (r'(?:app|router)\.(?:get|post|put|patch|delete)\(["\']([^"\']+)', "express"),
            (r'@(?:Get|Post|Put|Patch|Delete)\(["\']([^"\']+)', "nestjs"),
        ],
        "Go": [
            (r'(?:http\.Handle|r\.(?:GET|POST|PUT|PATCH|DELETE))\(["\']([^"\']+)', "stdlib/chi"),
        ],
    }
    lang_patterns = patterns.get(lang, [])
    if not lang_patterns:
        return routes

    src_exts = {
        "Python": {".py"},
        "JavaScript": {".js", ".jsx"},
        "TypeScript": {".ts", ".tsx"},
        "Go": {".go"},
    }.get(lang, set())

    for fpath in _iter_source_files(root, src_exts, limit=80):
        content = read_safe(fpath)
        for pattern, style in lang_patterns:
            for m in re.finditer(pattern, content):
                routes.append({"path": m.group(1), "style": style,
                                "file": str(fpath.relative_to(root))})
    return routes[:MAX_ROUTES]


# ── CLI flag detection ────────────────────────────────────────────────────────

def extract_cli_flags(root: Path, lang: str) -> list:
    flags = []

    if lang == "Python":
        # Filter first (so the 15-file budget isn't eaten by irrelevant paths),
        # then slice. Use AST to reliably parse add_argument calls.
        for fpath in list(_iter_source_files(root, {".py"}, limit=MAX_FILES_SCANNED))[:15]:
            content = read_safe(fpath)
            if "add_argument" not in content:
                continue
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and
                        isinstance(node.func, ast.Attribute) and
                        node.func.attr == "add_argument"):
                    continue
                # First positional arg is the flag name
                flag_name = ""
                if node.args:
                    first = node.args[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        flag_name = first.value
                if not flag_name:
                    continue
                # Look for help= keyword
                help_text = ""
                for kw in node.keywords:
                    if kw.arg == "help" and isinstance(kw.value, ast.Constant):
                        help_text = str(kw.value.value)
                        break
                flags.append({"flag": flag_name, "help": help_text})

    elif lang in ("JavaScript", "TypeScript"):
        content_all = ""
        js_exts = {".js", ".ts", ".jsx", ".tsx"}
        for fpath in list(_iter_source_files(root, js_exts, limit=MAX_FILES_SCANNED))[:20]:
            content_all += read_safe(fpath)
        for m in re.finditer(
            r'\.option\(["\'](-{1,2}[\w, <>\[\]]+)["\'](?:\s*,\s*["\']([^"\']*))?\)?',
            content_all,
        ):
            flags.append({"flag": m.group(1).split(",")[0].strip(),
                           "help": (m.group(2) or "").strip()})

    elif lang == "Go":
        content_all = ""
        for fpath in list(_iter_source_files(root, {".go"}, limit=MAX_FILES_SCANNED))[:15]:
            content_all += read_safe(fpath)
        for m in re.finditer(
            r'flag\.(?:String|Bool|Int|Float64)\(["\'](\w+)["\'],\s*[^,]+,\s*["\']([^"\']*)',
            content_all,
        ):
            flags.append({"flag": f"--{m.group(1)}", "help": m.group(2).strip()})

    return flags[:MAX_CLI_FLAGS]


# ── Environment variable extraction ──────────────────────────────────────────

# Matches os.environ.get("FOO"), os.getenv("FOO"), os.Getenv("FOO"),
# ENV.fetch("FOO"), ENV["FOO"], process.env("FOO"), process.env.FOO, and
# process.env["FOO"] / process.env['FOO'].
_ENV_PATTERN = re.compile(
    r"""(?:
            (?:os\.environ(?:\.get)?|os\.getenv|os\.Getenv|ENV\.fetch)
            \s*\(?\s*["']([A-Z_][A-Z0-9_]*)["']
          |
            os\.environ\s*\[\s*["']([A-Z_][A-Z0-9_]*)["']
          |
            ENV\s*\[\s*["']([A-Z_][A-Z0-9_]*)["']
          |
            process\.env\s*\(\s*["']([A-Z_][A-Z0-9_]*)["']
          |
            process\.env\s*\[\s*["']([A-Z_][A-Z0-9_]*)["']
          |
            process\.env\.([A-Z_][A-Z0-9_]*)
        )""",
    re.VERBOSE,
)


def extract_env_vars(root: Path) -> list:
    vars_found = {}

    # .env.example / .env.sample / .env.template
    for env_file in [".env.example", ".env.sample", ".env.template", ".env.defaults"]:
        content = read_safe(root / env_file)
        if content:
            for raw_line in content.splitlines():
                stripped = raw_line.strip()
                if stripped.startswith("#") or not stripped:
                    continue
                m = re.match(r"^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)", stripped)
                if m:
                    key, default = m.group(1), m.group(2).strip().strip('"\'')
                    # Strip trailing inline comments (e.g. FOO=bar # description)
                    default = re.sub(r"\s+#.*$", "", default).strip()
                    vars_found[key] = {
                        "key": key,
                        "required": not bool(default),
                        "default": default or None,
                        "description": "",
                    }

    # Scan source files for env-var access patterns across the common langs.
    exts = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rb"}
    for f in _iter_source_files(root, exts, limit=MAX_FILES_SCANNED):
        content = read_safe(f)
        for m in _ENV_PATTERN.finditer(content):
            key = next((g for g in m.groups() if g), None)
            if key and key not in vars_found:
                vars_found[key] = {"key": key, "required": True,
                                   "default": None, "description": ""}

    return list(vars_found.values())[:MAX_ENV_VARS]


# ── Dependency purpose extraction ─────────────────────────────────────────────

KNOWN_DEPS = {
    # JS / TS
    "express": "HTTP server framework",
    "fastify": "HTTP server framework",
    "next": "React framework with SSR",
    "react": "UI component library",
    "vue": "UI component library",
    "axios": "HTTP client",
    "prisma": "ORM / database client",
    "typeorm": "ORM",
    "mongoose": "MongoDB ODM",
    "pg": "PostgreSQL client",
    "ioredis": "Redis client",
    "jsonwebtoken": "JWT authentication",
    "zod": "Schema validation",
    "dotenv": "Environment variable loading",
    "winston": "Logging",
    "pino": "Logging",
    # Python
    "fastapi": "HTTP API framework",
    "flask": "HTTP web framework",
    "django": "Full-stack web framework",
    "sqlalchemy": "ORM / database toolkit",
    "pydantic": "Data validation",
    "httpx": "HTTP client",
    "requests": "HTTP client",
    "celery": "Task queue",
    "redis": "Redis client",
    "boto3": "AWS SDK",
    "openai": "OpenAI API client",
    "langchain": "LLM orchestration",
    # Go
    "gin": "HTTP web framework",
    "echo": "HTTP web framework",
    "chi": "HTTP router",
    "gorm": "ORM",
    "cobra": "CLI framework",
}


def _parse_pyproject_deps(content: str):
    """
    Return the set of top-level dependency package names declared in a
    pyproject.toml. Handles both ``[project] dependencies`` and
    ``[tool.poetry.dependencies]`` styles without a TOML parser.
    """
    names = set()

    # [project]-style ``dependencies = [...]`` blocks. Walk line-by-line so
    # that package extras like ``pydantic[email]`` don't fool a naive regex
    # that treats the first ``]`` as the end of the list.
    in_list = False
    list_marker_re = re.compile(r'(?:^|\b)(?:dependencies|optional-dependencies'
                                r'|dev-dependencies)\s*=\s*\[')
    for raw in content.splitlines():
        stripped = raw.strip()
        if not in_list:
            if list_marker_re.search(stripped):
                in_list = True
                # Strip the "foo = [" prefix so the same line's first spec is
                # still considered.
                stripped = stripped.split("[", 1)[1]
            else:
                continue
        # Inside a list — end on a line whose first non-space char is ``]``.
        if stripped.startswith("]"):
            in_list = False
            continue
        for item in re.findall(r'["\']([^"\']+)["\']', stripped):
            pkg = re.split(r"[>=<!;~\[\s]", item.strip(), maxsplit=1)[0].lower()
            if pkg:
                names.add(pkg)

    # [tool.poetry.dependencies] style — lines like `fastapi = "^0.110"`.
    in_poetry = False
    for raw in content.splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_poetry = line.startswith("[tool.poetry.dependencies")
            continue
        if in_poetry and "=" in line and not line.startswith("#"):
            name = line.split("=", 1)[0].strip().strip('"').lower()
            if name and name != "python":
                names.add(name)

    return names


def extract_key_deps(root: Path, lang: str) -> list:
    deps = []
    seen = set()

    def _add(name):
        if name in KNOWN_DEPS and name not in seen:
            deps.append({"name": name, "purpose": KNOWN_DEPS[name]})
            seen.add(name)

    if lang in ("JavaScript", "TypeScript") and (root / "package.json").exists():
        pkg = json.loads(read_safe(root / "package.json") or "{}")
        all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        for name in all_deps:
            _add(name)

    elif lang == "Python":
        for req_file in ["requirements.txt", "requirements/base.txt", "requirements/prod.txt"]:
            content = read_safe(root / req_file)
            if content:
                for line in content.splitlines():
                    pkg_name = re.split(r"[>=<!;\[]", line.strip())[0].lower()
                    _add(pkg_name)
        if (root / "pyproject.toml").exists():
            content = read_safe(root / "pyproject.toml")
            for pkg_name in _parse_pyproject_deps(content):
                _add(pkg_name)

    return deps[:MAX_DEPS]


# ── Test file examples ────────────────────────────────────────────────────────

def find_test_examples(root: Path, lang: str) -> list:
    """Return short usage snippets extracted from test files."""
    examples = []
    # Use _iter_source_files (filter-then-slice) so that SKIP_DIR_PARTS directories
    # (build/, dist/, node_modules/, .venv/, etc.) are excluded BEFORE the [:5] budget
    # cap is applied.  Raw rglob()[:5] slices first, which lets skipped dirs starve the
    # budget and hide real test files that appear later in the walk order.
    suffix_map = {
        "Python":     ({".py"},  lambda p: p.name.startswith("test_") or p.name.endswith("_test.py")),
        "JavaScript": ({".js"},  lambda p: ".test." in p.name or ".spec." in p.name),
        "TypeScript": ({".ts"},  lambda p: ".test." in p.name or ".spec." in p.name),
        "Go":         ({".go"},  lambda p: p.name.endswith("_test.go")),
    }
    if lang not in suffix_map:
        return []
    suffixes, is_test = suffix_map[lang]
    candidates = (
        f for f in _iter_source_files(root, suffixes)
        if is_test(f)
    )
    # Collect up to 5 filtered candidates (filter-then-slice).
    fpaths = []
    for f in candidates:
        fpaths.append(f)
        if len(fpaths) >= 5:
            break
    for fpath in fpaths:
        content = read_safe(fpath)
        if not content:
            continue
        # Grab the first 30 non-blank lines as a usage hint
        lines = [l for l in content.splitlines() if l.strip()][:30]
        examples.append({
            "file": str(fpath.relative_to(root)),
            "snippet": "\n".join(lines[:15]),
        })
    return examples[:MAX_TEST_EXAMPLES]


# ── Port detection ────────────────────────────────────────────────────────────

def detect_ports(root: Path) -> list:
    ports = set()
    exts = {".py", ".js", ".jsx", ".ts", ".tsx", ".go"}
    for f in _iter_source_files(root, exts, limit=MAX_FILES_SCANNED):
        content = read_safe(f)
        for m in re.finditer(r'(?:PORT|port)[^\d]*(\d{4,5})', content):
            p = int(m.group(1))
            if 1000 < p < 65535:
                ports.add(p)
    return sorted(ports)[:MAX_PORTS]


# ── Existing docs inventory ───────────────────────────────────────────────────

def inventory_docs(root: Path) -> dict:
    return {
        "has_readme":       (root / "README.md").exists() or (root / "README.rst").exists(),
        "has_license":      (root / "LICENSE").exists() or (root / "LICENSE.md").exists(),
        "has_contributing": (root / "CONTRIBUTING.md").exists(),
        "has_changelog":    (root / "CHANGELOG.md").exists() or (root / "CHANGELOG.rst").exists(),
        "has_docker":       (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists() or (root / "docker-compose.yaml").exists(),
        "has_makefile":     (root / "Makefile").exists(),
        "has_env_example":  any((root / f).exists() for f in [".env.example", ".env.sample", ".env.template"]),
        "has_ci":           (root / ".github" / "workflows").exists() or (root / ".gitlab-ci.yml").exists(),
        "docs_dirs":        [d.name for d in root.iterdir() if d.is_dir() and d.name.lower() in ("docs", "doc", "documentation", "wiki")],
    }


# ── Source directory map ──────────────────────────────────────────────────────

def map_source_dirs(root: Path) -> list:
    dirs = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and d.name not in SKIP_DIR_PARTS and not d.name.startswith("."):
            # Count source files inside
            src_count = sum(
                1 for f in d.rglob("*")
                if f.is_file() and f.suffix in (".py", ".js", ".ts", ".go", ".rs", ".rb", ".java", ".kt")
            )
            dirs.append({"name": d.name, "src_files": src_count})
    return sorted(dirs, key=lambda x: -x["src_files"])[:MAX_SOURCE_DIRS]


# ── Main ──────────────────────────────────────────────────────────────────────

def build_report(root: Path) -> dict:
    """Build the full exploration report for ``root`` (must be a directory)."""
    stack = detect_stack(root)
    lang = stack["language"]

    extractor = API_EXTRACTORS.get(lang)
    api_surface = extractor(root) if extractor else []

    return {
        # Project identity
        "name":            stack["name"],
        "version":         stack["version"],
        "description":     stack["description"],
        "repo_url":        stack.get("repo_url", ""),

        # Stack
        "language":        lang,
        "framework":       stack["framework"],
        "runtime":         stack["runtime"],
        "package_manager": stack["package_manager"],
        "test_runner":     stack["test_runner"],
        "scripts":         stack["scripts"],

        # Code structure
        "entry_points":    find_entry_points(root, lang),
        "source_dirs":     map_source_dirs(root),
        "api_surface":     api_surface,
        "routes":          extract_routes(root, lang),
        "cli_flags":       extract_cli_flags(root, lang),

        # Configuration
        "env_vars":        extract_env_vars(root),
        "ports":           detect_ports(root),
        "key_deps":        extract_key_deps(root, lang),

        # Usage examples from tests
        "test_examples":   find_test_examples(root, lang),

        # Existing docs
        "docs":            inventory_docs(root),
    }


def main():
    target = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not target.exists():
        print(json.dumps({"error": f"Path not found: {target}"}))
        sys.exit(1)

    # The skill advertises `/doc-explorer [directory or file]`. When the user
    # passes a single file, analyse its containing directory — the same report
    # shape is what Step 2 onwards of SKILL.md expects.
    if target.is_file():
        root = target.parent
    else:
        root = target

    output = build_report(root)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
