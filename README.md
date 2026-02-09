# namingpaper

A CLI tool that renames academic PDF papers using AI-extracted metadata.

**Before:** `1-s2.0-S0304405X13000044-main.pdf`

**After:** `Fama and French, (1993, JFE), Common risk factors in the returns....pdf`

## Features

- Extracts metadata (authors, year, journal, title) from PDFs using AI
- Supports multiple AI providers: Claude, OpenAI, Gemini, and Ollama (local)
- **Batch processing** - rename entire directories at once
- **Custom templates** - flexible filename formatting
- Dry-run mode by default for safety
- Copy to output directory (keeps original file)
- Handles filename collisions (skip, increment, or overwrite)
- Common journal abbreviations (JFE, AER, QJE, etc.)

## Installation

```bash
# Using uv (recommended)
uv tool install namingpaper

# Using pipx
pipx install namingpaper

# With optional providers
uv tool install "namingpaper[openai]"    # OpenAI support
uv tool install "namingpaper[gemini]"    # Gemini support
# or with pipx
pipx install "namingpaper[openai]"
pipx install "namingpaper[gemini]"

# Update to latest version
uv tool upgrade namingpaper
# or
pipx upgrade namingpaper

# Or install from source
git clone https://github.com/DanTsai0903/namingpaper.git
cd namingpaper
uv sync
```

## Quick Start

