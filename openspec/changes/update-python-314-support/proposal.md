# Change: Add Python 3.14 support

## Why
The project currently restricts Python to `>=3.11,<3.14` in `pyproject.toml`, excluding Python 3.14. PyMuPDF (the main native dependency) uses the Python Stable ABI targeting 3.10+, so it is already compatible. All other dependencies (typer, rich, pydantic, ollama, etc.) are pure-Python or have broad version support. There is no technical blocker.

## What Changes
- Update `requires-python` in `pyproject.toml` from `>=3.11,<3.14` to `>=3.11`
- Regenerate `uv.lock` to reflect the new constraint
- Verify tests pass (no Python 3.14 deprecation issues)

## Impact
- Affected code: `pyproject.toml`, `uv.lock`
- No spec changes — this is a packaging/config update
- Risk: minimal — all key dependencies already support Python 3.14 via stable ABI or pure Python
