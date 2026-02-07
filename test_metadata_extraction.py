#!/usr/bin/env python3
"""Debug script to see what metadata extraction returns."""
import asyncio
import json
from pathlib import Path

from namingpaper.pdf_reader import extract_pdf_content
from namingpaper.providers.ollama import OllamaProvider


async def test_metadata_extraction():
    pdf_path = Path(
        "/Users/tsaipingjui/Library/CloudStorage/OneDrive-國立臺灣大學/論文/"
        "Yoshiba (2015, Review of Economic Studies and Management), "
        "Maximum Likelihood Estimation of Skew-t Copulas with Its Applications to Stock Returns.pdf.pdf"
    )

    print(f"Testing with: {pdf_path.name}\n")

    # Extract PDF content
    print("1. Extracting PDF content...")
    content = extract_pdf_content(pdf_path)
    print(f"   Text length: {len(content.text)} chars")
    print(f"   Has image: {content.first_page_image is not None}\n")

    # Try to extract metadata
    print("2. Extracting metadata with Ollama...")
    provider = OllamaProvider()

    try:
        metadata = await provider.extract_metadata(content)
        print("   ✓ Success!\n")
        print("=== EXTRACTED METADATA ===")
        print(json.dumps(metadata.model_dump(), indent=2))
    except Exception as e:
        print(f"   ✗ Error: {e}\n")

        # Try to get the raw response
        print("=== DEBUGGING: Raw Ollama Response ===")
        import httpx
        from namingpaper.providers.base import EXTRACTION_PROMPT
        from namingpaper.config import get_settings

        settings = get_settings()

        # Stage 1: OCR
        if content.first_page_image:
            import base64
            image_b64 = base64.standard_b64encode(content.first_page_image).decode("utf-8")
            ocr_payload = {
                "model": "deepseek-ocr",
                "messages": [
                    {
                        "role": "user",
                        "content": "Extract all text from this academic paper image. Include title, authors, abstract, and any visible text.",
                        "images": [image_b64],
                    }
                ],
                "stream": False,
                "keep_alive": "30s",
            }

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    "http://localhost:11434/api/chat",
                    json=ocr_payload,
                )
                ocr_result = response.json()
                ocr_text = ocr_result.get("message", {}).get("content", "")
                print(f"\nOCR extracted text (first 500 chars):\n{ocr_text[:500]}\n")

                combined_text = f"=== OCR Text from First Page ===\n{ocr_text}\n\n=== PDF Text ===\n{content.text}"
        else:
            combined_text = content.text

        # Stage 2: Parse metadata
        text = combined_text[:settings.max_text_chars]
        prompt = f"Paper text:\n\n{text}\n\n{EXTRACTION_PROMPT}"

        parse_payload = {
            "model": "llama3.1:8b",
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "keep_alive": "30s",
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json=parse_payload,
            )
            parse_result = response.json()
            raw_response = parse_result.get("response", "")
            print(f"Raw metadata parsing response:\n{raw_response}\n")

            # Try to extract JSON
            json_text = raw_response
            if "```json" in raw_response:
                json_text = raw_response.split("```json")[1].split("```")[0]
            elif "```" in raw_response:
                json_text = raw_response.split("```")[1].split("```")[0]

            try:
                data = json.loads(json_text.strip())
                print("Parsed JSON:")
                print(json.dumps(data, indent=2))
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")


if __name__ == "__main__":
    asyncio.run(test_metadata_extraction())
