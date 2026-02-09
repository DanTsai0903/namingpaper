# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

## Project Overview

**namingpaper** is a CLI tool that renames academic PDF files using AI-extracted metadata. It converts filenames like `1-s2.0-S0304405X13000044-main.pdf` into `Fama and French, (1993, JFE), Common risk factors in the returns....pdf`.

## Commands

```bash
# Install dependencies
uv sync --all-extras --dev

# Run tests
uv run pytest
uv run pytest tests/test_formatter.py -v                          # single file
uv run pytest tests/test_formatter.py::TestBuildFilename::test_standard_format -v  # single test

# Run the CLI
uv run namingpaper rename <file.pdf>
uv run namingpaper batch <directory>

# Build
uv build
```

Tests use `pytest-asyncio` with `asyncio_mode = "auto"`.

## Architecture

**Pipeline:** PDF → `pdf_reader.py` (text/image extraction) → `extractor.py` (orchestration) → AI Provider → `formatter.py`/`template.py` (filename generation) → `renamer.py` (safe file ops)

**Provider pattern:** Abstract `AIProvider` in `providers/base.py` with implementations for Claude, OpenAI, Gemini, and Ollama. Factory function `get_provider()` in `providers/__init__.py`. Ollama is the default (no API key needed), using a two-stage approach: `deepseek-ocr` for OCR then a text model for metadata parsing.

**Key models** (`models.py`): `PaperMetadata` (authors, year, journal, title, confidence), `PDFContent`, `RenameOperation`, `BatchItem`/`BatchResult`.

**Template system:** Presets (default, compact, full, simple) with placeholders like `{authors}`, `{year}`, `{journal}`, `{title}`.

**Safety:** Dry-run by default (requires `--execute`), collision strategies (skip/increment/overwrite), confidence threshold filtering.

**Config priority:** CLI args > env vars (`NAMINGPAPER_*`) > config file (`~/.namingpaper/config.toml`) > defaults. Managed via Pydantic Settings in `config.py`.

## Release Procedure

1. Bump version in both `pyproject.toml` and `src/namingpaper/__init__.py`
2. Commit and push: `git add -A && git commit -m "Bump version to X.Y.Z" && git push origin main`
3. Create GitHub release: `gh release create vX.Y.Z --title "vX.Y.Z" --prerelease --notes "..."`
   - Drop `--prerelease` for stable releases
4. Build and publish to PyPI:
   ```bash
   uv build
   source .env  # contains UV_PUBLISH_TOKEN
   uv publish --token "$UV_PUBLISH_TOKEN"
   ```
5. Clean old dists if needed: `rm -rf dist/` before building to avoid uploading stale files

## uv Rules

This project uses **uv** as its Python package and project manager.

- **Add dependency**: `uv add <package>` (or `uv add --dev <package>`)
- **Remove**: `uv remove <package>`
- **Never** edit `pyproject.toml` dependencies by hand — always use `uv add`/`uv remove` so the lockfile stays in sync.
- **Run**: `uv run <command>` — do **not** use `pip install` or `python -m pip`.
- **Lockfile**: `uv.lock` is auto-managed. Do not manually edit it. Use `uv sync --locked` in CI.
