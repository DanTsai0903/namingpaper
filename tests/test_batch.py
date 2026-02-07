"""Tests for batch processing module."""

from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

from namingpaper.models import (
    LowConfidenceError,
    PaperMetadata,
    BatchItem,
    BatchItemStatus,
)
from namingpaper.batch import (
    scan_directory,
    process_single_file,
    detect_batch_collisions,
)


class TestScanDirectory:
    """Tests for scan_directory function."""

    def test_scan_empty_directory(self, tmp_path: Path) -> None:
        """Should return empty list for directory with no PDFs."""
        result = scan_directory(tmp_path)
        assert result == []

    def test_scan_directory_with_pdfs(self, tmp_path: Path) -> None:
        """Should find all PDF files in directory."""
        (tmp_path / "paper1.pdf").touch()
        (tmp_path / "paper2.pdf").touch()
        (tmp_path / "other.txt").touch()

        result = scan_directory(tmp_path)

        assert len(result) == 2
        assert all(p.suffix == ".pdf" for p in result)

    def test_scan_directory_sorted(self, tmp_path: Path) -> None:
        """Should return files sorted by name."""
        (tmp_path / "zebra.pdf").touch()
        (tmp_path / "alpha.pdf").touch()
        (tmp_path / "middle.pdf").touch()

        result = scan_directory(tmp_path)

        assert [p.name for p in result] == ["alpha.pdf", "middle.pdf", "zebra.pdf"]

    def test_scan_non_recursive(self, tmp_path: Path) -> None:
        """Should not scan subdirectories by default."""
        (tmp_path / "root.pdf").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.pdf").touch()

        result = scan_directory(tmp_path, recursive=False)

        assert len(result) == 1
        assert result[0].name == "root.pdf"

    def test_scan_recursive(self, tmp_path: Path) -> None:
        """Should scan subdirectories when recursive=True."""
        (tmp_path / "root.pdf").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.pdf").touch()

        result = scan_directory(tmp_path, recursive=True)

        assert len(result) == 2

    def test_scan_with_filter_pattern(self, tmp_path: Path) -> None:
        """Should filter files by pattern."""
        (tmp_path / "2023_paper1.pdf").touch()
        (tmp_path / "2023_paper2.pdf").touch()
        (tmp_path / "2022_old.pdf").touch()

        result = scan_directory(tmp_path, pattern="2023*")

        assert len(result) == 2
        assert all("2023" in p.name for p in result)


class TestDetectBatchCollisions:
    """Tests for detect_batch_collisions function."""

    def test_no_collisions(self, tmp_path: Path) -> None:
        """Should not modify items when no collisions."""
        items = [
            BatchItem(
                source=tmp_path / "a.pdf",
                destination=tmp_path / "A.pdf",
                status=BatchItemStatus.OK,
            ),
            BatchItem(
                source=tmp_path / "b.pdf",
                destination=tmp_path / "B.pdf",
                status=BatchItemStatus.OK,
            ),
        ]

        result = detect_batch_collisions(items)

        assert all(item.status == BatchItemStatus.OK for item in result)

    def test_internal_collision(self, tmp_path: Path) -> None:
        """Should detect when multiple files map to same destination."""
        dest = tmp_path / "Same Name.pdf"
        items = [
            BatchItem(
                source=tmp_path / "a.pdf",
                destination=dest,
                status=BatchItemStatus.OK,
            ),
            BatchItem(
                source=tmp_path / "b.pdf",
                destination=dest,
                status=BatchItemStatus.OK,
            ),
        ]

        result = detect_batch_collisions(items)

        assert all(item.status == BatchItemStatus.COLLISION for item in result)

    def test_skip_error_items(self, tmp_path: Path) -> None:
        """Should not check items with error status."""
        items = [
            BatchItem(
                source=tmp_path / "a.pdf",
                destination=tmp_path / "Same.pdf",
                status=BatchItemStatus.OK,
            ),
            BatchItem(
                source=tmp_path / "b.pdf",
                destination=tmp_path / "Same.pdf",
                status=BatchItemStatus.ERROR,
            ),
        ]

        result = detect_batch_collisions(items)

        # First should stay OK (only one OK item with that dest)
        assert result[0].status == BatchItemStatus.OK
        # Second keeps ERROR status
        assert result[1].status == BatchItemStatus.ERROR


@pytest.mark.asyncio
class TestProcessSingleFile:
    """Tests for process_single_file function."""

    async def test_successful_extraction(
        self, tmp_path: Path, sample_metadata: PaperMetadata, mock_provider
    ) -> None:
        """Should create BatchItem with OK status on success."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()

        with patch("namingpaper.batch.extract_metadata", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = sample_metadata

            item = await process_single_file(pdf_path, mock_provider)

        assert item.status == BatchItemStatus.OK
        assert item.metadata == sample_metadata
        assert item.destination is not None
        assert item.destination.suffix == ".pdf"

    async def test_extraction_error(self, tmp_path: Path, mock_provider) -> None:
        """Should set ERROR status when extraction fails."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()

        with patch("namingpaper.batch.extract_metadata", new_callable=AsyncMock) as mock_extract:
            mock_extract.side_effect = Exception("API error")

            item = await process_single_file(pdf_path, mock_provider)

        assert item.status == BatchItemStatus.ERROR
        assert "API error" in item.error

    async def test_collision_detection(
        self, tmp_path: Path, sample_metadata: PaperMetadata, mock_provider
    ) -> None:
        """Should detect collision with existing file."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()

        with patch("namingpaper.batch.extract_metadata", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = sample_metadata
            with patch("namingpaper.batch.check_collision", return_value=True):
                item = await process_single_file(pdf_path, mock_provider)

        assert item.status == BatchItemStatus.COLLISION

    async def test_custom_output_dir(
        self, tmp_path: Path, sample_metadata: PaperMetadata, mock_provider
    ) -> None:
        """Should use output_dir when specified."""
        pdf_path = tmp_path / "input" / "test.pdf"
        pdf_path.parent.mkdir()
        pdf_path.touch()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch("namingpaper.batch.extract_metadata", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = sample_metadata

            item = await process_single_file(pdf_path, mock_provider, output_dir=output_dir)

        assert item.destination.parent == output_dir

    async def test_low_confidence_skipped(self, tmp_path: Path, mock_provider) -> None:
        """Should set SKIPPED status when confidence is below threshold."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()

        with patch("namingpaper.batch.extract_metadata", new_callable=AsyncMock) as mock_extract:
            mock_extract.side_effect = LowConfidenceError(0.1, 0.5)

            item = await process_single_file(pdf_path, mock_provider)

        assert item.status == BatchItemStatus.SKIPPED
        assert "not be an academic paper" in item.error
