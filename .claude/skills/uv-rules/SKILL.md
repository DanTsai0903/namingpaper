---
name: uv-rules
description: Rules and guidelines for using uv as the Python package manager in this project. Use when managing dependencies, running commands, or troubleshooting the venv.
metadata:
  author: namingpaper
  version: "1.0"
---

# uv Rules

This project uses **uv** as its Python package and project manager. Follow these rules strictly.

## Commands

- **Add dependency**: `uv add <package>` (or `uv add --dev <package>`)
- **Remove dependency**: `uv remove <package>`
- **Run commands**: `uv run <command>`
- **Install dependencies**: `uv sync --all-extras --dev`
- **CI lockfile check**: `uv sync --locked`

## Rules

- **Never** edit `pyproject.toml` dependencies by hand — always use `uv add`/`uv remove` so the lockfile stays in sync.
- **Never** use `pip install`, `python -m pip`, or `uv pip`. Mixing `uv pip` with `uv sync` corrupts the editable install and breaks the venv.
- `uv.lock` is auto-managed. Do not manually edit it.
- **If the venv breaks**: `rm -rf .venv && uv sync --all-extras --dev` to recreate from scratch.
