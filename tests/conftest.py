"""Test fixtures for namingpaper."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from namingpaper.models import PaperMetadata, PDFContent
from namingpaper.providers.base import AIProvider
from namingpaper.config import reset_settings


@pytest.fixture
def sample_metadata() -> PaperMetadata:
    """Sample paper metadata for testing."""
    return PaperMetadata(
        authors=["Fama", "French"],
        year=1993,
        journal="Journal of Financial Economics",
        journal_abbrev="JFE",
        title="Common risk factors in the returns on stocks and bonds",
        confidence=0.95,
    )


@pytest.fixture
def sample_metadata_many_authors() -> PaperMetadata:
    """Sample metadata with many authors."""
    return PaperMetadata(
        authors=["Smith", "Jones", "Brown", "Davis", "Wilson"],
        year=2020,
        journal="American Economic Review",
        journal_abbrev="AER",
        title="A very long title that should be truncated in the filename",
        confidence=0.9,
    )


@pytest.fixture
def sample_pdf_content() -> PDFContent:
    """Sample PDF content for testing."""
    return PDFContent(
        text="Sample academic paper text with authors and title...",
        first_page_image=None,
        path=Path("/tmp/test.pdf"),
    )


class MockProvider(AIProvider):
    """Mock AI provider for testing."""

    def __init__(self, metadata: PaperMetadata):
        self._metadata = metadata

    async def extract_metadata(self, content: PDFContent) -> PaperMetadata:
        return self._metadata


@pytest.fixture
def mock_provider(sample_metadata: PaperMetadata) -> MockProvider:
    """Mock AI provider that returns sample metadata."""
    return MockProvider(sample_metadata)


@pytest.fixture(autouse=True)
def reset_settings_fixture():
    """Reset settings before each test."""
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def temp_pdf(tmp_path: Path) -> Path:
    """Create a temporary PDF file for testing."""
    pdf_path = tmp_path / "test_paper.pdf"
    # Create a minimal valid PDF
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000206 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
300
%%EOF"""
    pdf_path.write_bytes(pdf_content)
    return pdf_path