The default provider is Ollama (local, no API key needed). Install it from [ollama.com](https://ollama.com), then pull the required models:

```bash
ollama pull deepseek-ocr
ollama pull llama3.1:8b

# Preview the rename (dry run)
namingpaper rename paper.pdf

# Actually rename the file
namingpaper rename paper.pdf --execute

# Batch rename all PDFs in a directory
namingpaper batch ~/Downloads/papers --execute
```

### Using Cloud Providers

If you want to use Claude, OpenAI, or Gemini instead of local Ollama:

```bash
# Option 1: Set environment variable (temporary, current session only)
export NAMINGPAPER_ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
namingpaper rename paper.pdf -p claude

# Option 2: Add to shell profile (permanent)
# For zsh (macOS default):
echo 'export NAMINGPAPER_ANTHROPIC_API_KEY=sk-ant-api03-xxxxx' >> ~/.zshrc
source ~/.zshrc

# For bash:
echo 'export NAMINGPAPER_ANTHROPIC_API_KEY=sk-ant-api03-xxxxx' >> ~/.bashrc
source ~/.bashrc

# Option 3: Use config file (~/.namingpaper/config.toml)
mkdir -p ~/.namingpaper
cat > ~/.namingpaper/config.toml << EOF
ai_provider = "claude"
anthropic_api_key = "sk-ant-api03-xxxxx"
EOF
```

## Usage

### Rename Command

Rename a single PDF file.

```bash
namingpaper rename <pdf_path> [OPTIONS]

Options:
  -x, --execute              Actually rename (default is dry-run)
  -y, --yes                  Skip confirmation prompt
  -p, --provider TEXT        AI provider (claude, openai, gemini, ollama)
  -m, --model TEXT           Override the default model for the provider
  --ocr-model TEXT           Override Ollama OCR model (default: deepseek-ocr)
  -o, --output-dir DIR       Copy to directory (keeps original)
  -c, --collision STRATEGY   Handle collisions: skip, increment, overwrite
```

### Batch Command

Rename multiple PDF files in a directory.

```bash
namingpaper batch <directory> [OPTIONS]

Options:
  -x, --execute              Actually rename (default is dry-run)
  -y, --yes                  Skip confirmation prompt
  -r, --recursive            Scan subdirectories
  -f, --filter PATTERN       Only process files matching pattern (e.g., '2023*')
  -p, --provider TEXT        AI provider (claude, openai, gemini, ollama)
  -m, --model TEXT           Override the default model for the provider
  --ocr-model TEXT           Override Ollama OCR model (default: deepseek-ocr)
  -t, --template TEXT        Filename template or preset name
  -o, --output-dir DIR       Copy to directory (keeps originals)
  -c, --collision STRATEGY   Handle collisions: skip, increment, overwrite
  --parallel N               Concurrent extractions (default: 1)
  --json                     Output results as JSON
```

### Templates Command

Show available filename templates.

```bash
namingpaper templates
```

## Examples

### Single File

```bash
# Dry run with Ollama (default)
namingpaper rename paper.pdf

# Execute rename
namingpaper rename paper.pdf --execute

# Copy to a different folder (keeps original)
namingpaper rename paper.pdf -o ~/Papers --execute

# Use Claude
namingpaper rename paper.pdf -p claude --execute

# Use OpenAI
namingpaper rename paper.pdf -p openai --execute

# Auto-increment on collision
namingpaper rename paper.pdf -c increment --execute

# Skip confirmation
namingpaper rename paper.pdf -xy
```

### Batch Processing

```bash
# Preview all renames in a directory
namingpaper batch ~/Downloads/papers

# Execute batch rename
namingpaper batch ~/Downloads/papers --execute

# Recursive scan with subdirectories
namingpaper batch ~/Downloads/papers -r --execute

# Filter by pattern (only 2023 papers)
namingpaper batch ~/Downloads/papers -f "2023*" --execute

# Use compact template
namingpaper batch ~/Downloads/papers -t compact --execute

# Custom template
namingpaper batch ~/Downloads/papers -t "{year} - {authors} - {title}" --execute

# Copy to organized folder
namingpaper batch ~/Downloads -o ~/Papers/Organized --execute

# Parallel processing (faster)
namingpaper batch ~/Downloads/papers --parallel 4 --execute

# Output as JSON (for scripting)
namingpaper batch ~/Downloads/papers --json
```

### View Configuration

```bash
namingpaper config --show
```

## Filename Templates

Templates control how the output filename is formatted.

### Preset Templates

| Name | Pattern | Example |
|------|---------|---------|
| `default` | `{authors}, ({year}, {journal}), {title}` | `Fama and French, (1993, JFE), Common risk....pdf` |
| `compact` | `{authors} ({year}) {title}` | `Fama and French (1993) Common risk....pdf` |
| `full` | `{authors}, ({year}, {journal_full}), {title}` | `Fama and French, (1993, Journal of Financial Economics), Common....pdf` |
| `simple` | `{authors}_{year}_{title}` | `Fama and French_1993_Common risk....pdf` |

### Template Placeholders

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{authors}` | Author surnames (comma-separated, "et al" if >3) | `Fama and French` |
| `{authors_full}` | Author full names | `Eugene F. Fama and Kenneth R. French` |
| `{authors_abbrev}` | Surname with initials | `Fama, E. F. and French, K. R.` |
| `{year}` | Publication year | `1993` |
| `{journal}` | Journal abbreviation (or full name if no abbrev) | `JFE` |
| `{journal_abbrev}` | Journal abbreviation only | `JFE` |
| `{journal_full}` | Full journal name | `Journal of Financial Economics` |
| `{title}` | Paper title (truncated) | `Common risk factors in the returns...` |

### Custom Templates

```bash
# Year-first format
namingpaper batch ~/papers -t "{year} - {authors} - {title}"

# Minimal format
namingpaper batch ~/papers -t "{authors} {year}"

# Full journal name
namingpaper batch ~/papers -t "{authors}, ({year}, {journal_full}), {title}"
```

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `NAMINGPAPER_ANTHROPIC_API_KEY` | Anthropic API key (for Claude) |
| `NAMINGPAPER_OPENAI_API_KEY` | OpenAI API key |
| `NAMINGPAPER_GEMINI_API_KEY` | Google Gemini API key |
| `NAMINGPAPER_AI_PROVIDER` | Provider: `ollama` (default), `claude`, `openai`, `gemini` |
| `NAMINGPAPER_MODEL_NAME` | Override default text model for provider |
| `NAMINGPAPER_OLLAMA_OCR_MODEL` | Override Ollama OCR model (default: `deepseek-ocr`) |
| `NAMINGPAPER_OLLAMA_BASE_URL` | Ollama API URL (default: `http://localhost:11434`) |
| `NAMINGPAPER_MAX_AUTHORS` | Max authors before "et al" (default: 3) |
| `NAMINGPAPER_MAX_FILENAME_LENGTH` | Max filename length (default: 200) |

### Config File

Create `~/.namingpaper/config.toml`:

```toml
# Default provider (ollama requires no API key)
ai_provider = "ollama"
ollama_base_url = "http://localhost:11434"
# ollama_ocr_model = "deepseek-ocr"    # Override OCR model
# model_name = "llama3.1:8b"           # Override text model

# Or use cloud providers
# ai_provider = "claude"
# anthropic_api_key = "sk-ant-..."

# Formatting options
max_authors = 3
max_filename_length = 200
```

## AI Providers

### Ollama (Default)

Local LLM, no API key needed. Just have Ollama running.

```bash
# Pull the default models
ollama pull deepseek-ocr      # OCR model (extracts text from images)
ollama pull llama3.1:8b        # Text model (parses metadata)

# Use it (default provider)
namingpaper rename paper.pdf

# Use a different text model
namingpaper rename paper.pdf -m gemma2:9b

# Use a different OCR model
namingpaper rename paper.pdf --ocr-model llava
```

### Claude (included by default)

```bash
export NAMINGPAPER_ANTHROPIC_API_KEY=sk-ant-...
namingpaper rename paper.pdf -p claude

# Use a specific Claude model
namingpaper rename paper.pdf -p claude -m claude-haiku-4-20250514
```

### OpenAI

```bash
uv add "namingpaper[openai]"
export NAMINGPAPER_OPENAI_API_KEY=sk-...
namingpaper rename paper.pdf -p openai

# Use a specific OpenAI model
namingpaper rename paper.pdf -p openai -m gpt-4o-mini
```

### Gemini

```bash
uv add "namingpaper[gemini]"
export NAMINGPAPER_GEMINI_API_KEY=...
namingpaper rename paper.pdf -p gemini

# Use a specific Gemini model
namingpaper rename paper.pdf -p gemini -m gemini-2.0-flash
```

## Development

```bash
# Clone and setup
git clone https://github.com/DanTsai0903/namingpaper.git
cd namingpaper
uv sync --extra dev

# Run tests
uv run pytest -v

# Run a specific test
uv run pytest tests/test_formatter.py -v
```

## License

MIT
