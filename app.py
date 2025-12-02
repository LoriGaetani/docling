# main.py

import os
import sys
from datetime import datetime
from pathlib import Path

import torch

from docling_pipeline import run_docling_parsing
from easyocr_report import run_easyocr_report_if_needed
from openai_ocr_report import run_openai_ocr_report_if_needed


def parse_document(
    file_path: str = "esame.jpg",
    output_root: str = "output",
    use_rapidocr: bool = False,
    use_openai: bool = False,
):
    """
    - crea output/<run_id>/ per ogni esecuzione
    - lancia Docling (JSON, MD, immagini, chunks)
    - lancia EasyOCR per il report, se serve
    """
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    print("CUDA is available" if torch.cuda.is_available() else "CUDA is NOT available")

    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)

    run_id = f"{Path(file_path).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = output_root_path / run_id
    print(f"Run output directory: {run_dir}")

    try:
        # 1) Docling
        ocr_enabled, ocr_engine_name, _ = run_docling_parsing(
            file_path=file_path,
            run_dir=run_dir,
            use_rapidocr=use_rapidocr,
        )

        # 2) OCR esterno
        if use_openai:
            run_openai_ocr_report_if_needed(
                file_path=file_path,
                ocr_enabled=ocr_enabled,
                docling_ocr_engine_name=ocr_engine_name,
                run_dir=run_dir,
                model="gpt-4o",  # o altro modello OpenAI che preferisci
            )
        else:
            run_easyocr_report_if_needed(
                file_path=file_path,
                ocr_enabled=ocr_enabled,
                ocr_engine_name=ocr_engine_name,
                run_dir=run_dir,
            )

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Uso: python main.py [file] [--rapidocr]
    args = sys.argv[1:]

    file_path = "dataset/appunti-a-mano.jpg"
    use_rapidocr = False
    use_openai = False

    for a in args:
        if a == "--rapidocr":
            use_rapidocr = True
        elif a == "--openai":
            use_openai = True
        elif not a.startswith("-"):
            file_path = a

    parse_document(
        file_path=file_path,
        use_rapidocr=use_rapidocr,
        use_openai=use_openai,
    )
