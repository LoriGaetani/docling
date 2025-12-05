# pipeline.py

import json
import uuid
from dataclasses import dataclass
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


@dataclass
class DoclingParseResult:
    ocr_enabled: bool
    ocr_engine_name: str

    # contenuto
    markdown: str  # markdown finale con header

    # dove ha scritto le cose
    run_dir: Path
    json_path: Path           # output.json grezzo
    markdown_path: Path       # output.md
    chunks_path: Path         # chunks.json
    images_dir: Optional[Path]

    # info utili per le immagini (path relativi da usare nei link)
    image_rel_paths: List[str]


# TODO test with different document formats
# TODO test if the ocr is actually needed based on text layer presence


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
) -> DoclingParseResult:
    """
    Esegue la pipeline Docling completa:
    1. Conversione (PDF/Image -> Docling Doc)
    2. Export JSON grezzo
    3. Analisi Merge Tabelle
    4. Generazione Markdown PULITO (nuova logica iterate_items) con placeholder immagini
    5. Salvataggio immagini su disco (fix percorsi Windows)
    6. Applicazione Merge Tabelle
    7. Iniezione Link Immagini (fix posizionamento)
    8. Salvataggio e Chunking
    """

    # 0. SETUP PERCORSI ASSOLUTI
    run_dir = run_dir.resolve()
    print(f"\n--- PROCESSING: {file_path} ---")
    print(f"Output Directory: {run_dir}")

    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. Parsing
    print(f"Running Docling conversion on {file_path}...")
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
    print(f"Saved JSON data to {json_path}")

    # 3. Analisi Merge Tabelle
    merged_groups = merge_tables(result.document)

    # 4. Generazione Markdown Pulito
    print("Generating Markdown with visual sorting...")
    md_parts: List[str] = []

    # Lista di tutti gli elementi
    all_items = []
    for item, level in result.document.iterate_items():
        all_items.append((item, level))

    # Funzione per estrarre la posizione (Pagina, Coordinata Y in alto)
    def get_sort_key(entry):
        item, _ = entry
        if hasattr(item, "prov") and item.prov:
            return (item.prov[0].page_no, item.prov[0].bbox.t)
        return (0, 999999)

    # Ordiniamo per posizione visiva
    all_items.sort(key=get_sort_key)

    # Placeholder per immagini in ordine di apparizione
    image_placeholders: List[str] = []
    image_index = 0

    # Generazione Markdown in ordine visivo
    for item, level in all_items:
        text = (getattr(item, "text", "") or "").strip()

        # Filtri (header/footer pagina)
        if item.label in (DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER):
            continue

        # Costruzione Markdown
        if item.label == DocItemLabel.SECTION_HEADER:
            if len(text) < 3:
                continue
            prefix = "#" * (level if level and level > 0 else 1)
            md_parts.append(f"{prefix} {text}")

        elif item.label == DocItemLabel.LIST_ITEM:
            md_parts.append(f"* {text}")

        elif item.label == DocItemLabel.TABLE:
            if hasattr(item, "export_to_markdown"):
                md_parts.append(item.export_to_markdown())
            else:
                if text:
                    md_parts.append(text)

        elif item.label == DocItemLabel.PICTURE:
            # Mettiamo un placeholder unico che sostituiremo dopo con ![Image](path)
            if text:
                md_parts.append(text)
            placeholder = f"[[[IMG_{image_index}]]]"
            image_placeholders.append(placeholder)
            md_parts.append(placeholder)
            image_index += 1

        elif item.label == DocItemLabel.CODE:
            md_parts.append(f"```\n{text}\n```")

        else:
            # Paragrafi standard
            if text:
                md_parts.append(text)

    cleaned_md = "\n\n".join(md_parts)

    # 5. Salvataggio Immagini CON FILTRO DIMENSIONI
    images_folder = run_dir / "images"
    images_folder.mkdir(parents=True, exist_ok=True)
    saved_image_paths: List[Union[str, None]] = []

    if hasattr(result.document, "pictures") and result.document.pictures:
        print(f"Analyzing {len(result.document.pictures)} pictures...")
        for i, picture in enumerate(result.document.pictures):
            if (
                hasattr(picture, "image")
                and hasattr(picture.image, "pil_image")
                and picture.image.pil_image is not None
            ):
                try:
                    pil_image = picture.image.pil_image
                    width, height = pil_image.size

                    # FILTRO ANTI-RUMORE (icone/linee troppo piccole)
                    if width < 50 or height < 50:
                        print(f"  Skipping small image {i} ({width}x{height})")
                        saved_image_paths.append(None)
                        continue

                    # Gestione formato
                    image_format = "png"
                    if hasattr(picture.image, "mimetype") and picture.image.mimetype:
                        image_format = picture.image.mimetype.split("/")[-1].lower()

                    fname = f"{uuid.uuid4()}.{image_format}"
                    save_path = images_folder / fname

                    pil_image.save(save_path, format=image_format.upper())

                    # Path relativo con slash unix
                    rel_path = str(save_path.relative_to(run_dir)).replace("\\", "/")
                    saved_image_paths.append(rel_path)

                except Exception as e:
                    print(f"  Could not save picture {i}: {e}")
                    saved_image_paths.append(None)
            else:
                saved_image_paths.append(None)
    else:
        print("No pictures found in the document.")

    # 6. Applicazione del Merge Tabelle
    final_md = generate_merged_markdown(result.document, cleaned_md, merged_groups)

    # 7. Iniezione Link Immagini CON SPAZIATURA
    if saved_image_paths and image_placeholders:
        print("Injecting image links into Markdown...")

        # Usiamo zip per accoppiare placeholder e path nello stesso ordine
        for placeholder, img_path in zip(image_placeholders, saved_image_paths):
            if img_path:
                final_md = final_md.replace(
                    placeholder,
                    f"\n\n![Image]({img_path})\n\n"
                )
            else:
                # Se l'immagine è stata filtrata o è fallita, rimuoviamo il placeholder
                final_md = final_md.replace(placeholder, "")

    # 8. Creazione Header e Salvataggio Output
    header_info = (
        f"> Docling OCR engine: **{ocr_engine_name}** "
        f"(enabled: {ocr_enabled})\n\n"
        f"File: `{file_path}`\n\n"
        f"---\n\n"
    )
    final_md_with_header = header_info + final_md

    md_output_path = run_dir / "output.md"
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(final_md_with_header)
    print(f"Successfully saved merged markdown to {md_output_path}")

    # 9. Chunking
    chunks_path = run_dir / "chunks.json"
    generate_markdown_chunks_from_string(
        markdown_text=final_md,  # Passiamo il testo pulito (senza header tecnico)
        output_path=chunks_path,
        source_name="docling_clean_smart"
    )

    # images_folder ce l'hai già definita sopra
    images_dir: Optional[Path] = None
    if hasattr(result.document, "pictures") and result.document.pictures:
        if images_folder.exists():
            images_dir = images_folder

    # filtriamo i None da saved_image_paths, tenendo solo i path validi
    image_rel_paths_clean = [p for p in saved_image_paths if p is not None]

    # path del JSON grezzo (lo hai già)
    json_path = run_dir / "output.json"

    return DoclingParseResult(
        ocr_enabled=ocr_enabled,
        ocr_engine_name=ocr_engine_name,
        markdown=final_md_with_header,
        run_dir=run_dir,
        json_path=json_path,
        markdown_path=md_output_path,
        chunks_path=chunks_path,
        images_dir=images_dir,
        image_rel_paths=image_rel_paths_clean,
    )

