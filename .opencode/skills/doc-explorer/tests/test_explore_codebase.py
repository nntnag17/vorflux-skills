"""Unit tests for explore_codebase.py.

Uses pytest's built-in ``tmp_path`` fixture to build small throwaway project
trees and asserts the key fields of the report. Designed to catch the
specific regressions called out in the review:

- file-mode input (SKILL.md advertises `[directory or file]`)
- JS/TS env-var detection for `process.env.FOO` and `process.env["FOO"]`
- language fallback for source-only directories (no manifest)
- Python class methods must NOT be re-emitted as standalone functions
- word-boundary dependency matching in pyproject.toml
- filter-before-slice so __pycache__ doesn't steal the file budget
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import explore_codebase as ec  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


def _run_script(arg: Path) -> dict:
    """Invoke the CLI exactly as the skill does and parse its JSON output."""
    out = subprocess.check_output(
        [sys.executable, str(SCRIPT_DIR / "explore_codebase.py"), str(arg)],
        text=True,
    )
    return json.loads(out)


# ── Helper-level tests ────────────────────────────────────────────────────────

def test_is_test_file_python():
    assert ec._is_test_file(Path("test_foo.py"), "Python")
    assert ec._is_test_file(Path("foo_test.py"), "Python")
    assert not ec._is_test_file(Path("testimonial.py"), "Python")
    assert not ec._is_test_file(Path("latest.py"), "Python")


def test_is_test_file_js_ts():
    assert ec._is_test_file(Path("a.test.ts"), "TypeScript")
    assert ec._is_test_file(Path("a.spec.js"), "JavaScript")
    assert ec._is_test_file(Path("pkg/__tests__/a.ts"), "TypeScript")
    # Substring-only matches must NOT be flagged as tests.
    assert not ec._is_test_file(Path("testimonial.ts"), "TypeScript")
    assert not ec._is_test_file(Path("latest.ts"), "TypeScript")


def test_is_test_file_go():
    assert ec._is_test_file(Path("foo_test.go"), "Go")
    assert not ec._is_test_file(Path("tester.go"), "Go")


def test_is_skipped_picks_up_subdirs(tmp_path):
    assert ec._is_skipped(tmp_path / "node_modules" / "a.js")
    assert ec._is_skipped(tmp_path / "pkg" / "__pycache__" / "x.pyc")
    assert not ec._is_skipped(tmp_path / "src" / "index.ts")


def test_word_in_avoids_substrings():
    assert ec._word_in("flask", "flask = '^2'")
    assert not ec._word_in("flask", "flask-admin = '^1'")
    assert ec._word_in("redis", "redis = '^4'")
    assert not ec._word_in("redis", "redisearch = '^1'")


def test_parse_pyproject_deps_project_style():
    toml = """
[project]
name = "demo"
dependencies = [
    "fastapi >= 0.100",
    "pydantic[email] ~= 2.0",
    "redis-om == 0.2",
]
"""
    names = ec._parse_pyproject_deps(toml)
    assert "fastapi" in names
    assert "pydantic" in names
    assert "redis-om" in names
    # redis alone must NOT appear just because redis-om mentions it.
    assert "redis" not in names


def test_parse_pyproject_deps_poetry_style():
    toml = """
