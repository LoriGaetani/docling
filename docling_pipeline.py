# docling_pipeline.py

import json
from pathlib import Path
from typing import List, Tuple, Optional, Set, Union
from collections import Counter
from mimetypes import guess_type

import torch
import pandas as pd
from PIL import Image

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    ImageFormatOption,
)
from docling_core.types.doc import DocItemLabel

from chunking import chunk_markdown


# =========================================================
#  Helpers: document-like detection
# =========================================================

def is_document_like_image(image_path: Union[str, Path]) -> bool:
    image_path = Path(image_path)
    try:
        with Image.open(image_path) as img:
            width, height = img.size
    except Exception:
        return False

    min_side = min(width, height)
    if min_side < 600:
        return False

    aspect_ratio = max(width, height) / min(width, height)
    if not (0.7 <= aspect_ratio <= 1.9):
        return False

    return True


def should_enable_ocr_for_file(file_path: Union[str, Path]) -> bool:
    file_path = Path(file_path)
    mime, _ = guess_type(file_path.name)

    if mime == "application/pdf":
        return True

    if mime and mime.startswith("image/"):
        return is_document_like_image(file_path)

    return False


# =========================================================
#  Header/footer cleaning helpers (heuristic)
# =========================================================

def _normalize_line(line: str) -> str:
    return " ".join(line.split()).strip()


def _extract_block(lines: List[str], start_idx: int, max_block_size: int = 8) -> Tuple[str, ...]:
    block: List[str] = []
    i = start_idx
    while i < len(lines) and len(block) < max_block_size:
        norm = _normalize_line(lines[i])
        if norm == "":
            break
        block.append(norm)
        i += 1
    return tuple(block)


def _find_repeated_header_block(
    lines: List[str],
    min_block_size: int = 3,
    max_block_size: int = 8,
    min_repetitions: int = 3,
) -> Optional[Tuple[str, ...]]:
    blocks_counter: Counter[Tuple[str, ...]] = Counter()
    for start_idx in range(len(lines)):
        block = _extract_block(lines, start_idx, max_block_size=max_block_size)
        if len(block) >= min_block_size:
            blocks_counter[block] += 1

    if not blocks_counter:
        return None

    block, count = blocks_counter.most_common(1)[0]
    if count >= min_repetitions:
        return block
    return None


def _find_repeated_footer_lines(
    lines: List[str], min_repetitions: int = 3
) -> Set[str]:
    counter: Counter[str] = Counter()
    for line in lines:
        norm = _normalize_line(line)
        if norm.isdigit():
            counter[norm] += 1

    return {v for v, c in counter.items() if c >= min_repetitions}


def _matches_block_at(lines: List[str], start_idx: int, block: Tuple[str, ...]) -> bool:
    if start_idx + len(block) > len(lines):
        return False
    for offset, expected in enumerate(block):
        if _normalize_line(lines[start_idx + offset]) != expected:
            return False
    return True


def clean_headers_footers(text: str) -> str:
    lines = text.splitlines()

    header_block = _find_repeated_header_block(lines)
    footer_lines_norm = _find_repeated_footer_lines(lines)

    print("=== HEADER/FOOTER DETECTION (heuristic) ===")
    if header_block:
        print("\nDetected HEADER block:")
        for l in header_block:
            print("  ", l)
    else:
        print("\nNo repeated header block found.")

    if footer_lines_norm:
        print("\nDetected FOOTER numeric lines:")
        for f in footer_lines_norm:
            print("  ", f)
    else:
        print("\nNo repeated numeric footers found.")
    print("===========================================\n")

    cleaned_lines: List[str] = []
    i = 0
    while i < len(lines):
        if header_block and _matches_block_at(lines, i, header_block):
            i += len(header_block)
            continue

        if _normalize_line(lines[i]) in footer_lines_norm:
            i += 1
            continue

        cleaned_lines.append(lines[i])
        i += 1

    return "\n".join(cleaned_lines)


# =========================================================
#  Table merge
# =========================================================

def merge_tables(doc):
    if not doc.tables:
        print("No tables found to merge.")
        return []

    print("Analyzing tables for merging...")

    merged_groups = []
    dfs = [t.export_to_dataframe() for t in doc.tables]
    if not dfs:
        return []

    current_indices = [0]
    current_df = dfs[0]

    for i in range(1, len(dfs)):
        next_df = dfs[i]

        if len(current_df.columns) == len(next_df.columns):
            if list(current_df.columns) == list(next_df.columns):
                current_df = pd.concat([current_df, next_df], ignore_index=True)
                print(f"  Merged table {i} into previous table (matching headers).")
            else:
                is_range_index = (
                    isinstance(next_df.columns, pd.RangeIndex)
                    or (
                        pd.api.types.is_numeric_dtype(next_df.columns)
                        and list(next_df.columns) == list(range(len(next_df.columns)))
                    )
                )

                if is_range_index:
                    next_df.columns = current_df.columns
                    current_df = pd.concat([current_df, next_df], ignore_index=True)
                    print(f"  Merged table {i} into previous table (renamed integer columns).")
                else:
                    header_row = next_df.columns.tolist()
                    data_values = next_df.values.tolist()
                    full_data = [header_row] + data_values
                    fixed_next_df = pd.DataFrame(full_data, columns=current_df.columns)
                    current_df = pd.concat([current_df, fixed_next_df], ignore_index=True)
                    print(f"  Merged table {i} into previous table (recovered header as data row).")

            current_indices.append(i)
        else:
            merged_groups.append({'indices': current_indices, 'df': current_df})
            current_indices = [i]
            current_df = next_df

    merged_groups.append({'indices': current_indices, 'df': current_df})
    return merged_groups


