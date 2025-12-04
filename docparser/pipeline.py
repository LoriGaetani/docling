# pipeline.py

import json
from pathlib import Path
from typing import List, Tuple, Optional, Set, Union
from collections import Counter
from mimetypes import guess_type

import torch
import pandas as pd
from PIL import Image

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions, EasyOcrOptions
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    ImageFormatOption,
)
from docling_core.types.doc import DocItemLabel

from docparser.chunking import generate_markdown_chunks_from_string
from docparser.utils import should_enable_ocr_for_file, merge_tables, generate_merged_markdown


# =========================================================
#  Helpers: document-like detection
# =========================================================

#TODO test with different document formats
#TODO test if the ocr is actually needed based on text layer presence




# =========================================================
#  Docling Converter Setup
# =========================================================

def build_docling_converter(
        file_path: str,
        use_rapidocr: bool,
) -> tuple[DocumentConverter, bool, str]:
    ocr_enabled = should_enable_ocr_for_file(file_path)
    print(f"Automatic OCR decision: {'ENABLED' if ocr_enabled else 'DISABLED'} for this file.")

    ocr_options = None
    ocr_engine_name = "no-ocr"

    if not ocr_enabled:
        ocr_engine_name = "no-ocr"
    else:
        if EasyOcrOptions is not None and RapidOcrOptions is not None:
            if use_rapidocr:
                print("Docling OCR engine: RapidOCR (forced)")
                ocr_options = RapidOcrOptions(lang=["it", "en"])
                ocr_engine_name = "rapidocr"
            else:
                print("Docling OCR engine: EasyOCR (default)")
                ocr_options = EasyOcrOptions(
                    lang=["it", "en"],
                    use_gpu=torch.cuda.is_available(),
                )
                ocr_engine_name = "easyocr"
        else:
            print("Docling OCR engine: AUTO (library default)")
            ocr_engine_name = "auto"

    pdf_pipeline_options = PdfPipelineOptions(
        generate_picture_images=True,
        generate_page_images=True,
        use_ocr=ocr_enabled,
        ocr_options=ocr_options if ocr_enabled else None,
    )

    image_pipeline_options = PdfPipelineOptions(
        generate_picture_images=True,
        generate_page_images=True,
        use_ocr=ocr_enabled,
        ocr_options=ocr_options if ocr_enabled else None,
    )

    pdf_format_option = PdfFormatOption(pipeline_options=pdf_pipeline_options)
    image_format_option = ImageFormatOption(pipeline_options=image_pipeline_options)

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: pdf_format_option,
            InputFormat.IMAGE: image_format_option,
        }
    )

    return converter, ocr_enabled, ocr_engine_name


# =========================================================
#  MAIN PARSING FUNCTION
# =========================================================

