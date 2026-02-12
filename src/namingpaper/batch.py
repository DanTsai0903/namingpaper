"""Batch processing for multiple PDF files."""

import asyncio
from fnmatch import fnmatch
from pathlib import Path
from typing import Callable

from namingpaper.models import (
    BatchItem,
    BatchItemStatus,
    BatchResult,
    LowConfidenceError,
    PaperMetadata,
    RenameOperation,
)
from namingpaper.extractor import extract_metadata
from namingpaper.formatter import build_destination
from namingpaper.template import build_filename_from_template
from namingpaper.providers import get_provider
from namingpaper.providers.base import AIProvider
from namingpaper.renamer import check_collision, execute_rename, CollisionStrategy


def scan_directory(
    directory: Path,
    recursive: bool = False,
    pattern: str | None = None,
) -> list[Path]:
    """Scan directory for PDF files.

    Args:
        directory: Directory to scan
        recursive: If True, scan subdirectories
        pattern: Optional glob pattern to filter filenames

    Returns:
        List of PDF file paths, sorted by name
    """
    if recursive:
        pdf_files = list(directory.rglob("*.pdf"))
    else:
        pdf_files = list(directory.glob("*.pdf"))

    # Apply filename filter
    if pattern:
        pdf_files = [f for f in pdf_files if fnmatch(f.name, pattern)]

    # Sort by name for consistent ordering
    return sorted(pdf_files, key=lambda p: p.name.lower())


async def process_single_file(
    pdf_path: Path,
    provider: AIProvider,
    template: str | None = None,
    output_dir: Path | None = None,
) -> BatchItem:
    """Process a single PDF file for batch operation.

    Args:
        pdf_path: Path to PDF file
        provider: AI provider for metadata extraction
        template: Optional template for filename formatting
        output_dir: Optional output directory

    Returns:
        BatchItem with extraction results
    """
    item = BatchItem(source=pdf_path)

    try:
        # Quick check: skip files that can't be opened
        with open(pdf_path, "rb") as f:
            header = f.read(5)
        if header != b"%PDF-":
            item.status = BatchItemStatus.SKIPPED
            item.error = "Not a valid PDF file"
            return item

        # Extract metadata
        metadata = await extract_metadata(pdf_path, provider=provider)
        item.metadata = metadata

        # Build destination filename
        if template:
            filename = build_filename_from_template(metadata, template)
        else:
            dest = build_destination(pdf_path, metadata)
            filename = dest.name

        # Determine destination directory
        if output_dir:
            item.destination = output_dir / filename
        else:
            item.destination = pdf_path.parent / filename

        # Check for collision
        if check_collision(item.destination):
            item.status = BatchItemStatus.COLLISION
        else:
            item.status = BatchItemStatus.OK

    except LowConfidenceError as e:
        item.status = BatchItemStatus.SKIPPED
        item.error = str(e)
    except (OSError, PermissionError) as e:
        item.status = BatchItemStatus.SKIPPED
        item.error = f"Cannot open file: {e}"
    except Exception as e:
        item.status = BatchItemStatus.ERROR
        item.error = str(e)

    return item


async def process_batch(
    files: list[Path],
    provider_name: str | None = None,
    model_name: str | None = None,
    ocr_model: str | None = None,
    template: str | None = None,
    output_dir: Path | None = None,
    parallel: int = 1,
    progress_callback: Callable[[int, int, BatchItem], None] | None = None,
) -> list[BatchItem]:
    """Process multiple PDF files.

    Args:
        files: List of PDF file paths
        provider_name: AI provider name
        model_name: Override the default model for the provider
        ocr_model: Override the Ollama OCR model
        template: Optional template for filename formatting
        output_dir: Optional output directory
        parallel: Number of concurrent extractions (1 = sequential)
        progress_callback: Called after each file with (current, total, item)

    Returns:
        List of BatchItem results
    """
    provider = get_provider(provider_name, model_name=model_name, ocr_model=ocr_model, keep_alive="60s")
    results: list[BatchItem] = []
    total = len(files)

    try:
        if parallel <= 1:
            # Sequential processing
            for i, pdf_path in enumerate(files):
                item = await process_single_file(pdf_path, provider, template, output_dir)
                results.append(item)
                if progress_callback:
                    progress_callback(i + 1, total, item)
        else:
            # Parallel processing with semaphore
            semaphore = asyncio.Semaphore(parallel)
            lock = asyncio.Lock()
            completed = 0

            async def process_with_semaphore(pdf_path: Path) -> BatchItem:
                nonlocal completed
                async with semaphore:
                    item = await process_single_file(pdf_path, provider, template, output_dir)
                    async with lock:
                        completed += 1
                        if progress_callback:
                            progress_callback(completed, total, item)
                    return item

            results = await asyncio.gather(
                *[process_with_semaphore(f) for f in files],
                return_exceptions=True,
            )
            # Handle any exceptions that were returned
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    item = BatchItem(source=files[i])
                    item.status = BatchItemStatus.ERROR
                    item.error = str(result)
                    processed_results.append(item)
                else:
                    processed_results.append(result)
            results = processed_results
    finally:
        if hasattr(provider, "aclose"):
            await provider.aclose()

    return results


