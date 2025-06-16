import fitz  # PyMuPDF
import json
from typing import List, Dict, Any
import pytesseract
from PIL import Image
import io
import re
from datetime import datetime

def extract_pdf_text_with_ocr(pdf_path: str) -> List[List[Dict[str, Any]]]:
    doc = fitz.open(pdf_path)
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("blocks")
        page_lines = []
        # If text blocks are found, use them
        if blocks and any(block[4].strip() for block in blocks):
            for block in blocks:
                x0, y0, x1, y1, text, *_ = block
                if text.strip():
                    page_lines.append({
                        "text": text.strip(),
                        "bbox": [x0, y0, x1, y1],
                        "page": page_num + 1,
                        "source": "text"
                    })
        else:
            # Fallback to OCR for this page
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            ocr_text = pytesseract.image_to_string(img, lang="eng+fra")
            # Optionally, split OCR text into lines
            for line in ocr_text.splitlines():
                if line.strip():
                    page_lines.append({
                        "text": line.strip(),
                        "bbox": None,  # No bbox from OCR
                        "page": page_num + 1,
                        "source": "ocr"
                    })
        pages.append(page_lines)
    return pages

def save_extraction_to_json(pages: List[List[Dict[str, Any]]], output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)

def extract_date_from_pdf_metadata(pdf_path: str):
    """Try to extract the creation or modification date from PDF metadata."""
    doc = fitz.open(pdf_path)
    meta = doc.metadata
    date_str = meta.get('creationDate') or meta.get('modDate')
    if date_str:
        # PDF dates are often in the format D:YYYYMMDDHHmmSS
        m = re.match(r"D:(\d{4})(\d{2})(\d{2})", date_str)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
            except Exception:
                pass
    return None

def extract_date_from_filename(filename: str):
    """Try to extract a date from the filename in formats like YYYY-MM-DD, YYYYMMDD, or YYYY_MM_DD."""
    patterns = [
        r"(20\d{2})[-_](\d{2})[-_](\d{2})",  # 2023-06-10 or 2023_06_10
        r"(20\d{2})(\d{2})(\d{2})",         # 20230610
    ]
    for pat in patterns:
        m = re.search(pat, filename)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
            except Exception:
                continue
    return None