def run_docling_parsing(
        file_path: str,
        run_dir: Path,
        use_rapidocr: bool = False,
) -> tuple[bool, str, str]:
    """
    Esegue la pipeline Docling completa:
    1. Conversione (PDF/Image -> Docling Doc)
    2. Export JSON grezzo
    3. Analisi Merge Tabelle
    4. Generazione Markdown PULITO (nuova logica iterate_items)
    5. Salvataggio immagini
    6. Applicazione Merge Tabelle
    7. Chunking (chiama modulo esterno)
    """

    print(f"Processing {file_path} with Docling...")
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. Parsing
    converter, ocr_enabled, ocr_engine_name = build_docling_converter(
        file_path=file_path,
        use_rapidocr=use_rapidocr,
    )
    result = converter.convert(file_path)

    # 2. Export JSON grezzo
    json_path = run_dir / "output.json"
    doc_data = result.document.export_to_dict()
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(doc_data, f, indent=2, ensure_ascii=False)
    print(f"Successfully saved parsed data to {json_path}")

    # 3. Analisi Merge Tabelle
    merged_groups = merge_tables(result.document)

    # 4. Generazione Markdown Pulito (NUOVA LOGICA iterate_items)
    # Questa parte sostituisce la logica "clean_headers_footers" euristica vecchia
    print("Generating Markdown filtering out page headers/footers (New Logic)...")
    md_parts: List[str] = []

    NOISY_HEADER_PATTERNS = [
        "Comando Provinciale Carabinieri",
        "Procedimento penale nr.9028/10 RGNR",
        "Procura della Repubblica di Genova - DDA",
        # Aggiungi qui altri pattern fissi da rimuovere
    ]

    for item, level in result.document.iterate_items():
        text = (getattr(item, "text", "") or "").strip()

        # Filtro 1: Label Docling (Header/Footer pagina)
        if item.label in (DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER):
            continue

        # Filtro 2: Pattern testuali specifici
        if any(pat in text for pat in NOISY_HEADER_PATTERNS):
            continue

        # Costruzione Markdown in base al tipo
        if item.label == DocItemLabel.SECTION_HEADER:
            prefix = "#" * (level if level and level > 0 else 1)
            if text:
                md_parts.append(f"{prefix} {text}")

        elif item.label == DocItemLabel.LIST_ITEM:
            if text:
                md_parts.append(f"* {text}")

        elif item.label == DocItemLabel.TABLE:
            # Qui inseriamo la versione base della tabella, poi verrà sostituita se fa parte di un merge
            if hasattr(item, "export_to_markdown"):
                md_parts.append(item.export_to_markdown())
            else:
                if text:
                    md_parts.append(text)

        elif item.label == DocItemLabel.PICTURE:
            if text:
                md_parts.append(text)
            # Placeholder per dopo
            md_parts.append("<!-- image -->")

        elif item.label == DocItemLabel.CODE:
            md_parts.append(f"```\n{text}\n```")

        else:
            # Testo standard (paragrafi, didascalie, ecc.)
            if text:
                md_parts.append(text)

    # Uniamo il tutto
    cleaned_md = "\n\n".join(md_parts)

    # 5. Salvataggio Immagini
    images_folder = run_dir / "images"
    images_folder.mkdir(parents=True, exist_ok=True)
    saved_image_paths: List[Union[str, None]] = []

    if hasattr(result.document, "pictures") and result.document.pictures:
        print(f"Saving {len(result.document.pictures)} pictures to {images_folder}...")
        for i, picture in enumerate(result.document.pictures):
            if (
                    hasattr(picture, "image")
                    and hasattr(picture.image, "pil_image")
                    and picture.image.pil_image is not None
            ):
                try:
                    pil_image = picture.image.pil_image
                    image_format = "png"
                    if hasattr(picture.image, "mimetype") and picture.image.mimetype:
                        image_format = picture.image.mimetype.split("/")[-1].lower()

                    picture_filename = f"picture_{i}.{image_format}"
                    picture_path = images_folder / picture_filename

                    pil_image.save(picture_path, format=image_format.upper())
                    saved_image_paths.append(str(picture_path.relative_to(run_dir)))
                except Exception as e:
                    print(f"  Could not save picture {i}: {e}")
                    saved_image_paths.append(None)
            else:
                saved_image_paths.append(None)
    else:
        print("No pictures found in the document.")

    # 6. Applicazione del Merge Tabelle sulla stringa pulita
    final_md = generate_merged_markdown(result.document, cleaned_md, merged_groups)

    # 7. Iniezione Link Immagini (Modifica final_md, che è ancora "pulito")
    if saved_image_paths:
        print("Injecting image links into Markdown...")
        placeholder = ""
        for img_path in saved_image_paths:
            # ... (logica replace) ...
            if img_path and placeholder in final_md:
                final_md = final_md.replace(placeholder, f"![Image]({img_path})", 1)
            elif not img_path and placeholder in final_md:
                final_md = final_md.replace(placeholder, "", 1)

    # 8. Creazione Header (SOLO per il file .md su disco)
    header_info = (
        f"> Docling OCR engine: **{ocr_engine_name}** "
        f"(enabled: {ocr_enabled})\n\n"
        f"File: `{file_path}`\n\n"
        f"---\n\n"
    )
    final_md_with_header = header_info + final_md  # <--- Versione "sporcam" per debug

    # 9. Salvataggio Markdown (Salviamo quella con l'header)
    md_output_path = run_dir / "output.md"
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(final_md_with_header)
    print(f"Successfully saved merged markdown to {md_output_path}")

    # 10. Chunking (MODIFICA QUI: passiamo 'final_md', non 'final_md_with_header')
    chunks_path = run_dir / "chunks.json"
    generate_markdown_chunks_from_string(
        markdown_text=final_md,  # <--- Passa SOLO il contenuto pulito all'LLM
        output_path=chunks_path,
        source_name="docling_clean_smart"
    )

    return ocr_enabled, ocr_engine_name, final_md_with_header
