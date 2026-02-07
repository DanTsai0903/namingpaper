"""Abstract base class for AI providers."""

from abc import ABC, abstractmethod

from namingpaper.models import PDFContent, PaperMetadata


EXTRACTION_PROMPT = """Extract metadata from this academic paper.

Return a JSON object with these fields:
- authors: list of author last names only (e.g., ["Fama", "French"])
- year: publication year as integer
- journal: full journal name
- journal_abbrev: common abbreviation if known (e.g., "JFE" for Journal of Financial Economics, "AER" for American Economic Review), or null
- title: paper title (just the main title, not subtitle)
- confidence: your confidence in the extraction from 0.0 to 1.0

Common journal abbreviations:
- Journal of Finance -> JF
- Journal of Financial Economics -> JFE
- Review of Financial Studies -> RFS
- American Economic Review -> AER
- Quarterly Journal of Economics -> QJE
- Journal of Political Economy -> JPE
- Econometrica -> ECMA
- Review of Economic Studies -> REStud
- Journal of Monetary Economics -> JME
- Journal of Economic Theory -> JET

Only return valid JSON, no other text."""


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def extract_metadata(self, content: PDFContent) -> PaperMetadata:
        """Extract paper metadata using the AI model.

        Args:
            content: Extracted PDF content (text and optional image)

        Returns:
            Extracted paper metadata
        """
        pass

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncate text to fit within token limits."""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n\n[Text truncated...]"
