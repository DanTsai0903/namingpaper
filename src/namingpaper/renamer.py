"""Safe file renaming operations."""

import shutil
from enum import Enum
from pathlib import Path

from namingpaper.models import RenameOperation


class CollisionStrategy(str, Enum):
    """Strategy for handling filename collisions."""

    SKIP = "skip"
    INCREMENT = "increment"
    OVERWRITE = "overwrite"


class RenameError(Exception):
    """Error during rename operation."""

    pass


def check_collision(destination: Path) -> bool:
    """Check if destination file already exists."""
    return destination.exists()


def get_incremented_path(destination: Path) -> Path:
    """Get a unique path by adding a number suffix.

    Example: paper.pdf -> paper (1).pdf -> paper (2).pdf
    """
    stem = destination.stem
    suffix = destination.suffix
    parent = destination.parent

    counter = 1
    while True:
        new_name = f"{stem} ({counter}){suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1
        if counter > 1000:
            raise RenameError(f"Too many collisions for {destination}")


def validate_rename(operation: RenameOperation) -> list[str]:
    """Validate a rename operation, returning list of warnings."""
    warnings = []

    # Don't follow symlinks (check before is_file, since symlinks to files pass is_file)
    if operation.source.is_symlink():
        raise RenameError(f"Source is a symlink (not supported): {operation.source}")

    # Check source is a regular file (not directory); is_file() returns False if nonexistent
    if not operation.source.is_file():
        raise RenameError(f"Source is not a regular file or does not exist: {operation.source}")

    # Check destination directory exists
    if not operation.destination.parent.exists():
        raise RenameError(
            f"Destination directory does not exist: {operation.destination.parent}"
        )

    # Check for collision
    if check_collision(operation.destination):
        warnings.append(f"Destination already exists: {operation.destination}")

    # Check if source and destination are the same
    if operation.source.resolve() == operation.destination.resolve():
        warnings.append("Source and destination are the same file")

    return warnings


def execute_rename(
    operation: RenameOperation,
    collision_strategy: CollisionStrategy = CollisionStrategy.SKIP,
    copy: bool = False,
) -> Path | None:
    """Execute a rename operation.

    Args:
        operation: The rename operation to execute
        collision_strategy: How to handle filename collisions
        copy: If True, copy the file instead of renaming (keeps original)

    Returns:
        The final destination path, or None if skipped
    """
    # Validate first
    warnings = validate_rename(operation)
    has_collision = any("Destination already exists" in w for w in warnings)

    destination = operation.destination

    # Handle collisions
    if has_collision:
        match collision_strategy:
            case CollisionStrategy.SKIP:
                return None
            case CollisionStrategy.INCREMENT:
                destination = get_incremented_path(destination)
            case CollisionStrategy.OVERWRITE:
                pass  # Will overwrite

    # Check same file
    if operation.source.resolve() == destination.resolve():
        return destination  # No-op, but successful

    # Perform the operation
    if copy:
        shutil.copy2(operation.source, destination)
    else:
        operation.source.replace(destination)
    return destination


def preview_rename(operation: RenameOperation, copy: bool = False) -> str:
    """Generate a human-readable preview of the rename operation."""
    source_name = operation.source.name
    dest_name = operation.destination.name

    # Show full path if destination is in a different directory
    if operation.source.parent != operation.destination.parent:
        dest_display = str(operation.destination)
    else:
        dest_display = dest_name

    action = "→ (copy)" if copy else "→"
    return f"{source_name} {action} {dest_display}"
