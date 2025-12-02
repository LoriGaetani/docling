# easyocr_report.py

from pathlib import Path
from typing import List, Optional

import easyocr


def easyocr_text_from_image(
    image_path: str,
    languages: Optional[List[str]] = None,
    gpu: bool = False,
) -> List[str]:
    if languages is None:
        languages = ["it", "en"]

    print(f"Running EasyOCR on {image_path}...")
    reader = easyocr.Reader(languages, gpu=gpu)
    results = reader.readtext(image_path, detail=1)

    lines = []
    for idx, item in enumerate(results, start=1):
        bbox, text, conf = item
        line = f"{idx:03d}. {text} (conf={conf:.3f})"
        lines.append(line)
    return lines


def build_easyocr_markdown(image_path: str) -> str:
    try:
        easy_lines = easyocr_text_from_image(image_path)
    except Exception as e:
        print(f"Error in EasyOCR: {e}")
        easy_lines = [f"Error while running EasyOCR: {e}"]

    md_parts = []
    md_parts.append("## EasyOCR\n")
    md_parts.append("```text")
    if easy_lines:
        md_parts.extend(easy_lines)
    else:
        md_parts.append("(No text detected by EasyOCR)")
    md_parts.append("```")
    md_parts.append("")
    return "\n".join(md_parts)


def run_easyocr_report_if_needed(
    file_path: str,
    ocr_enabled: bool,
    ocr_engine_name: str,
    run_dir: Path,
) -> None:
    """
    Crea ocr_compare.md dentro run_dir se:
      - il file è un'immagine
      - ocr_enabled è True
    In cima al markdown scrive quale OCR Docling è stato usato.
    """
    ext = Path(file_path).suffix.lower()
    image_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

    ocr_md_path = run_dir / "ocr_compare.md"

    if ext in image_exts and ocr_enabled:
        print("Running EasyOCR on input document-like image...")
        easy_md_body = build_easyocr_markdown(file_path)

        header = (
            f"# OCR report\n\n"
            f"> Docling OCR engine: **{ocr_engine_name}** "
            f"(enabled: {ocr_enabled})\n\n"
            f"File: `{file_path}`\n\n"
        )

        full_md = header + easy_md_body

        with open(ocr_md_path, "w", encoding="utf-8") as f:
            f.write(full_md)
        print(f"Successfully saved OCR markdown to {ocr_md_path}")

    elif ext in image_exts and not ocr_enabled:
        print("Input is an image but does not look like a document: skipping OCR report.")
    else:
        print("Input is not a single image, OCR report skipped.")
