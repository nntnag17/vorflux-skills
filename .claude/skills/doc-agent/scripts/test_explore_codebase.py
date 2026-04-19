"""Smoke tests for explore_codebase.py.

Each test creates a minimal fixture directory representing a language stack,
runs the script against it, and asserts key JSON fields are correct.
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

SCRIPT = Path(__file__).parent / "explore_codebase.py"


def run_script(root: Path) -> dict:
    """Run explore_codebase.py against *root* and return the parsed JSON report."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(root)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Script failed:\n{result.stderr}"
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Python fixture
# ---------------------------------------------------------------------------

def make_python_fixture(tmp: Path) -> Path:
    root = tmp / "py_project"
    root.mkdir()
    (root / "pyproject.toml").write_text(textwrap.dedent("""\
        [project]
        name = "my-lib"
        version = "1.2.3"
        description = "A test library"
        [project.scripts]
        my-cli = "my_lib.cli:main"
    """))
    src = root / "my_lib"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "core.py").write_text(textwrap.dedent("""\
        def public_func(x: int) -> int:
            \"\"\"Return x doubled.\"\"\"
            return x * 2

        def _private(x):
            return x
    """))
    (src / "cli.py").write_text("def main(): pass\n")
    return root


def test_python_stack(tmp_path):
    root = make_python_fixture(tmp_path)
    report = run_script(root)

    assert report["stack"]["language"] == "Python"
    assert report["stack"]["name"] == "my-lib"
    assert report["stack"]["version"] == "1.2.3"
    assert report["stack"]["description"] == "A test library"

    # CLI entrypoint detected from [project.scripts]
    cli = report.get("cli_entrypoints", [])
    assert any("my-cli" in ep.get("command", "") for ep in cli), \
        f"Expected my-cli in cli_entrypoints, got: {cli}"

    # Public API: public_func should appear; _private should not
    api_names = [s["name"] for s in report.get("public_api", [])]
    assert any("public_func" in n for n in api_names), \
        f"Expected public_func in public_api, got: {api_names}"
    assert not any("_private" in n for n in api_names), \
        f"_private should not appear in public_api, got: {api_names}"


# ---------------------------------------------------------------------------
# Go fixture
# ---------------------------------------------------------------------------

def make_go_fixture(tmp: Path) -> Path:
    root = tmp / "go_project"
    root.mkdir()
    (root / "go.mod").write_text("module github.com/example/myapp\n\ngo 1.21\n")
    (root / "main.go").write_text(textwrap.dedent("""\
        package main

        import "fmt"

        // Run starts the application.
        func Run() {
            fmt.Println("hello")
        }

        func main() {
            Run()
        }
    """))
    return root


def test_go_stack(tmp_path):
    root = make_go_fixture(tmp_path)
    report = run_script(root)

    assert report["stack"]["language"] == "Go"

    api_names = [s["name"] for s in report.get("public_api", [])]
    assert any("Run" in n for n in api_names), \
        f"Expected Run in public_api, got: {api_names}"


# ---------------------------------------------------------------------------
# Shell fixture
# ---------------------------------------------------------------------------

def make_shell_fixture(tmp: Path) -> Path:
    root = tmp / "shell_project"
    root.mkdir()
    scripts = root / "Network"
    scripts.mkdir()
    (scripts / "ping.10s.sh").write_text("#!/bin/bash\nping -c 1 google.com\n")
    (root / "README.md").write_text("# Shell project\n")
    return root


def test_shell_stack(tmp_path):
    root = make_shell_fixture(tmp_path)
    report = run_script(root)

    assert report["stack"]["language"] == "Shell"
    # No false-positive env vars from shell scripts
    assert report.get("env_vars", []) == [], \
        f"Shell project should have no env_vars, got: {report.get('env_vars')}"
    # No false-positive ports from shell scripts
    assert report.get("ports", []) == [], \
        f"Shell project should have no ports, got: {report.get('ports')}"


# ---------------------------------------------------------------------------
# audit_docs: has_ci with .github/workflows
# ---------------------------------------------------------------------------

def test_audit_docs_has_ci(tmp_path):
    root = tmp_path / "ci_project"
    root.mkdir()
    (root / "go.mod").write_text("module example.com/ci\n\ngo 1.21\n")
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("on: push\njobs: {}\n")

    report = run_script(root)
    assert report["docs_audit"]["has_ci"] is True, \
        f"Expected has_ci=True when .github/workflows exists, got: {report['docs_audit']}"


# ---------------------------------------------------------------------------
# Render: --render flag produces a README file
# ---------------------------------------------------------------------------

def test_render_flag(tmp_path):
    root = make_python_fixture(tmp_path)
    out_path = tmp_path / "README_out.md"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(root), "--render", str(out_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"--render failed:\n{result.stderr}"
    assert out_path.exists(), "README file was not created"
    content = out_path.read_text()
    assert "my-lib" in content, "README should contain project name"
    assert "## Installation" in content or "## Getting Started" in content, \
        "README should contain installation/getting-started section"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import traceback

    tests = [
        test_python_stack,
        test_go_stack,
        test_shell_stack,
        test_audit_docs_has_ci,
        test_render_flag,
    ]
    passed = 0
    failed = 0
    for test_fn in tests:
        with tempfile.TemporaryDirectory() as d:
            try:
                test_fn(Path(d))
                print(f"  PASS  {test_fn.__name__}")
                passed += 1
            except Exception:
                print(f"  FAIL  {test_fn.__name__}")
                traceback.print_exc()
                failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
