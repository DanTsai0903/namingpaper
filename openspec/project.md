# Project Context

## Purpose
A CLI tool that renames academic paper files (typically PDFs) to a standardized
format:

```
author names_(year, journal abbrev)_topic.ext
```

Examples:
- `Smith, Wang_(2023, JFE)_Asset pricing anomalies.pdf`
- `Fama, French_(1993, JFE)_Common risk factors in stock returns.pdf`

The tool can process a single file or batch-rename all papers in a folder.

## Tech Stack
- **Python 3.14** — language runtime
- **uv** — package management and virtual-env tooling
- **Pytest** — test framework
- Standard library for file I/O; potentially external libs for PDF metadata or
  API lookups (TBD)

## Project Conventions

### Code Style
- PEP 8 throughout
- Type hints on all public functions and class signatures
- One clear responsibility per module — keep files focused and small

### Architecture Patterns
- `main.py` is the CLI entry point; subcommands added as the tool grows
- Core logic separated from CLI:
  - **pdf_reader** — extracts text or renders pages from PDFs
  - **ai_provider** — abstract interface with implementations for Claude/OpenAI/Gemini
  - **extractor** — sends PDF content to AI, parses structured response
  - **formatter** — builds the canonical filename string from metadata
  - **renamer** — performs the actual filesystem rename with safety checks
- Config stored in `~/.namingpaper/config.toml` or env vars for API keys

### Testing Strategy
- Pytest as the single test framework
- Tests live in a top-level `tests/` directory
- All filesystem operations in tests use `tmp_path` fixtures — never touch real
  user directories
- Unit tests cover naming-rule evaluation; integration tests cover full
  CLI round-trips (dry-run and live)

### Git Workflow
- Feature branches off `main`
- Squash or rebase before merging — keep history linear
- Use OpenSpec proposals for any new capability, breaking change, or
  architectural shift before coding begins

## Domain Context
The core domain is **academic paper metadata**:

- **Authors** — one or more author surnames, comma-separated
- **Year** — publication year (4 digits)
- **Journal abbreviation** — standard short form (e.g., JFE, RFS, AER, QJE)
- **Topic** — a short descriptive title or the paper's actual title

### Metadata source (MVP)
**AI-powered extraction** — extract text/images from the PDF (title page,
abstract, headers) and send to an AI API to identify:
- Author names
- Publication year
- Journal name (and derive abbreviation)
- Paper topic/title

The tool supports multiple AI providers (Claude, OpenAI, Gemini) via a
configurable backend. User selects their provider and supplies an API key.

Workflow:
1. Extract content from PDF (text or render first page as image)
2. Send to AI with a structured prompt asking for the fields
3. Parse AI response into metadata struct
4. Let user confirm/edit before renaming

Fallback: if AI extraction fails or user has no API key, prompt for manual entry.

## Important Constraints
- **Safe by default** — never overwrite a file without explicit confirmation or
  a `--dry-run` flag showing the planned changes first
- **Collision-aware** — if a rename would collide with an existing file, warn
  and skip (or offer an auto-increment strategy)
- **Cross-platform paths** — must handle macOS, Linux, and Windows path
  conventions correctly
- Symlinks should be reported but not silently followed during a rename

## External Dependencies

**Required:**
- **pypdf** or **pdfplumber** — for extracting text from PDFs
- **pdf2image** + **Pillow** — for rendering PDF pages as images (if using
  vision models)

**AI providers (user installs one or more):**
- **anthropic** — Claude API client
- **openai** — OpenAI API client
- **google-generativeai** — Gemini API client

**Future/optional:**
- **httpx** — for API calls to CrossRef/Semantic Scholar
- **click** or **typer** — for richer CLI (or stick with argparse from stdlib)

## Configuration
The tool needs:
- **AI provider selection** — which backend to use (claude/openai/gemini)
- **API key** — stored in env var or config file (never committed to repo)
- **Journal abbreviation mappings** — optional lookup table for full name → abbrev