def generate_merged_markdown(doc, md_text, merged_groups):
    print("Post-processing Markdown to merge tables...")

    for group in merged_groups:
        indices = group['indices']
        if len(indices) <= 1:
            continue

        merged_df = group['df']
        merged_md_table = merged_df.to_markdown(index=False)

        first_idx = indices[0]
        first_table_item = doc.tables[first_idx]
        first_table_md_snippet = first_table_item.export_to_markdown(doc=doc)

        if first_table_md_snippet in md_text:
            md_text = md_text.replace(first_table_md_snippet, merged_md_table, 1)
        else:
            print(f"  Warning: Could not find original text for table {first_idx} in Markdown.")

        for idx in indices[1:]:
            table_item = doc.tables[idx]
            table_md_snippet = table_item.export_to_markdown(doc=doc)
            if table_md_snippet in md_text:
                md_text = md_text.replace(table_md_snippet, "\n<!-- merged table part -->\n", 1)
            else:
                print(f"  Warning: Could not find original text for table {idx} in Markdown.")

    return md_text


# =========================================================
#  Docling OCR engine (EasyOCR default, RapidOCR su flag)
# =========================================================

try:
    from docling.datamodel.pipeline_options import (
        EasyOcrOptions,
        RapidOcrOptions,
    )
except ImportError:
    EasyOcrOptions = None
    RapidOcrOptions = None


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
#  Core parsing Docling (PDF / immagini) -> run_dir
# =========================================================

def run_docling_parsing(
    file_path: str,
    run_dir: Path,
    use_rapidocr: bool = False,
) -> tuple[bool, str, str]:
    """
    - esegue Docling
    - salva output.json, output.md, chunks.json, immagini
    - in cima a output.md scrive quale OCR Docling ha usato
    """
    print(f"Processing {file_path} with Docling...")

    run_dir.mkdir(parents=True, exist_ok=True)

    converter, ocr_enabled, ocr_engine_name = build_docling_converter(
        file_path=file_path,
        use_rapidocr=use_rapidocr,
    )

    result = converter.convert(file_path)

    # JSON
    json_path = run_dir / "output.json"
    doc_data = result.document.export_to_dict()
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(doc_data, f, indent=2, ensure_ascii=False)
    print(f"Successfully saved parsed data to {json_path}")

    # Merge tabelle
    merged_groups = merge_tables(result.document)

    # Markdown base
    try:
        allowed_labels = {
            label
            for label in DocItemLabel
            if label not in (DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER)
        }
        original_md = result.document.export_to_markdown(labels=allowed_labels)
        print("Exported Markdown without page headers/footers (DocItemLabel filter).")
    except Exception as e:
        print(f"Warning: could not filter out headers/footers, falling back to default export: {e}")
        original_md = result.document.export_to_markdown()

    cleaned_md = clean_headers_footers(original_md)

    # Immagini
    images_folder = run_dir / "images"
    images_folder.mkdir(parents=True, exist_ok=True)
    saved_image_paths = []

    if hasattr(result.document, 'pictures') and result.document.pictures:
        print(f"Saving {len(result.document.pictures)} pictures to {images_folder}...")
        for i, picture in enumerate(result.document.pictures):
            if hasattr(picture, 'image') and hasattr(picture.image, 'pil_image') and picture.image.pil_image:
                try:
                    pil_image = picture.image.pil_image
                    image_format = "png"
                    if hasattr(picture.image, 'mimetype') and picture.image.mimetype:
                        image_format = picture.image.mimetype.split('/')[-1].lower()

                    picture_filename = f"picture_{i}.{image_format}"
                    picture_path = images_folder / picture_filename

                    pil_image.save(picture_path, format=image_format.upper())
                    print(f"  Saved {picture_filename}")
                    saved_image_paths.append(str(picture_path.relative_to(run_dir)))
                except Exception as e:
                    print(f"  Could not save picture {i} (ID: {getattr(picture, 'id', 'N/A')}): {e}")
                    saved_image_paths.append(None)
            else:
                print(
                    f"  Picture {i} (ID: {getattr(picture, 'id', 'N/A')}) "
                    f"has no PIL image data."
                )
                saved_image_paths.append(None)
    else:
        print("No pictures found in the document.")

    # Merge tabelle nel markdown
    final_md = generate_merged_markdown(result.document, cleaned_md, merged_groups)

    # Placeholder immagini
    if saved_image_paths:
        print("Injecting image links into Markdown...")
        for img_path in saved_image_paths:
            if img_path and "<!-- image -->" in final_md:
                final_md = final_md.replace("<!-- image -->", f"![Image]({img_path})", 1)
            elif img_path:
                print(f"  Warning: No placeholder found for image {img_path}")
            else:
                if "<!-- image -->" in final_md:
                    final_md = final_md.replace("<!-- image -->", "<!-- image missing -->", 1)

    # Header con info OCR
    header = (
        f"> Docling OCR engine: **{ocr_engine_name}** "
        f"(enabled: {ocr_enabled})\n\n"
        f"File: `{file_path}`\n\n"
        f"---\n\n"
    )
    final_md_with_header = header + final_md

    # Salva output.md
    md_output_path = run_dir / "output.md"
    with open(md_output_path, 'w', encoding='utf-8') as f:
        f.write(final_md_with_header)
    print(f"Successfully saved merged markdown to {md_output_path}")

    # Chunking
    chunks_path = run_dir / "chunks.json"
    chunk_markdown(final_md_with_header, str(chunks_path))
    print(f"Successfully saved chunks to {chunks_path}")

    return ocr_enabled, ocr_engine_name, final_md_with_header
