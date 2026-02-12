"""CLI entry point for namingpaper."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from namingpaper.config import get_settings
from namingpaper.extractor import plan_rename_sync
from namingpaper.models import BatchItem, BatchItemStatus, LowConfidenceError
from namingpaper.renamer import (
    CollisionStrategy,
    execute_rename,
    preview_rename,
    check_collision,
)

app = typer.Typer(
    name="namingpaper",
    help="Rename academic papers using AI-extracted metadata.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def rename(
    pdf_path: Annotated[
        Path,
        typer.Argument(
            help="Path to the PDF file to rename",
            exists=True,
            dir_okay=False,
            resolve_path=True,
        ),
    ],
    execute: Annotated[
        bool,
        typer.Option(
            "--execute",
            "-x",
            help="Actually rename the file (default is dry-run)",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Skip confirmation prompt",
        ),
    ] = False,
    provider: Annotated[
        str | None,
        typer.Option(
            "--provider",
            "-p",
            help="AI provider to use (claude, openai, gemini, ollama)",
        ),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="Override the default model for the provider",
        ),
    ] = None,
    ocr_model: Annotated[
        str | None,
        typer.Option(
            "--ocr-model",
            help="Override Ollama OCR model (default: deepseek-ocr)",
        ),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            "-o",
            help="Copy renamed file to this directory (keeps original)",
            exists=True,
            file_okay=False,
            resolve_path=True,
        ),
    ] = None,
    template: Annotated[
        str | None,
        typer.Option(
            "--template",
            "-t",
            help="Filename template or preset (default, compact, full, simple)",
        ),
    ] = None,
    collision: Annotated[
        CollisionStrategy,
        typer.Option(
            "--collision",
            "-c",
            help="How to handle filename collisions",
        ),
    ] = CollisionStrategy.SKIP,
) -> None:
    """Rename a PDF file based on AI-extracted metadata.

    By default, runs in dry-run mode showing what would happen.
    Use --execute to actually rename the file.
    """
    # Check file extension
    if pdf_path.suffix.lower() != ".pdf":
        console.print(f"[red]Error:[/red] File must be a PDF: {pdf_path}")
        raise typer.Exit(1)

    # Validate template if provided
    if template:
        from namingpaper.template import validate_template, get_template
        template_str = get_template(template)
        is_valid, error = validate_template(template_str)
        if not is_valid:
            console.print(f"[red]Invalid template:[/red] {error}")
            raise typer.Exit(1)

    # Extract metadata and plan rename
    with console.status("[bold blue]Extracting metadata..."):
        try:
            operation = plan_rename_sync(pdf_path, provider_name=provider, model_name=model, ocr_model=ocr_model, keep_alive="0s")
        except LowConfidenceError as e:
            console.print(
                f"[yellow]Skipped:[/yellow] {e}"
            )
            raise typer.Exit(2)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error extracting metadata:[/red] {e}")
            raise typer.Exit(1)

    # Apply template if provided
    if template:
        from namingpaper.template import build_filename_from_template
        filename = build_filename_from_template(operation.metadata, template)
        operation.destination = pdf_path.parent / filename

    # If output_dir specified, update destination to that directory
    copy_mode = output_dir is not None
    if output_dir:
        operation.destination = output_dir / operation.destination.name

    # Display metadata
    metadata = operation.metadata
    table = Table(title="Extracted Metadata", show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("Authors", ", ".join(metadata.authors))
    table.add_row("Year", str(metadata.year))
    table.add_row("Journal", metadata.journal)
    if metadata.journal_abbrev:
        table.add_row("Abbreviation", metadata.journal_abbrev)
    table.add_row("Title", metadata.title)
    table.add_row("Confidence", f"{metadata.confidence:.0%}")

    console.print(table)
    console.print()

    # Show planned rename
    preview = preview_rename(operation, copy=copy_mode)
    title = "Planned Copy" if copy_mode else "Planned Rename"
    console.print(Panel(preview, title=title, border_style="blue"))

    # Check for collision
    if check_collision(operation.destination):
        console.print(
            f"[yellow]Warning:[/yellow] Destination exists. "
            f"Strategy: [bold]{collision.value}[/bold]"
        )

    # Dry run mode
    if not execute:
        console.print()
        action = "copy" if copy_mode else "rename"
        console.print(f"[dim]Dry run mode. Use --execute to {action}.[/dim]")
        return

    # Confirm
    if not yes:
        action = "copy" if copy_mode else "rename"
        confirmed = typer.confirm(f"Proceed with {action}?")
        if not confirmed:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    # Execute rename/copy
    result = execute_rename(operation, collision_strategy=collision, copy=copy_mode)

    if result is None:
        console.print("[yellow]Skipped:[/yellow] File already exists.")
    elif copy_mode:
        console.print(f"[green]Copied to:[/green] {result}")
    else:
        console.print(f"[green]Renamed to:[/green] {result}")


@app.command()
def batch(
    directory: Annotated[
        Path,
        typer.Argument(
            help="Directory containing PDF files to process",
            exists=True,
            file_okay=False,
            resolve_path=True,
        ),
    ],
    execute: Annotated[
        bool,
        typer.Option(
            "--execute",
            "-x",
            help="Actually rename files (default is dry-run)",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Skip confirmation prompt",
        ),
    ] = False,
    recursive: Annotated[
        bool,
        typer.Option(
            "--recursive",
            "-r",
            help="Scan subdirectories for PDF files",
        ),
    ] = False,
    filter_pattern: Annotated[
        str | None,
        typer.Option(
            "--filter",
            "-f",
            help="Only process files matching this pattern (e.g., '2023*')",
        ),
    ] = None,
    provider: Annotated[
        str | None,
        typer.Option(
            "--provider",
            "-p",
            help="AI provider to use (claude, openai, gemini, ollama)",
        ),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="Override the default model for the provider",
        ),
    ] = None,
    ocr_model: Annotated[
        str | None,
        typer.Option(
            "--ocr-model",
            help="Override Ollama OCR model (default: deepseek-ocr)",
        ),
    ] = None,
    template: Annotated[
        str | None,
        typer.Option(
            "--template",
            "-t",
            help="Filename template or preset (default, compact, full, simple)",
        ),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            "-o",
            help="Copy renamed files to this directory (keeps originals)",
            exists=True,
            file_okay=False,
            resolve_path=True,
        ),
    ] = None,
    collision: Annotated[
        CollisionStrategy,
        typer.Option(
            "--collision",
            "-c",
            help="How to handle filename collisions",
        ),
    ] = CollisionStrategy.SKIP,
    parallel: Annotated[
        int,
        typer.Option(
            "--parallel",
            help="Number of concurrent extractions (1 = sequential)",
        ),
    ] = 1,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output results as JSON",
        ),
    ] = False,
) -> None:
    """Batch rename PDF files in a directory.

    By default, runs in dry-run mode showing what would happen.
    Use --execute to actually rename files.

    Template placeholders:
      {authors}        - Author surnames
      {authors_full}   - Author full names
      {authors_abbrev} - Surname with initials
      {year}           - Publication year
      {journal}        - Journal abbreviation
      {journal_full}   - Full journal name
      {title}          - Paper title

    Preset templates: default, compact, full, simple
    """
    from namingpaper.batch import (
        scan_directory,
        process_batch_sync,
        detect_batch_collisions,
        execute_batch,
    )
    from namingpaper.template import validate_template, get_template
    import json

    # Validate template if provided
    if template:
        template_str = get_template(template)
        is_valid, error = validate_template(template_str)
        if not is_valid:
            console.print(f"[red]Invalid template:[/red] {error}")
            raise typer.Exit(1)

    # Scan directory
    console.print(f"[blue]Scanning[/blue] {directory}...")
    pdf_files = scan_directory(directory, recursive=recursive, pattern=filter_pattern)

    if not pdf_files:
        console.print("[yellow]No PDF files found.[/yellow]")
        raise typer.Exit(0)

    console.print(f"Found [bold]{len(pdf_files)}[/bold] PDF file(s)")
    console.print()

    # Process files with progress bar
    items: list[BatchItem] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Extracting metadata...", total=len(pdf_files))

        def on_progress(current: int, total: int, item: BatchItem) -> None:
            progress.update(task, completed=current, description=f"Processing: {item.source.name[:40]}")

        try:
            items = process_batch_sync(
                pdf_files,
                provider_name=provider,
                model_name=model,
                ocr_model=ocr_model,
                template=template,
                output_dir=output_dir,
                parallel=parallel,
                progress_callback=on_progress,
            )
        except Exception as e:
            console.print(f"[red]Error during extraction:[/red] {e}")
            raise typer.Exit(1)

    # Detect internal collisions
    items = detect_batch_collisions(items)

    # Compute status counts once
    ok_count = sum(1 for i in items if i.status == BatchItemStatus.OK)
    collision_count = sum(1 for i in items if i.status == BatchItemStatus.COLLISION)
    error_count = sum(1 for i in items if i.status == BatchItemStatus.ERROR)
    skipped_count = sum(1 for i in items if i.status == BatchItemStatus.SKIPPED)

    # JSON output mode
    if json_output:
        output = {
            "files": [
                {
                    "source": str(item.source),
                    "destination": str(item.destination) if item.destination else None,
                    "status": item.status.value,
                    "error": item.error,
                    "metadata": item.metadata.model_dump() if item.metadata else None,
                }
                for item in items
            ],
            "summary": {
                "total": len(items),
                "ok": ok_count,
                "collision": collision_count,
                "error": error_count,
                "skipped": skipped_count,
            },
        }
        print(json.dumps(output, indent=2))
        return

    # Display preview table
    console.print()
    table = Table(title="Planned Renames", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Original", style="cyan", max_width=40)
    table.add_column("New Name", max_width=50)
    table.add_column("Status", width=10)
    table.add_column("Confidence", width=10)

    status_styles = {
        BatchItemStatus.OK: "[green]OK[/green]",
        BatchItemStatus.COLLISION: "[yellow]COLLISION[/yellow]",
        BatchItemStatus.ERROR: "[red]ERROR[/red]",
        BatchItemStatus.PENDING: "[dim]PENDING[/dim]",
        BatchItemStatus.SKIPPED: "[dim]SKIPPED[/dim]",
        BatchItemStatus.COMPLETED: "[green]DONE[/green]",
    }

    for i, item in enumerate(items, 1):
        status_str = status_styles.get(item.status, str(item.status))
        confidence = f"{item.metadata.confidence:.0%}" if item.metadata else "-"
        new_name = item.destination.name if item.destination else item.error or "N/A"

        if item.status == BatchItemStatus.ERROR:
            new_name = f"[red]{item.error}[/red]"

        table.add_row(
            str(i),
            item.source.name,
            new_name,
            status_str,
            confidence,
        )

    console.print(table)
    console.print()

    # Summary
    summary_parts = [f"[green]{ok_count} ready[/green]"]
    if collision_count:
        summary_parts.append(f"[yellow]{collision_count} collisions[/yellow]")
    if skipped_count:
        summary_parts.append(f"[dim]{skipped_count} skipped[/dim]")
    if error_count:
        summary_parts.append(f"[red]{error_count} errors[/red]")
    console.print(f"Summary: {', '.join(summary_parts)}")
    console.print()

    # Dry run mode
    if not execute:
        action = "copy" if output_dir else "rename"
        console.print(f"[dim]Dry run mode. Use --execute to {action} files.[/dim]")
        return

    # Nothing to process
    if ok_count == 0 and collision_count == 0:
        console.print("[yellow]No files to process.[/yellow]")
        return

    # Confirm
    if not yes:
        action = "copy" if output_dir else "rename"
        if collision == CollisionStrategy.SKIP:
            processable = ok_count
        else:
            processable = ok_count + collision_count
        confirmed = typer.confirm(
            f"Proceed with {action} of {processable} file(s)? "
            f"(Collision strategy: {collision.value})"
        )
        if not confirmed:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    # Execute batch
    console.print()
    copy_mode = output_dir is not None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Renaming files...", total=len(items))

        def on_execute_progress(current: int, total: int, item: BatchItem) -> None:
            progress.update(task, completed=current)

        result = execute_batch(
            items,
            collision_strategy=collision,
            copy=copy_mode,
            progress_callback=on_execute_progress,
        )

    # Final summary
    console.print()
    console.print(
        f"[bold]Complete:[/bold] "
        f"[green]{result.successful} successful[/green], "
        f"[yellow]{result.skipped} skipped[/yellow], "
        f"[red]{result.errors} errors[/red]"
    )


@app.command()
def config(
    show: Annotated[
        bool,
        typer.Option(
            "--show",
            "-s",
            help="Show current configuration",
        ),
    ] = False,
) -> None:
    """View or manage configuration."""
    if show:
        settings = get_settings()
        table = Table(title="Current Configuration", show_header=False)
        table.add_column("Setting", style="cyan")
        table.add_column("Value")

        table.add_row("AI Provider", settings.ai_provider)
        table.add_row(
            "Anthropic API Key",
            "[green]set[/green]"
            if settings.anthropic_api_key
            else "[dim]not set[/dim]",
        )
        table.add_row(
            "OpenAI API Key",
            "[green]set[/green]"
            if settings.openai_api_key
            else "[dim]not set[/dim]",
        )
        table.add_row(
            "Gemini API Key",
            "[green]set[/green]"
            if settings.gemini_api_key
            else "[dim]not set[/dim]",
        )
        table.add_row("Ollama URL", settings.ollama_base_url)
        table.add_row(
            "Ollama OCR Model",
            settings.ollama_ocr_model or "[dim]default (deepseek-ocr)[/dim]",
        )
        table.add_row("Max Authors", str(settings.max_authors))
        table.add_row("Max Filename Length", str(settings.max_filename_length))

        console.print(table)
    else:
        console.print("Use --show to view current configuration.")
        console.print()
        console.print("Configuration can be set via:")
        console.print("  - Environment variables (NAMINGPAPER_*)")
        console.print("  - Config file (~/.namingpaper/config.toml)")


@app.command()
def templates() -> None:
    """Show available filename templates."""
    from namingpaper.template import list_presets

    table = Table(title="Available Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Pattern")
    table.add_column("Example")

    examples = {
        "default": "Smith, Wang, (2023, JFE), Asset pricing....pdf",
        "compact": "Smith, Wang (2023) Asset pricing....pdf",
        "full": "Smith, Wang, (2023, Journal of Financial Economics), Asset pricing....pdf",
        "simple": "Smith, Wang - 2023 - Asset pricing....pdf",
    }

    for name, pattern in list_presets().items():
        table.add_row(name, pattern, examples.get(name, ""))

    console.print(table)
    console.print()
    console.print("[dim]Use with: namingpaper batch --template <name|pattern>[/dim]")


@app.command()
def check(
    provider: Annotated[
        str | None,
        typer.Option(
            "--provider",
            "-p",
            help="Provider to check (claude, openai, gemini, ollama)",
        ),
    ] = None,
) -> None:
    """Check if your environment is set up correctly."""
    import httpx

    settings = get_settings()
    provider_name = provider or settings.ai_provider

    table = Table(title="Setup Check", show_header=True)
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    all_ok = True

    table.add_row("Provider", "[green]OK[/green]", provider_name)

    if provider_name == "ollama":
        ocr_model = settings.ollama_ocr_model or "deepseek-ocr"
        text_model = settings.model_name or "qwen3:8b"
        base_url = settings.ollama_base_url

        # Check connectivity
        try:
            resp = httpx.get(f"{base_url}/api/tags", timeout=5.0)
            resp.raise_for_status()
            tag_data = resp.json()
            table.add_row("Ollama server", "[green]OK[/green]", base_url)

            # Check models
            available = {m["name"] for m in tag_data.get("models", [])}

            # Text model is required (exact match only)
            if text_model in available:
                table.add_row("Text model", "[green]OK[/green]", text_model)
            else:
                table.add_row("Text model", "[red]MISSING[/red]", f"Run: ollama pull {text_model}")
                all_ok = False

            # OCR model is optional (only used when PDF text extraction is insufficient)
            if ocr_model in available:
                table.add_row("OCR model", "[green]OK[/green]", ocr_model)
            else:
                table.add_row("OCR model", "[yellow]OPTIONAL[/yellow]", f"For scanned PDFs: ollama pull {ocr_model}")
        except (httpx.ConnectError, httpx.HTTPError):
            table.add_row("Ollama server", "[red]FAIL[/red]", f"Cannot connect to {base_url}")
            table.add_row("Text model", "[dim]SKIP[/dim]", "Server not reachable")
            table.add_row("OCR model", "[dim]SKIP[/dim]", "Server not reachable")
            all_ok = False

            console.print(table)
            console.print()
            console.print(
                "[yellow]Ollama is not reachable. To set up:[/yellow]\n"
                "  1. Install Ollama: https://ollama.com/download\n"
                "  2. Start the server: ollama serve\n"
                f"  3. Pull the text model: ollama pull {text_model}\n"
                f"  4. (Optional, for scanned PDFs) ollama pull {ocr_model}\n\n"
                "Or use a different provider: namingpaper rename --provider claude <file>"
            )
            raise typer.Exit(1)
    else:
        # Cloud provider checks
        provider_info = {
            "claude": ("anthropic", settings.anthropic_api_key, "NAMINGPAPER_ANTHROPIC_API_KEY"),
            "openai": ("openai", settings.openai_api_key, "NAMINGPAPER_OPENAI_API_KEY"),
            "gemini": ("google.generativeai", settings.gemini_api_key, "NAMINGPAPER_GEMINI_API_KEY"),
        }

        if provider_name not in provider_info:
            table.add_row("Provider", "[red]UNKNOWN[/red]", f"'{provider_name}' is not a valid provider")
            console.print(table)
            raise typer.Exit(1)

        package, api_key, env_var = provider_info[provider_name]

        # Check package
        try:
            __import__(package)
            table.add_row("Package", "[green]OK[/green]", package)
        except ImportError:
            table.add_row("Package", "[red]MISSING[/red]", f"Run: uv add {package}")
            all_ok = False

        # Check API key
        if api_key:
            table.add_row("API key", "[green]OK[/green]", f"{env_var} is set")
        else:
            table.add_row("API key", "[red]MISSING[/red]", f"Set {env_var}")
            all_ok = False

    console.print(table)
    console.print()

    if all_ok:
        console.print("[green]All checks passed![/green]")
    else:
        console.print("[yellow]Some checks failed. See details above.[/yellow]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
