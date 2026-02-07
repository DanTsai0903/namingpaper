"""Tests for file renaming operations."""

from pathlib import Path

import pytest

from namingpaper.models import PaperMetadata, RenameOperation
from namingpaper.renamer import (
    CollisionStrategy,
    RenameError,
    check_collision,
    execute_rename,
    get_incremented_path,
    preview_rename,
    validate_rename,
)


@pytest.fixture
def temp_pdf_file(tmp_path: Path) -> Path:
    """Create a temporary PDF file."""
    pdf_path = tmp_path / "original.pdf"
    pdf_path.write_text("PDF content")
    return pdf_path


@pytest.fixture
def sample_operation(
    temp_pdf_file: Path, sample_metadata: PaperMetadata
) -> RenameOperation:
    """Create a sample rename operation."""
    return RenameOperation(
        source=temp_pdf_file,
        destination=temp_pdf_file.parent / "renamed.pdf",
        metadata=sample_metadata,
    )


class TestCheckCollision:
    def test_no_collision(self, tmp_path: Path):
        assert check_collision(tmp_path / "nonexistent.pdf") is False

    def test_collision_exists(self, temp_pdf_file: Path):
        assert check_collision(temp_pdf_file) is True


class TestGetIncrementedPath:
    def test_increments_filename(self, tmp_path: Path):
        # Create existing file
        (tmp_path / "paper.pdf").write_text("content")

        result = get_incremented_path(tmp_path / "paper.pdf")
        assert result == tmp_path / "paper (1).pdf"

    def test_increments_multiple(self, tmp_path: Path):
        # Create multiple existing files
        (tmp_path / "paper.pdf").write_text("content")
        (tmp_path / "paper (1).pdf").write_text("content")
        (tmp_path / "paper (2).pdf").write_text("content")

        result = get_incremented_path(tmp_path / "paper.pdf")
        assert result == tmp_path / "paper (3).pdf"


class TestValidateRename:
    def test_valid_operation(self, sample_operation: RenameOperation):
        warnings = validate_rename(sample_operation)
        assert warnings == []

    def test_source_not_exists(self, tmp_path: Path, sample_metadata: PaperMetadata):
        operation = RenameOperation(
            source=tmp_path / "nonexistent.pdf",
            destination=tmp_path / "dest.pdf",
            metadata=sample_metadata,
        )
        with pytest.raises(RenameError, match="does not exist"):
            validate_rename(operation)

    def test_warns_on_collision(
        self, temp_pdf_file: Path, sample_metadata: PaperMetadata
    ):
        # Create destination file
        dest = temp_pdf_file.parent / "dest.pdf"
        dest.write_text("existing")

        operation = RenameOperation(
            source=temp_pdf_file,
            destination=dest,
            metadata=sample_metadata,
        )
        warnings = validate_rename(operation)
        assert any("already exists" in w for w in warnings)


class TestExecuteRename:
    def test_successful_rename(self, sample_operation: RenameOperation):
        result = execute_rename(sample_operation)
        assert result == sample_operation.destination
        assert sample_operation.destination.exists()
        assert not sample_operation.source.exists()

    def test_skip_on_collision(
        self, temp_pdf_file: Path, sample_metadata: PaperMetadata
    ):
        # Create destination
        dest = temp_pdf_file.parent / "dest.pdf"
        dest.write_text("existing")

        operation = RenameOperation(
            source=temp_pdf_file,
            destination=dest,
            metadata=sample_metadata,
        )
        result = execute_rename(operation, collision_strategy=CollisionStrategy.SKIP)
        assert result is None
        assert temp_pdf_file.exists()  # Source unchanged

    def test_increment_on_collision(
        self, temp_pdf_file: Path, sample_metadata: PaperMetadata
    ):
        # Create destination
        dest = temp_pdf_file.parent / "dest.pdf"
        dest.write_text("existing")

        operation = RenameOperation(
            source=temp_pdf_file,
            destination=dest,
            metadata=sample_metadata,
        )
        result = execute_rename(
            operation, collision_strategy=CollisionStrategy.INCREMENT
        )
        assert result == temp_pdf_file.parent / "dest (1).pdf"
        assert result.exists()

    def test_overwrite_on_collision(
        self, temp_pdf_file: Path, sample_metadata: PaperMetadata
    ):
        # Create destination with different content
        dest = temp_pdf_file.parent / "dest.pdf"
        dest.write_text("old content")
        original_content = temp_pdf_file.read_text()

        operation = RenameOperation(
            source=temp_pdf_file,
            destination=dest,
            metadata=sample_metadata,
        )
        result = execute_rename(
            operation, collision_strategy=CollisionStrategy.OVERWRITE
        )
        assert result == dest
        assert dest.read_text() == original_content


class TestPreviewRename:
    def test_preview_format(self, sample_operation: RenameOperation):
        preview = preview_rename(sample_operation)
        assert "original.pdf" in preview
        assert "renamed.pdf" in preview
        assert "→" in preview
