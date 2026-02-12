#!/usr/bin/env python3
"""Quick test to see what glm-ocr outputs.

Requires a running Ollama server with the glm-ocr model.
"""
import asyncio
import base64
import json
import time
from pathlib import Path

import pytest
import httpx

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PDF = FIXTURES_DIR / "sample.pdf"


@pytest.mark.skip(reason="Requires local Ollama server with glm-ocr model")
async def test_glm_ocr():
    pdf_path = SAMPLE_PDF

    print(f"Testing with: {pdf_path.name}\n")

    # Read first page as image
    from namingpaper.pdf_reader import extract_pdf_content

    print("Extracting PDF content...")
    start_time = time.time()
    content = extract_pdf_content(pdf_path)
    extract_time = time.time() - start_time
    print(f"✓ PDF extraction took: {extract_time:.2f}s")

    if not content.first_page_image:
        print("No image found, skipping OCR test")
        return

    image_b64 = base64.standard_b64encode(content.first_page_image).decode("utf-8")

    payload = {
        "model": "glm-ocr",
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

    print("\nCalling glm-ocr...")
    ocr_start = time.time()
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            "http://localhost:11434/api/chat",
            json=payload,
        )
        result = response.json()
    ocr_time = time.time() - ocr_start
    print(f"✓ OCR processing took: {ocr_time:.2f}s")

    print("\n=== RAW RESPONSE ===")
    print(json.dumps(result, indent=2))

    if "message" in result:
        ocr_text = result["message"].get("content", "")
        print("\n=== EXTRACTED TEXT ===")
        print(ocr_text[:1000])

    print(f"\n=== TIMING SUMMARY ===")
    print(f"PDF extraction: {extract_time:.2f}s")
    print(f"OCR processing: {ocr_time:.2f}s")
    print(f"Total time:     {extract_time + ocr_time:.2f}s")


if __name__ == "__main__":
    asyncio.run(test_glm_ocr())
