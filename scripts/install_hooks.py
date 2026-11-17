#!/usr/bin/env python3
"""
Install local git hooks (e.g., pre-push) that run scripts/preflight.py.
Git hooks are stored in .git/hooks and are local-only (never committed/pushed).
"""

import sys
from pathlib import Path

HOOK_CONTENT = """#!/bin/sh
# VIGIL pre-push gatekeeper
echo "Running VIGIL preflight check before push..."
# Prefer the repo virtual environment so the hook works without an activated shell.
PY=python
if [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe"; fi
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; fi
"$PY" scripts/preflight.py --quick
if [ $? -ne 0 ]; then
    echo "Preflight check failed! Push aborted."
    exit 1
fi
exit 0
"""


def main():
    git_dir = Path(".git")
    if not git_dir.exists():
        print("Error: .git directory not found. Must be run from repo root.")
        sys.exit(1)

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    pre_push_hook = hooks_dir / "pre-push"
    pre_push_hook.write_text(HOOK_CONTENT, encoding="utf-8")

    # On POSIX or Git Bash, make it executable
    try:
        pre_push_hook.chmod(0o755)
    except Exception:
        pass

    print(f"Successfully installed pre-push hook at {pre_push_hook}")


if __name__ == "__main__":
    main()
