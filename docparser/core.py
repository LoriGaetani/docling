import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List

import torch
import traceback

from .pipeline import run_docling_parsing, DoclingParseResult
from .reports.easyocr_report import run_easyocr_report_if_needed
from .utils import is_supported_file


def process_document(
        file_path: str,
        output_root: str = "output",
        use_rapidocr: bool = False,
        use_openai: bool = False,
) -> DoclingParseResult:
    """
    Funzione principale della libreria per un singolo documento.
    Restituisce un DoclingParseResult (con path e metadata).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Error: {file_path} not found.")

    print("CUDA is available" if torch.cuda.is_available() else "CUDA is NOT available")

    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)

    run_id = f"{Path(file_path).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = output_root_path / run_id
    print(f"Run output directory: {run_dir}")

    try:
        # 1) Docling Pipeline
        parse_result: DoclingParseResult = run_docling_parsing(
            file_path=file_path,
            run_dir=run_dir,
            use_rapidocr=use_rapidocr,
        )

        # 2) Report OCR Esterni (Opzionale)
        if use_openai:
            # Qui dovresti importare e chiamare la tua funzione openai
            pass
        elif use_rapidocr:
            print("RAPIDOCR enabled (Report skipped)")
        else:
            run_easyocr_report_if_needed(
                file_path=file_path,
                ocr_enabled=parse_result.ocr_enabled,
                ocr_engine_name=parse_result.ocr_engine_name,
                run_dir=parse_result.run_dir,
            )

        # Ritorniamo il risultato completo, non solo la cartella
        return parse_result

    except Exception as e:
        print(f"An error occurred inside the library: {e}")
        traceback.print_exc()
        raise e


def process_batch_or_file(
        input_path: str,
        output_root: str = "output",
        use_rapidocr: bool = False,
        use_openai: bool = False,
) -> List[DoclingParseResult]:
    """
    Entry point "intelligente":
    - Se input_path è un file: processa il file.
    - Se input_path è una cartella: processa tutti i file supportati all'interno.

    Ritorna una lista di DoclingParseResult.
    """
    path_obj = Path(input_path)
    successful_runs: List[DoclingParseResult] = []

    # 1. Identifica la lista dei file da processare
    files_to_process: List[Path] = []

    if path_obj.is_file():
        if is_supported_file(path_obj):
            files_to_process.append(path_obj)
        else:
            print(f"Error: Il file {path_obj.name} non ha un'estensione supportata.")
            return []

    elif path_obj.is_dir():
        print(f"Scanning folder: {input_path}...")
        all_files = sorted(path_obj.iterdir())
        files_to_process = [p for p in all_files if p.is_file() and is_supported_file(p)]

        if not files_to_process:
            print("Nessun file supportato trovato nella cartella.")
            return []

        print(f"Trovati {len(files_to_process)} file da processare.")

    else:
        print(f"Error: {input_path} non esiste o non è valido.")
        return []

    # 2. Ciclo di elaborazione
    for i, file_p in enumerate(files_to_process, start=1):
        print(f"\n--- Processing {i}/{len(files_to_process)}: {file_p.name} ---")
        try:
            parse_result = process_document(
                file_path=str(file_p),
                output_root=output_root,
                use_rapidocr=use_rapidocr,
                use_openai=use_openai
            )
            successful_runs.append(parse_result)

        except Exception as e:
            print(f"[ERROR] Failed processing {file_p.name}: {e}")
            continue

    return successful_runs
