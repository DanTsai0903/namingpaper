# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