def detect_batch_collisions(items: list[BatchItem]) -> list[BatchItem]:
    """Detect collisions within the batch itself.

    Multiple source files might map to the same destination.

    Args:
        items: List of batch items to check

    Returns:
        Updated items with collision status
    """
    # Group by destination (include both OK and COLLISION items for cross-detection)
    # Use case-folded string key for case-insensitive filesystems (macOS, Windows)
    dest_map: dict[str, list[BatchItem]] = {}
    for item in items:
        if item.destination and item.status in (BatchItemStatus.OK, BatchItemStatus.COLLISION):
            key = str(item.destination).casefold()
            dest_map.setdefault(key, []).append(item)

    # Mark internal collisions
    for dest, colliding_items in dest_map.items():
        if len(colliding_items) > 1:
            for item in colliding_items:
                item.status = BatchItemStatus.COLLISION
                item.error = f"Collides with {len(colliding_items) - 1} other file(s)"

    return items


def execute_batch(
    items: list[BatchItem],
    collision_strategy: CollisionStrategy = CollisionStrategy.SKIP,
    copy: bool = False,
    progress_callback: Callable[[int, int, BatchItem], None] | None = None,
) -> BatchResult:
    """Execute rename operations for batch items.

    Args:
        items: List of BatchItem to process
        collision_strategy: How to handle collisions
        copy: If True, copy instead of rename
        progress_callback: Called after each file

    Returns:
        BatchResult with summary
    """
    result = BatchResult(total=len(items), items=items)
    total = len(items)

    for i, item in enumerate(items):
        if item.status == BatchItemStatus.SKIPPED:
            result.skipped += 1
        elif item.status == BatchItemStatus.ERROR:
            result.errors += 1
        elif item.status in (BatchItemStatus.OK, BatchItemStatus.COLLISION):
            if item.destination is None or item.metadata is None:
                item.status = BatchItemStatus.ERROR
                item.error = "Missing destination or metadata"
                result.errors += 1
                continue

            operation = RenameOperation(
                source=item.source,
                destination=item.destination,
                metadata=item.metadata,
            )

            try:
                outcome = execute_rename(
                    operation,
                    collision_strategy=collision_strategy,
                    copy=copy,
                )
                if outcome is None:
                    item.status = BatchItemStatus.SKIPPED
                    result.skipped += 1
                else:
                    item.status = BatchItemStatus.COMPLETED
                    item.destination = outcome
                    result.successful += 1
            except Exception as e:
                item.status = BatchItemStatus.ERROR
                item.error = str(e)
                result.errors += 1

        if progress_callback:
            progress_callback(i + 1, total, item)

    return result


def process_batch_sync(
    files: list[Path],
    provider_name: str | None = None,
    model_name: str | None = None,
    ocr_model: str | None = None,
    template: str | None = None,
    output_dir: Path | None = None,
    parallel: int = 1,
    progress_callback: Callable[[int, int, BatchItem], None] | None = None,
) -> list[BatchItem]:
    """Synchronous wrapper for process_batch."""
    return asyncio.run(
        process_batch(
            files,
            provider_name=provider_name,
            model_name=model_name,
            ocr_model=ocr_model,
            template=template,
            output_dir=output_dir,
            parallel=parallel,
            progress_callback=progress_callback,
        )
    )