[tool.poetry.dependencies]
python = "^3.11"
flask = "^3.0"
pydantic-settings = "^2.1"
"""
    names = ec._parse_pyproject_deps(toml)
    assert names == {"flask", "pydantic-settings"}


# ── Python project fixture ────────────────────────────────────────────────────

@pytest.fixture
def python_project(tmp_path):
    root = tmp_path / "pyproj"
    _write(root, "pyproject.toml", (
        '[project]\n'
        'name = "pyproj"\n'
        'version = "1.2.3"\n'
        'description = "demo project"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = ["fastapi >= 0.100", "redis-om == 0.2"]\n'
    ))
    _write(root, "main.py", (
        '"""Entry point."""\n'
        'import os\n'
        'DB_URL = os.environ.get("DATABASE_URL")\n'
        'TOKEN = os.getenv("API_TOKEN", "")\n'
        '\n'
        'def run(port: int = 8000):\n'
        '    """Start the server."""\n'
        '    return port\n'
        '\n'
        'class Client:\n'
        '    def connect(self): pass\n'
        '    def _private(self): pass\n'
        '    async def fetch(self): pass\n'
    ))
    _write(root, "cli.py", (
        "import argparse\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--verbose', help='enable verbose output')\n"
        "p.add_argument('--config', help='config file path')\n"
    ))
    _write(root, ".env.example", "DATABASE_URL=\nLOG_LEVEL=info\n")
    # Dead bytecode directory — must not consume the file-scan budget.
    _write(root, "__pycache__/trash.pyc", "noise")
    return root


def test_python_project_report(python_project):
    report = ec.build_report(python_project)

    assert report["language"] == "Python"
    assert report["name"] == "pyproj"
    assert report["version"] == "1.2.3"
    assert report["runtime"] == "Python >=3.10"
    assert report["framework"] == "FastAPI"  # from pyproject.toml dependencies

    # Entry points includes main.py and cli.py (cli is a conventional name).
    assert "main.py" in report["entry_points"]
    assert "cli.py" in report["entry_points"]

    # Env vars: from .env.example AND from os.environ/os.getenv usage.
    keys = {v["key"] for v in report["env_vars"]}
    assert "DATABASE_URL" in keys
    assert "API_TOKEN" in keys
    assert "LOG_LEVEL" in keys

    # CLI flags extracted via AST.
    flag_names = {f["flag"] for f in report["cli_flags"]}
    assert "--verbose" in flag_names
    assert "--config" in flag_names

    # API surface: class methods must NOT be emitted as standalone functions.
    api = report["api_surface"]
    client = next(e for e in api if e["type"] == "class" and e["name"] == "Client")
    # Public methods only — private `_private` is excluded.
    assert set(client["public_methods"]) == {"connect", "fetch"}
    # `connect` should appear only as a class method, never at module level.
    top_level_functions = {e["name"] for e in api if e["type"] == "function"}
    assert "connect" not in top_level_functions
    assert "fetch" not in top_level_functions
    # `run` IS a top-level function, so it must appear.
    assert "run" in top_level_functions


def test_python_project_key_deps_word_boundary(python_project):
    report = ec.build_report(python_project)
    dep_names = {d["name"] for d in report["key_deps"]}
    assert "fastapi" in dep_names
    # `redis` must NOT be inferred from `redis-om`.
    assert "redis" not in dep_names


# ── JS/TS project fixture (env-var detection regression) ─────────────────────

def test_js_env_vars_process_env_forms(tmp_path):
    root = tmp_path / "jsproj"
    _write(root, "package.json", json.dumps({
        "name": "jsproj",
        "version": "0.1.0",
        "dependencies": {"express": "^4", "pg": "^8"},
    }))
    _write(root, "index.js", (
        "const port = process.env.PORT || 3000;\n"
        "const token = process.env['API_TOKEN'];\n"
        "const db = process.env[\"DATABASE_URL\"];\n"
    ))
    report = ec.build_report(root)

    assert report["language"] == "JavaScript"
    keys = {v["key"] for v in report["env_vars"]}
    # All three access forms must be detected.
    assert "PORT" in keys
    assert "API_TOKEN" in keys
    assert "DATABASE_URL" in keys

    dep_names = {d["name"] for d in report["key_deps"]}
    assert "express" in dep_names
    assert "pg" in dep_names


def test_ts_excludes_test_files_not_substrings(tmp_path):
    root = tmp_path / "tsproj"
    _write(root, "package.json", json.dumps({"name": "tsproj", "version": "0.1.0"}))
    _write(root, "tsconfig.json", "{}")
    _write(root, "src/testimonial.ts", "export const testimonial = 1;\n")
    _write(root, "src/api.test.ts", "export const internal = 2;\n")
    report = ec.build_report(root)

    assert report["language"] == "TypeScript"
    names = {e["name"] for e in report["api_surface"]}
    # testimonial.ts is NOT a test file — its export must be surfaced.
    assert "testimonial" in names
    # api.test.ts IS a test file — it must be excluded.
    assert "internal" not in names


# ── Go project fixture (nested cmd/<name>/main.go entry point) ────────────────

def test_go_nested_cmd_entrypoint(tmp_path):
    root = tmp_path / "goproj"
    _write(root, "go.mod", "module example.com/tool\n\ngo 1.21\n")
    _write(root, "cmd/tool/main.go", (
        "package main\n"
        "import \"os\"\n"
        "func main() {\n"
        "  _ = os.Getenv(\"TOOL_TOKEN\")\n"
        "}\n"
        "func Helper() {}\n"
    ))
    report = ec.build_report(root)

    assert report["language"] == "Go"
    # The recursive cmd/ scan must surface the nested main.go.
    assert any(ep.endswith("main.go") for ep in report["entry_points"]), \
        f"expected a main.go entry point, got {report['entry_points']}"

    env_keys = {v["key"] for v in report["env_vars"]}
    assert "TOOL_TOKEN" in env_keys

    api_names = {e["name"] for e in report["api_surface"]}
    assert "Helper" in api_names


# ── Source-only (no manifest) fallback ───────────────────────────────────────

def test_language_fallback_for_source_only_dir(tmp_path):
    root = tmp_path / "bare"
    _write(root, "main.py", (
        "def greet(name):\n"
        "    return f'hello {name}'\n"
    ))
    report = ec.build_report(root)

    # Even without pyproject.toml/requirements.txt, language must fall back.
    assert report["language"] == "Python"
    assert "main.py" in report["entry_points"]
    names = {e["name"] for e in report["api_surface"] if e["type"] == "function"}
    assert "greet" in names


# ── CLI file-mode (SKILL.md advertises `[directory or file]`) ────────────────

def test_cli_accepts_file_path(tmp_path):
    """Running the CLI against a file must not crash; it analyses parent dir."""
    root = tmp_path / "pkg"
    _write(root, "pyproject.toml", '[project]\nname = "pkg"\nversion = "0.1"\n')
    file_arg = _write(root, "main.py", "def go(): return 1\n")

    report = _run_script(file_arg)
    assert report["language"] == "Python"
    assert report["name"] == "pkg"


def test_cli_accepts_directory(tmp_path):
    root = tmp_path / "pkg"
    _write(root, "pyproject.toml", '[project]\nname = "pkg"\nversion = "0.1"\n')
    report = _run_script(root)
    assert report["language"] == "Python"
    assert report["name"] == "pkg"


def test_cli_missing_path_exits_nonzero(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "explore_codebase.py"),
         str(tmp_path / "does_not_exist")],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert "error" in payload


# ── find_test_examples: filter-before-slice regression ───────────────────────

def test_find_test_examples_skipped_dir_does_not_starve_budget(tmp_path):
    """
    Regression: find_test_examples previously used rglob()[:5] (slice-before-filter).
    If the first 5 filesystem hits were all inside a SKIP_DIR_PARTS directory
    (e.g. build/, dist/, node_modules/) the budget was exhausted before _is_skipped
    could exclude them, and real test files later in the walk were silently dropped.

    The fix routes through _iter_source_files (filter-then-slice), matching every
    other extractor in the module.
    """
    root = tmp_path / "proj"

    # 'build' is in SKIP_DIR_PARTS and sorts before 'src' alphabetically,
    # so rglob visits it first — filling the old [:5] budget with noise.
    build_dir = root / "build"
    build_dir.mkdir(parents=True)
    for i in range(5):
        _write(root, f"build/test_noise{i}.py", f"def test_noise_{i}(): pass\n")

    # The one real test we want back.
    _write(root, "src/test_real.py", "def test_business_logic(): assert 2 + 2 == 4\n")

    examples = ec.find_test_examples(root, "Python")
    files = [e["file"] for e in examples]

    assert "src/test_real.py" in files, (
        f"real test file was not returned (budget starved by build/): {files}"
    )
    assert not any("build" in f for f in files), (
        f"build/ noise leaked into results: {files}"
    )


def test_find_test_examples_js_skipped_node_modules(tmp_path):
    """Same budget-starvation regression for JavaScript / node_modules."""
    root = tmp_path / "jsproj"

    nm = root / "node_modules" / "somepkg"
    nm.mkdir(parents=True)
    for i in range(5):
        _write(root, f"node_modules/somepkg/comp{i}.test.js",
               f"test('noise {i}', () => {{}});\n")

    _write(root, "src/app.test.js",
           "test('works', () => expect(1).toBe(1));\n")

    examples = ec.find_test_examples(root, "JavaScript")
    files = [e["file"] for e in examples]

    assert "src/app.test.js" in files, (
        f"real JS test not returned (budget starved by node_modules): {files}"
    )
    assert not any("node_modules" in f for f in files), (
        f"node_modules noise leaked: {files}"
    )
