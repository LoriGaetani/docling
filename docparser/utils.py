
from pathlib import Path
from typing import Union
from mimetypes import guess_type

import pandas as pd
from PIL import Image



def is_document_like_image(image_path: Union[str, Path]) -> bool:
    """
    Euristica veloce per capire se un'immagine assomiglia a un documento scansionato.

    True  = probabile foto/pdf di documento (foglio, contratto, ecc.)
    False = probabile foto di persone/paesaggi/oggetti vari
    """
    image_path = Path(image_path)

    try:
        with Image.open(image_path) as img:
            width, height = img.size
    except Exception:
        # Se non riesco a leggerla, non rischio OCR
        return False

    # Immagini troppo piccole: difficilmente un documento leggibile
    min_side = min(width, height)
    if min_side < 600:
        return False

    # Aspect ratio tipo foglio (A4 ≈ 1.41), teniamo un range largo
    aspect_ratio = max(width, height) / min(width, height)
    if not (0.7 <= aspect_ratio <= 1.9):
        # molto panoramica o molto stretta → più probabile foto
        return False

    return True


def should_enable_ocr_for_file(file_path: Union[str, Path]) -> bool:
    """
    Decide se ha senso abilitare l'OCR per questo file *a livello Docling*.

    - PDF      -> True  (Docling poi decide pagina per pagina dove usare OCR)
    - Immagine -> True  solo se l'immagine sembra un documento
    - Altro    -> False
    """
    file_path = Path(file_path)
    mime, _ = guess_type(file_path.name)

    # PDF: abilitiamo sempre OCR, Docling userà il text layer se c'è
    if mime == "application/pdf":
        return True

    # Immagini: usiamo l'euristica document-like
    if mime and mime.startswith("image/"):
        return is_document_like_image(file_path)

    # Altri formati: di default niente OCR
    return False


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
#  Table merge Logic
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
    """
    Sostituisce le tabelle nel markdown generato con le versioni mergiate.
    """
    print("Post-processing Markdown to merge tables...")

    for group in merged_groups:
        indices = group['indices']
        if len(indices) <= 1:
            continue

        merged_df = group['df']
        merged_md_table = merged_df.to_markdown(index=False)

        first_idx = indices[0]
        first_table_item = doc.tables[first_idx]
        # Nota: Qui usiamo l'export standard per trovare la stringa da sostituire
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
                pass

    return md_text


SUPPORTED_EXTENSIONS = {".pdf", ".jpg"}

def is_supported_file(file_path: Union[str, Path]) -> bool:
    """Ritorna True se il file ha un'estensione supportata."""
    return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS